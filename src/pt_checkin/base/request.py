from __future__ import annotations

import re
from abc import ABC, abstractmethod
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


class RequestMethod(Enum):
    """请求方法类型枚举"""
    DEFAULT = 'default'          # 标准requests请求
    BROWSER = 'browser'          # 浏览器自动化请求
    AUTO = 'auto'               # 自动选择（默认行为）

class BrowserResponse:
    """浏览器响应对象，用于DrissionPage返回结果"""

    def __init__(self, page, original_url=''):
        """
        从DrissionPage页面创建响应对象

        Args:
            page: DrissionPage的页面对象
            original_url: 原始请求URL
        """
        try:
            self.status_code = 200  # DrissionPage通常不提供状态码

            # 根据DrissionPage文档，使用正确的方法获取HTML
            if hasattr(page, 'html'):
                self.text = page.html
            elif hasattr(page, 'page_source'):
                self.text = page.page_source
            else:
                # 备用方法
                self.text = str(page)

            self.url = page.url if hasattr(page, 'url') else original_url
            self.headers = {}  # DrissionPage不直接提供响应头
            self.content = self.text.encode('utf-8') if self.text else b''
            self._original_url = original_url

            logger.debug(f"创建浏览器响应对象: {self.url}, 内容长度: {len(self.text)}")

        except Exception as e:
            logger.error(f"创建浏览器响应对象失败: {e}")
            self.status_code = 500
            self.text = ''
            self.url = original_url
            self.headers = {}
            self.content = b''


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


class BaseRequest(ABC):
    """HTTP请求处理抽象基类"""

    def __init__(self):
        self.session: Optional[requests.Session] = None
        self._browser_manager = None  # 浏览器管理器实例

    @abstractmethod
    def request(self,
                entry: SignInEntry,
                method: str,
                url: str,
                config: Optional[dict] = None,
                force_default: bool = False,
                **kwargs,
                ) -> Response | None:
        """
        发送HTTP请求的抽象方法

        Args:
            entry: 签到条目
            method: HTTP方法 (GET, POST等)
            url: 请求URL
            config: 配置字典
            force_default: 强制使用标准requests（用于验证码图片下载等场景）
            **kwargs: 其他请求参数

        Returns:
            Response对象或None
        """
        pass

    def _init_session(self, entry: SignInEntry) -> None:
        """初始化session"""
        if not self.session:
            self.session = requests.Session()
            if entry_headers := entry.get('headers'):
                self.session.headers.update(entry_headers)
            if entry_cookie := entry.get('cookie'):
                cookies = net_utils.cookie_str_to_dict(entry_cookie)
                self.session.cookies.update(cookies)
            self.session.mount('http://', HTTPAdapter(max_retries=2))
            self.session.mount('https://', HTTPAdapter(max_retries=2))

    def _update_session_cookie(self, entry: SignInEntry) -> None:
        """更新session cookie到entry中"""
        if self.session:
            cookie_items = self.session.cookies.items()
            session_cookie = ' '.join([f'{k}={v};' for k, v in cookie_items])
            entry['session_cookie'] = session_cookie

    def _get_browser_manager(self, config: Optional[dict] = None):
        """获取浏览器管理器实例"""
        if self._browser_manager is None:
            try:
                from ..utils import get_browser_manager
                # 确保传递完整的配置
                use_config = config or {}
                logger.info(f"传递给浏览器管理器的配置keys: {list(use_config.keys())}")
                logger.info(f"browser_automation配置: {use_config.get('browser_automation', 'NOT_FOUND')}")
                self._browser_manager = get_browser_manager(use_config)
            except ImportError as e:
                logger.error(f"浏览器管理器导入失败: {e}")
                return None
            except Exception as e:
                logger.error(f"浏览器管理器创建失败: {e}")
                return None
        return self._browser_manager

    def _should_use_browser(self, entry: SignInEntry, config: Optional[dict] = None) -> bool:
        """检查是否应该使用浏览器模拟"""
        # 检查是否强制使用浏览器
        if entry.get('force_browser', False):
            return True

        # 检查配置中的请求方法
        request_method = entry.get('request_method', RequestMethod.AUTO.value)
        if request_method == RequestMethod.BROWSER.value:
            return True

        # 自动检测：如果检测到Cloudflare，使用浏览器
        if request_method == RequestMethod.AUTO.value:
            # 这里可以添加更智能的检测逻辑
            return False

        return False

    def _request_with_browser(self,
                             entry: SignInEntry,
                             method: str,
                             url: str,
                             config: Optional[dict] = None,
                             **kwargs) -> Response | None:
        """使用浏览器自动化发送请求"""
        try:
            browser_manager = self._get_browser_manager(config)
            if not browser_manager:
                logger.error("浏览器管理器不可用")
                entry.fail_with_prefix("Browser manager not available")
                return None

            # 获取站点名称（从entry或URL推断）
            site_name = entry.get('site_name') or self._extract_site_name(url) or 'default'

            # 获取站点专用tab页面（先设置cookie再使用）
            page = browser_manager.get_site_tab(site_name, headless=True)

            try:
                # 设置cookies
                if entry_cookie := entry.get('cookie'):
                    # 处理相对URL和绝对URL
                    if url.startswith('http'):
                        # 绝对URL
                        url_parts = url.split('/')
                        base_url = f"{url_parts[0]}//{url_parts[2]}"
                    else:
                        # 相对URL，从entry中获取站点URL
                        site_url = entry.get('url', '')
                        if site_url.startswith('http'):
                            site_parts = site_url.split('/')
                            base_url = f"{site_parts[0]}//{site_parts[2]}"
                        else:
                            # 备用方案：从站点类获取URL
                            base_url = getattr(entry, 'URL', 'https://hdsky.me')
                            if not base_url.startswith('http'):
                                base_url = f"https://{base_url}"

                    browser_manager.set_cookies(page, entry_cookie, base_url)

                # 构建完整URL
                if not url.startswith('http'):
                    # 相对URL，需要构建完整URL
                    if url.startswith('/'):
                        full_url = base_url + url
                    else:
                        full_url = base_url + '/' + url
                else:
                    full_url = url

                logger.info(f"浏览器访问: {full_url}")

                # 访问页面
                if method.upper() == 'GET':
                    page.get(full_url)
                elif method.upper() == 'POST':
                    # 对于POST请求，先访问页面再提交表单
                    page.get(full_url)
                    # 这里可以添加表单提交逻辑
                    logger.warning("POST请求的表单提交功能待实现")
                else:
                    logger.error(f"浏览器不支持的请求方法: {method}")
                    return None

                # 检查是否需要Cloudflare绕过
                success_indicators = entry.get('success_indicators', {})
                cf_bypass = browser_manager.create_cloudflare_bypass(
                    page, site_name, {site_name: success_indicators} if site_name else None
                )
                bypass_success = cf_bypass.bypass()

                if not bypass_success:
                    logger.warning("Cloudflare绕过失败")
                    entry.fail_with_prefix("Cloudflare bypass failed")
                    return None

                # 更新entry中的cookie
                try:
                    # 获取页面cookies并更新到entry
                    cookies = page.get_cookies()
                    if cookies:
                        cookie_list = []
                        for cookie in cookies:
                            cookie_list.append(f"{cookie['name']}={cookie['value']}")
                        entry['session_cookie'] = '; '.join(cookie_list)
                except Exception as e:
                    logger.debug(f"更新cookie失败: {e}")

                # 创建响应对象
                response = BrowserResponse(page, url)

                # 签到完成后关闭站点tab页面
                try:
                    browser_manager.close_site_tab(site_name)
                    logger.debug(f"站点 {site_name} 的tab页面已关闭")
                except Exception as e:
                    logger.warning(f"关闭站点 {site_name} tab失败: {e}")

                return response

            except Exception as e:
                logger.error(f"浏览器请求执行失败: {e}")
                import traceback
                logger.error(f"错误详情: {traceback.format_exc()}")
                entry.fail_with_prefix(f"Browser request failed: {e}")

                # 即使出错也要尝试关闭tab
                try:
                    browser_manager.close_site_tab(site_name)
                except:
                    pass

                return None

        except Exception as e:
            logger.error(f"浏览器请求错误: {e}")
            entry.fail_with_prefix(f"Browser request error: {e}")

            # 即使出错也要尝试关闭tab
            try:
                browser_manager = self._get_browser_manager(config)
                if browser_manager:
                    site_name = entry.get('site_name') or self._extract_site_name(url) or 'default'
                    browser_manager.close_site_tab(site_name)
            except:
                pass

            return None

    def _extract_site_name(self, url: str) -> Optional[str]:
        """从URL提取站点名称"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # 简单的站点名称映射
            site_mapping = {
                'pt.btschool.club': 'btschool',
                'hdsky.me': 'hdsky',
                'hdtime.org': 'hdtime',
            }

            return site_mapping.get(domain)
        except Exception:
            return None

    def _request_with_standard(self,
                              entry: SignInEntry,
                              method: str,
                              url: str,
                              config: Optional[dict] = None,
                              **kwargs) -> Response | None:
        """使用标准requests发送请求"""
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
                entry.fail_with_prefix(
                    f'url: {url} detected CloudFlare DDoS-GUARD. '
                    'Consider using browser automation.'
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






class SmartRequest(BaseRequest):
    """智能请求实现类 - 自动选择最佳请求方式"""

    def __init__(self):
        super().__init__()

    def request(self,
                entry: SignInEntry,
                method: str,
                url: str,
                config: Optional[dict] = None,
                force_default: bool = False,
                **kwargs,
                ) -> Response | None:
        """智能请求 - 自动选择最佳请求方式"""

        # 如果强制使用默认方式，直接使用标准请求
        if force_default:
            logger.debug("强制使用标准请求方式")
            return self._request_with_standard(entry, method, url, config, **kwargs)

        # 智能选择请求方式
        request_method = self._determine_request_method(entry, config)

        logger.info(f"选择请求方式: {request_method}")

        if request_method == RequestMethod.BROWSER:
            return self._request_with_browser(entry, method, url, config, **kwargs)
        else:
            return self._request_with_standard(entry, method, url, config, **kwargs)

    def _determine_request_method(self, entry: SignInEntry, config: Optional[dict] = None) -> RequestMethod:
        """智能确定请求方式"""

        # 检查entry中的显式配置
        explicit_method = entry.get('request_method')
        if explicit_method:
            try:
                return RequestMethod(explicit_method)
            except ValueError:
                logger.warning(f"无效的请求方法: {explicit_method}")

        # 检查是否强制使用浏览器
        if entry.get('force_browser', False):
            return RequestMethod.BROWSER

        # 检查站点特定配置
        site_name = entry.get('site_name') or self._extract_site_name(entry.get('url', ''))
        if site_name:
            # 某些站点默认使用浏览器
            browser_sites = ['btschool', 'hdsky', 'hdtime']  # 可配置
            if site_name in browser_sites:
                logger.debug(f"站点 {site_name} 默认使用浏览器模拟")
                return RequestMethod.BROWSER

        # 默认使用标准请求
        return RequestMethod.DEFAULT

    def _request_with_standard(self, entry: SignInEntry, method: str, url: str,
                              config: Optional[dict] = None, **kwargs) -> Response | None:
        """使用标准requests发送请求"""
        try:
            self._init_session(entry)

            logger.debug(f"标准请求: {method} {url}")

            response = self.session.request(method, url, **kwargs)

            # 检查Cloudflare
            if cf_detected(response):
                logger.warning(f"检测到Cloudflare保护: {url}")
                entry.fail_with_prefix(
                    f'url: {url} detected CloudFlare DDoS-GUARD. '
                    'Consider using browser automation.'
                )
            elif response is not None and response.status_code != 200:
                entry.fail_with_prefix(
                    f'url: {url} response.status_code={response.status_code}'
                )

            # 更新session cookie
            self._update_session_cookie(entry)

            return response

        except Exception as e:
            logger.error(f"标准请求失败: {e}")
            entry.fail_with_prefix(
                NetworkState.NETWORK_ERROR.value.format(url=url, error=e)
            )
        return None


class StandardRequest(BaseRequest):
    """标准HTTP请求实现类"""

    def request(self,
                entry: SignInEntry,
                method: str,
                url: str,
                config: Optional[dict] = None,
                force_default: bool = False,
                **kwargs,
                ) -> Response | None:
        """使用标准requests发送请求"""
        self._init_session(entry)

        try:
            response: Response = self.session.request(
                method, url, timeout=60, **kwargs
            )

            # 检测Cloudflare保护
            if cf_detected(response):
                entry.fail_with_prefix(
                    f'url: {url} detected CloudFlare DDoS-GUARD. '
                    'Consider using browser automation.'
                )
            elif response is not None and response.status_code != 200:
                entry.fail_with_prefix(
                    f'url: {url} response.status_code={response.status_code}'
                )

            # 更新session cookie
            self._update_session_cookie(entry)

            return response

        except Exception as e:
            entry.fail_with_prefix(
                NetworkState.NETWORK_ERROR.value.format(url=url, error=e)
            )
        return None


class BrowserAutomationRequest(BaseRequest):
    """浏览器自动化请求实现类"""

    def request(self,
                entry: SignInEntry,
                method: str,
                url: str,
                config: Optional[dict] = None,
                force_default: bool = False,
                **kwargs,
                ) -> Response | None:
        """使用浏览器自动化发送请求"""
        # 如果强制使用默认方式，回退到标准请求
        if force_default:
            standard_request = StandardRequest()
            return standard_request.request(entry, method, url, config,
                                          force_default, **kwargs)

        try:
            from ..utils.browser_automation import BrowserAutomation

            browser_config = config.get('browser_automation', {}) if config else {}
            browser = BrowserAutomation(browser_config)

            try:
                # 这里可以根据需要实现具体的浏览器自动化逻辑
                # 目前返回None，表示暂未实现
                logger.warning("Browser automation not yet implemented")
                entry.fail_with_prefix("Browser automation not yet implemented")
                return None
            finally:
                if hasattr(browser, 'quit'):
                    browser.quit()

        except ImportError:
            logger.error("Browser automation dependencies not available")
            entry.fail_with_prefix("Browser automation not available")
            return None
        except Exception as e:
            logger.error(f"Browser automation error: {e}")
            entry.fail_with_prefix(f"Browser automation error: {e}")
            return None


class RequestFactory:
    """请求工厂类，根据配置创建相应的Request实例"""

    @staticmethod
    def create_request(entry: SignInEntry,
                      config: Optional[dict] = None) -> BaseRequest:
        """
        根据配置创建相应的Request实例

        Args:
            entry: 签到条目
            config: 配置字典

        Returns:
            BaseRequest实例
        """
        # 新版本统一使用SmartRequest，它会自动选择最佳请求方式
        logger.debug("创建SmartRequest实例")
        return SmartRequest()

    @staticmethod
    def create_legacy_request(entry: SignInEntry,
                            config: Optional[dict] = None) -> BaseRequest:
        """
        创建传统的Request实例（保持向后兼容）

        Args:
            entry: 签到条目
            config: 配置字典

        Returns:
            BaseRequest实例
        """
        method_type = RequestFactory._get_method_type_from_config(entry, config)

        if method_type == RequestMethod.BROWSER:
            return BrowserAutomationRequest()
        elif method_type == RequestMethod.DEFAULT:
            return StandardRequest()
        elif method_type == RequestMethod.AUTO:
            # 使用SmartRequest进行智能选择
            return SmartRequest()
        else:
            # 默认使用SmartRequest
            logger.warning(f"Unknown method_type: {method_type}, using SmartRequest")
            return SmartRequest()

    @staticmethod
    def _get_method_type_from_config(entry: SignInEntry,
                                   config: Optional[dict]) -> RequestMethod:
        """从配置中获取请求方法类型"""
        if not config:
            return RequestMethod.AUTO

        site_name = entry.get('title', '').lower()

        # 1. 检查站点特定的request_method配置
        site_config = config.get('sites', {}).get(site_name, {})
        if isinstance(site_config, dict) and 'request_method' in site_config:
            method_str = site_config['request_method'].upper()
            try:
                return RequestMethod(method_str.lower())
            except ValueError:
                logger.warning(
                    f"Invalid request_method '{method_str}' for site "
                    f"{site_name}, using AUTO"
                )

        # 2. 检查全局request_method配置
        global_method = config.get('request_method', '').upper()
        if global_method:
            try:
                return RequestMethod(global_method.lower())
            except ValueError:
                logger.warning(
                    f"Invalid global request_method '{global_method}', "
                    f"using AUTO"
                )

        # 3. 默认使用AUTO模式
        return RequestMethod.AUTO




# 便捷函数
def create_request(entry: SignInEntry, config: Optional[dict] = None) -> BaseRequest:
    """
    创建请求实例的便捷函数

    Args:
        entry: 签到条目
        config: 配置字典

    Returns:
        BaseRequest实例
    """
    return RequestFactory.create_request(entry, config)


# 向后兼容的别名
FlareSolverrRequest = SmartRequest  # 保持向后兼容性
