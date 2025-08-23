from __future__ import annotations

import re
import time
from enum import Enum
from typing import Optional

import requests
from requests import Response
from requests.adapters import HTTPAdapter

from ..base.log_manager import get_logger
from ..core.entry import SignInEntry
from ..utils import net_utils
from ..utils.common_utils import NetworkState, UrlUtils
from .work import Work

logger = get_logger(__name__)


class RequestMethod(Enum):
    """请求方法类型枚举"""
    DEFAULT = 'default'  # 标准requests请求
    FLARESOLVERR = 'flaresolverr'  # FlareSolverr请求


def check_network_state(entry: SignInEntry,
                        param: Work | str | list[str],
                        response: Response | None,
                        content: str | None = None,
                        check_content=False,
                        ) -> NetworkState:
    urls = param
    if isinstance(param, Work):
        urls = param.response_urls
    elif isinstance(param, str):
        urls = [param]

    if response is None or (check_content and content is None):
        entry.fail_with_prefix(
            NetworkState.NETWORK_ERROR.value.format(url=urls[0], error='Response is None')
        )
        return NetworkState.NETWORK_ERROR

    maintenance_state = check_maintenance_state(response, urls[0])
    if maintenance_state != NetworkState.SUCCEED:
        entry.fail_with_prefix(maintenance_state.value.format(url=urls[0]))
        return maintenance_state

    if cf_detected(response):
        entry.fail_with_prefix(NetworkState.CLOUDFLARE_BLOCKED.value.format(url=urls[0]))
        return NetworkState.CLOUDFLARE_BLOCKED

    if response.url not in urls:
        entry.fail_with_prefix(
        NetworkState.URL_REDIRECT.value.format(original_url=urls[0], redirect_url=response.url)
        )
        return NetworkState.URL_REDIRECT

    return NetworkState.SUCCEED


def check_maintenance_state(response: Response, url: str) -> NetworkState:
    if response is None:
        return NetworkState.NETWORK_ERROR

    try:
        content = response.text.lower()
        title = ""

        if hasattr(response, 'text') and response.text:
            title_match = re.search(r'<title[^>]*>(.*?)</title>', response.text, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip().lower()

        maintenance_indicators = [
            '维护中', '网站维护', '站点维护', '系统维护', '服务器维护',
            '暂停服务', '临时关闭', '升级中', '更新中',
            'maintenance', 'under maintenance', 'site maintenance',
            'system maintenance', 'server maintenance', 'temporarily unavailable',
            'service unavailable', 'upgrading', 'updating',
            '网站维护中', 'site under maintenance', 'maintenance mode'
        ]

        for indicator in maintenance_indicators:
            if indicator in content or indicator in title:
                logger.info(f"🔧 检测到站点维护状态: {url}")
                return NetworkState.MAINTENANCE

        if hasattr(response, 'status_code') and response.status_code == 503:
            logger.info(f"🔧 检测到503状态码，站点可能维护中: {url}")
            return NetworkState.MAINTENANCE

        return NetworkState.SUCCEED

    except Exception as e:
        logger.debug(f"维护状态检查异常: {e}")
        return NetworkState.SUCCEED


def cf_detected(response: Response) -> bool:
    if response is not None and hasattr(response, 'text'):
            return bool(re.search(r'security by.*Cloudflare</a>', response.text, flags=re.DOTALL))
    return False


class RequestHandler:
    """统一请求处理器，负责发送HTTP请求"""

    def __init__(self, entry: SignInEntry, config: Optional[dict] = None):
        self.entry = entry
        self.config = config or {}
        self.session: Optional[requests.Session] = None
        self._last_request_method_log: dict = {}

    def request(self, method: str, url: str, **kwargs) -> Response | None:
        """根据配置发送HTTP请求"""
        site_name = self.entry.get('site_name', 'unknown')

        request_method = self._determine_request_method()
        method_name = request_method.name

        log_key = f"{site_name}_{method_name}"
        current_time = time.time()
        if log_key not in self._last_request_method_log or current_time - self._last_request_method_log.get(log_key, 0) > 30:
            logger.info(f"{site_name} - 🌐 选择请求方式: {method_name}")
            self._last_request_method_log[log_key] = current_time

        if request_method == RequestMethod.FLARESOLVERR:
            return self._request_with_flaresolverr(method, url, **kwargs)
        return self._request_with_standard(method, url, **kwargs)

    def _determine_request_method(self) -> RequestMethod:
        """根据配置确定请求方式"""
        site_name = self.entry.get('site_name') or UrlUtils.extract_site_name(self.entry.get('url', ''))
        if self._should_use_flaresolverr(site_name):
            return RequestMethod.FLARESOLVERR
        return RequestMethod.DEFAULT

    def _should_use_flaresolverr(self, site_name: str) -> bool:
        """检查是否应为指定站点使用FlareSolverr"""
        flaresolverr_config = self.config.get('flaresolverr', {})
        if not flaresolverr_config.get('enabled'):
            return False
        enabled_sites = flaresolverr_config.get('enabled_sites', [])
        return enabled_sites == "*" or site_name in enabled_sites

    def _init_session(self) -> None:
        """初始化requests.Session"""
        if not self.session:
            self.session = requests.Session()
            if entry_headers := self.entry.get('headers'):
                self.session.headers.update(entry_headers)
            if entry_cookie := self.entry.get('cookie'):
                cookies = net_utils.cookie_str_to_dict(entry_cookie)
                self.session.cookies.update(cookies)
            self.session.mount('http://', HTTPAdapter(max_retries=2))
            self.session.mount('https://', HTTPAdapter(max_retries=2))

    def _update_session_cookie(self) -> None:
        """更新session cookie到entry中"""
        if self.session:
            cookie_items = self.session.cookies.items()
            session_cookie = ' '.join([f'{k}={v};' for k, v in cookie_items])
            self.entry['session_cookie'] = session_cookie

    def _request_with_standard(self, method: str, url: str, **kwargs) -> Response | None:
        """使用标准requests发送请求"""
        try:
            self._init_session()
            logger.debug(f"标准请求: {method} {url}")
            response = self.session.request(method, url, timeout=60, **kwargs)

            if cf_detected(response):
                logger.warning(f"检测到Cloudflare保护: {url}")
                self.entry.fail_with_prefix(f'url: {url} detected CloudFlare DDoS-GUARD. Consider using FlareSolverr.')
            elif response.status_code not in [200, 404]: # 404 for some special cases
                                self.entry.fail_with_prefix(f'url: {url} response.status_code={response.status_code}')

            self._update_session_cookie()
            return response
        except Exception as e:
            logger.error(f"标准请求失败: {e}")
            self.entry.fail_with_prefix(NetworkState.NETWORK_ERROR.value.format(url=url, error=e))
        return None

    def _request_with_flaresolverr(self, method: str, url: str, **kwargs) -> Response | None:
        """使用FlareSolverr发送请求"""
        try:
            from ..utils.flaresolverr import FlareSolverrClient
            client = FlareSolverrClient(self.config)
            return client.request(method, url, **kwargs)
        except ImportError:
            logger.error("FlareSolverr模块不可用")
            self.entry.fail_with_prefix("FlareSolverr module not available")
        except Exception as e:
            logger.error(f"FlareSolverr请求失败: {e}")
            self.entry.fail_with_prefix(f"FlareSolverr request error: {e}")
        return None
