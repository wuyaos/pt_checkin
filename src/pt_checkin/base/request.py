from __future__ import annotations

import re
from enum import Enum
from typing import Optional

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from loguru import logger

from ..core.entry import SignInEntry
from .work import Work
from ..utils import net_utils


class NetworkState(Enum):
    SUCCEED = 'Succeed'
    URL_REDIRECT = 'Url: {original_url} redirect to {redirect_url}'
    NETWORK_ERROR = 'Network error: url: {url}, error: {error}'


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
        entry.fail_with_prefix(NetworkState.NETWORK_ERROR.value.format(url=urls[0], error='Response is None'))
        return NetworkState.NETWORK_ERROR
    if response.url not in urls:
        entry.fail_with_prefix(
            NetworkState.URL_REDIRECT.value.format(original_url=urls[0], redirect_url=response.url))
        return NetworkState.URL_REDIRECT
    return NetworkState.SUCCEED


def cf_detected(response: Response) -> bool:
    if response is not None:
        return bool(re.search(r'security by.*Cloudflare</a>', response.text, flags=re.DOTALL))


class Request:

    def __init__(self):
        self.session = None
        self.flaresolverr_client = None

    def _should_use_flaresolverr(self, entry: SignInEntry) -> bool:
        """检查是否应该使用FlareSolverr"""
        # 使用统一的检测逻辑
        from ..utils.flaresolverr import should_use_flaresolverr
        config = entry.get('config', {})
        return should_use_flaresolverr(entry, config)

    def _get_flaresolverr_client(self, entry: SignInEntry,
                                config: Optional[dict] = None):
        """获取FlareSolverr客户端"""
        if self.flaresolverr_client is None:
            try:
                from ..utils.flaresolverr import get_flaresolverr_client
                # 优先使用传入的config，否则从entry中获取
                use_config = config or entry.get('config', {})
                logger.info(f"Creating FlareSolverr client with config: {use_config.get('flaresolverr', 'Not found')}")
                self.flaresolverr_client = get_flaresolverr_client(use_config)
                if self.flaresolverr_client:
                    logger.info(f"FlareSolverr client initialized: {self.flaresolverr_client.server_url}")
                else:
                    logger.warning("FlareSolverr client creation failed")
            except ImportError:
                logger.warning("FlareSolverr module not available")
                return None
            except Exception as e:
                logger.error(f"FlareSolverr client creation error: {e}")
                return None
        return self.flaresolverr_client

    def _request_with_flaresolverr(self,
                                  entry: SignInEntry,
                                  method: str,
                                  url: str,
                                  config: Optional[dict] = None,
                                  **kwargs) -> Response | None:
        """使用FlareSolverr发送请求"""
        client = self._get_flaresolverr_client(entry, config)
        if not client:
            logger.error("FlareSolverr client not available")
            return None

        try:
            # 准备请求参数
            headers = kwargs.get('headers', {})
            if entry_headers := entry.get('headers'):
                headers.update(entry_headers)

            cookies = {}
            if entry_cookie := entry.get('cookie'):
                from ..utils.flaresolverr import cookie_str_to_dict
                cookies = cookie_str_to_dict(entry_cookie)

            # 发送请求
            if method.upper() == 'GET':
                solution = client.request_get(url, headers, cookies)
            elif method.upper() == 'POST':
                # 处理POST数据
                post_data = ""
                logger.info(f"POST kwargs: {kwargs}")
                if 'data' in kwargs:
                    import urllib.parse
                    post_data = urllib.parse.urlencode(kwargs['data'])
                    logger.info(f"POST data encoded: {post_data}")
                elif 'json' in kwargs:
                    import json
                    post_data = json.dumps(kwargs['json'])
                    logger.info(f"POST json encoded: {post_data}")
                else:
                    logger.warning("No POST data found in kwargs")

                solution = client.request_post(url, post_data, headers, cookies)
            else:
                logger.error(f"Unsupported method for FlareSolverr: {method}")
                return None

            if not solution:
                return None

            # 创建模拟的Response对象
            class MockResponse:
                def __init__(self, solution_data):
                    self.status_code = solution_data.get('status', 200)
                    self.text = solution_data.get('response', '')
                    self.url = solution_data.get('url', url)
                    self.headers = solution_data.get('headers', {})

                    # 处理二进制内容
                    response_text = solution_data.get('response', '')
                    if isinstance(response_text, str):
                        # 检查是否是图片请求
                        if 'image.php' in url or any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
                            # 对于图片请求，使用latin-1编码保持字节不变
                            try:
                                self.content = response_text.encode('latin-1')
                            except UnicodeEncodeError:
                                # 如果latin-1失败，使用utf-8
                                self.content = response_text.encode('utf-8')
                        else:
                            # 对于普通文本内容，使用utf-8编码
                            self.content = response_text.encode('utf-8')
                    else:
                        self.content = response_text

                    # 更新entry中的cookie
                    if 'cookies' in solution_data:
                        cookie_list = []
                        for cookie in solution_data['cookies']:
                            cookie_list.append(f"{cookie['name']}={cookie['value']}")
                        entry['session_cookie'] = '; '.join(cookie_list)

            return MockResponse(solution)

        except Exception as e:
            logger.error(f"FlareSolverr request error: {e}")
            entry.fail_with_prefix(f"FlareSolverr error: {e}")
            return None

    def request(self,
                entry: SignInEntry,
                method: str,
                url: str,
                config: Optional[dict] = None,
                **kwargs,
                ) -> Response | None:

        # 检查是否使用FlareSolverr
        if self._should_use_flaresolverr(entry):
            logger.info(f"Using FlareSolverr for {url}")
            logger.info(f"Config passed to request: {config is not None}")
            logger.info(f"Entry config exists: {entry.get('config') is not None}")
            if config:
                logger.info(f"Config has flaresolverr: {'flaresolverr' in config}")
            if entry.get('config'):
                logger.info(f"Entry config has flaresolverr: {'flaresolverr' in entry.get('config', {})}")
            return self._request_with_flaresolverr(
                entry, method, url, config, **kwargs
            )

        # 使用常规请求
        if not self.session:
            self.session = requests.Session()
            if entry_headers := entry.get('headers'):
                self.session.headers.update(entry_headers)
            if entry_cookie := entry.get('cookie'):
                cookies = net_utils.cookie_str_to_dict(entry_cookie)
                self.session.cookies.update(cookies)
            self.session.mount('http://', HTTPAdapter(max_retries=2))
            self.session.mount('https://', HTTPAdapter(max_retries=2))

        try:
            response: Response = self.session.request(
                method, url, timeout=60, **kwargs
            )

            # 检测Cloudflare保护
            if cf_detected(response):
                logger.warning(f"Cloudflare detected for {url}")
                entry.fail_with_prefix(
                    f'url: {url} detected CloudFlare DDoS-GUARD. '
                    'Consider enabling FlareSolverr.'
                )
            elif response is not None and response.status_code != 200:
                entry.fail_with_prefix(
                    f'url: {url} response.status_code={response.status_code}'
                )

            # 更新session cookie
            cookie_items = self.session.cookies.items()
            session_cookie = ' '.join([f'{k}={v};' for k, v in cookie_items])
            entry['session_cookie'] = session_cookie

            return response

        except Exception as e:
            entry.fail_with_prefix(
                NetworkState.NETWORK_ERROR.value.format(url=url, error=e)
            )
        return None
