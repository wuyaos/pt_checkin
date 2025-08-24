"""
统一工具模块 - 合并重复功能
整合了网络状态处理、Cookie处理、URL处理等通用功能
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Dict, List, Optional
from urllib.parse import urlparse

import chardet
from requests import Response

# ============================================================================
# 网络状态统一处理
# ============================================================================


class NetworkState(Enum):
    """统一的网络状态枚举 - 合并原有的NetworkState和NetworkErrorReason"""

    # 基础状态
    SUCCEED = "Succeed"
    URL_REDIRECT = "Url: {original_url} redirect to {redirect_url}"
    NETWORK_ERROR = "Network error: url: {url}, error: {error}"
    MAINTENANCE = "Site under maintenance: {url}"
    CLOUDFLARE_BLOCKED = "Cloudflare protection detected: {url}"

    # 具体错误模式 (原NetworkErrorReason)
    DDOS_PROTECTION_BY_CLOUDFLARE = "DDoS protection by .+?Cloudflare"
    SERVER_LOAD_TOO_HIGH = r"<h3 align=center>(服务器负载过|伺服器負載過)高，正在重(试|試)，(请|請)稍(后|後)\.\.\.</h3>"
    CONNECTION_TIMED_OUT = r'<h2 class="text-gray-600 leading-1\.3 text-3xl font-light">Connection timed out</h2>'
    THE_WEB_SERVER_REPORTED_A_BAD_GATEWAY_ERROR = (
        r"<p>The web server reported a bad gateway error\.</p>"
    )
    WEB_SERVER_IS_DOWN = "站点关闭维护中，请稍后再访问...谢谢|站點關閉維護中，請稍後再訪問...謝謝|Web server is down"
    INCORRECT_CSRF_TOKEN = "Incorrect CSRF token"


class SignState(Enum):
    """签到状态枚举"""

    NO_SIGN_IN = "No sign in"
    SUCCEED = "Succeed"
    WRONG_ANSWER = "Wrong answer"
    SIGN_IN_FAILED = "Sign in failed, {}"
    UNKNOWN = "Unknown, url: {}"


# ============================================================================
# Cookie处理统一工具
# ============================================================================


class CookieUtils:
    """Cookie处理统一工具类"""

    @staticmethod
    def str_to_dict(cookie_str: str) -> Dict[str, str]:
        """
        将cookie字符串转换为字典

        Args:
            cookie_str: cookie字符串，格式如 "name1=value1; name2=value2"

        Returns:
            Dict[str, str]: cookie字典
        """
        cookie_dict = {}
        if not cookie_str:
            return cookie_dict

        for line in cookie_str.split(";"):
            line = line.strip()
            if "=" in line:
                name, value = line.split("=", 1)
                cookie_dict[name.strip()] = value.strip()
        return cookie_dict

    @staticmethod
    def dict_to_str(cookie_dict: Dict[str, str]) -> str:
        """
        将cookie字典转换为字符串

        Args:
            cookie_dict: cookie字典

        Returns:
            str: cookie字符串
        """
        if not cookie_dict:
            return ""

        cookie_array = []
        for name, value in cookie_dict.items():
            cookie_array.append(f"{name}={value}")
        return "; ".join(cookie_array)

    @staticmethod
    def list_to_str(cookie_items: List[tuple]) -> str:
        """
        将cookie列表转换为字符串

        Args:
            cookie_items: cookie元组列表 [(name, value), ...]

        Returns:
            str: cookie字符串
        """
        if not cookie_items:
            return ""

        cookie_array = []
        for name, value in cookie_items:
            cookie_array.append(f"{name}={value}")
        return "; ".join(cookie_array)


# ============================================================================
# URL处理统一工具
# ============================================================================


class UrlUtils:
    """URL处理统一工具类"""

    @staticmethod
    def extract_site_name(url: str) -> Optional[str]:
        """
        从URL中提取站点名称

        Args:
            url: 完整的URL

        Returns:
            Optional[str]: 站点名称，如果提取失败返回None
        """
        if not url:
            return None

        try:
            # 方法1：使用正则表达式 (原net_utils.py的方法)
            if (re_object := re.search("(?<=//).*?(?=/)", url)) and len(
                domain := re_object.group().split(".")
            ) > 1:
                site_name = domain[len(domain) - 2]
                return site_name if site_name != "edu" else domain[len(domain) - 3]

            # 方法2：使用urlparse作为备选 (更健壮)
            parsed = urlparse(url)
            if parsed.netloc:
                domain_parts = parsed.netloc.split(".")
                if len(domain_parts) >= 2:
                    site_name = domain_parts[-2]
                    return (
                        site_name
                        if site_name != "edu"
                        else domain_parts[-3] if len(domain_parts) >= 3 else site_name
                    )

            return None

        except Exception:
            return None

    @staticmethod
    def get_base_domain(url: str) -> Optional[str]:
        """
        获取URL的基础域名

        Args:
            url: 完整的URL

        Returns:
            Optional[str]: 基础域名，如果提取失败返回None
        """
        if not url:
            return None

        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else None
        except Exception:
            return None


# ============================================================================
# 响应处理统一工具
# ============================================================================


class ResponseUtils:
    """响应处理统一工具类"""

    @staticmethod
    def decode_response(response: Optional[Response]) -> Optional[str]:
        """
        解码HTTP响应内容

        Args:
            response: HTTP响应对象

        Returns:
            Optional[str]: 解码后的文本内容
        """
        if response is None:
            return None

        try:
            content = response.content
            charset_encoding = chardet.detect(content).get("encoding")

            # 处理特殊编码
            if charset_encoding == "ascii":
                charset_encoding = "unicode_escape"
            elif charset_encoding in ["Windows-1254", "MacRoman"]:
                charset_encoding = "utf-8"

            return content.decode(
                charset_encoding if charset_encoding else "utf-8", "ignore"
            )
        except Exception:
            return None


# ============================================================================
# 通用工具函数
# ============================================================================


def get_module_name(cls) -> str:
    """
    获取类的模块名称

    Args:
        cls: 类对象

    Returns:
        str: 模块名称
    """
    return cls.__module__.rsplit(".", maxsplit=1)[-1]


def dict_merge(dict1: dict, dict2: dict) -> None:
    """
    深度合并两个字典

    Args:
        dict1: 目标字典（会被修改）
        dict2: 源字典
    """
    for key in dict2:
        if isinstance(dict1.get(key), dict) and isinstance(dict2.get(key), dict):
            dict_merge(dict1[key], dict2[key])
        else:
            dict1[key] = dict2[key]


# ============================================================================
# 向后兼容性支持
# ============================================================================

# 为了保持向后兼容，提供原有函数的别名
cookie_str_to_dict = CookieUtils.str_to_dict
cookie_to_str = CookieUtils.list_to_str
get_site_name = UrlUtils.extract_site_name
decode = ResponseUtils.decode_response
