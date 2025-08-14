"""
FlareSolverr集成模块
用于绕过Cloudflare保护和处理JavaScript渲染页面
"""

from __future__ import annotations

import json
import time
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests
from loguru import logger

from ..core.entry import SignInEntry


class FlareSolverrClient:
    """FlareSolverr客户端"""
    
    def __init__(self, server_url: str, timeout: int = 60):
        """
        初始化FlareSolverr客户端
        
        Args:
            server_url: FlareSolverr服务器地址，如 http://localhost:8191
            timeout: 请求超时时间（秒）
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.session_id = None
    
    def create_session(self, proxy: Optional[str] = None) -> bool:
        """
        创建浏览器会话
        
        Args:
            proxy: 代理设置，格式如 http://proxy:port
            
        Returns:
            bool: 是否创建成功
        """
        try:
            data = {
                "cmd": "sessions.create",
                "proxy": proxy
            }
            
            response = requests.post(
                f"{self.server_url}/v1",
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "ok":
                    self.session_id = result.get("session")
                    logger.info(f"FlareSolverr session created: {self.session_id}")
                    return True
            
            logger.error(f"Failed to create FlareSolverr session: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"FlareSolverr session creation error: {e}")
            return False
    
    def destroy_session(self) -> bool:
        """销毁浏览器会话"""
        if not self.session_id:
            return True
            
        try:
            data = {
                "cmd": "sessions.destroy",
                "session": self.session_id
            }
            
            response = requests.post(
                f"{self.server_url}/v1",
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "ok":
                    logger.info(f"FlareSolverr session destroyed: {self.session_id}")
                    self.session_id = None
                    return True
            
            logger.error(f"Failed to destroy FlareSolverr session: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"FlareSolverr session destruction error: {e}")
            return False
    
    def request_get(self, url: str, headers: Optional[Dict[str, str]] = None,
                   cookies: Optional[Dict[str, str]] = None,
                   max_timeout: int = 60000) -> Optional[Dict[str, Any]]:
        """
        通过FlareSolverr发送GET请求

        Args:
            url: 目标URL
            headers: 请求头（FlareSolverr v2中已移除，仅保留兼容性）
            cookies: Cookie字典
            max_timeout: 最大超时时间（毫秒）

        Returns:
            Dict: 包含响应内容的字典，或None如果失败
        """
        try:
            data = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": max_timeout
            }

            if self.session_id:
                data["session"] = self.session_id

            # FlareSolverr v2移除了headers参数，不再添加
            # if headers:
            #     data["headers"] = headers

            if cookies:
                data["cookies"] = [
                    {"name": k, "value": v} for k, v in cookies.items()
                ]
            
            response = requests.post(
                f"{self.server_url}/v1",
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "ok":
                    return result.get("solution", {})
            
            logger.error(f"FlareSolverr request failed: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"FlareSolverr request error: {e}")
            return None
    
    def request_post(self, url: str, post_data: str,
                    headers: Optional[Dict[str, str]] = None,
                    cookies: Optional[Dict[str, str]] = None,
                    max_timeout: int = 60000) -> Optional[Dict[str, Any]]:
        """
        通过FlareSolverr发送POST请求

        Args:
            url: 目标URL
            post_data: POST数据（字符串格式）
            headers: 请求头（FlareSolverr v2中已移除，仅保留兼容性）
            cookies: Cookie字典
            max_timeout: 最大超时时间（毫秒）

        Returns:
            Dict: 包含响应内容的字典，或None如果失败
        """
        try:
            data = {
                "cmd": "request.post",
                "url": url,
                "postData": post_data,
                "maxTimeout": max_timeout
            }

            if self.session_id:
                data["session"] = self.session_id

            # FlareSolverr v2移除了headers参数，不再添加
            # if headers:
            #     data["headers"] = headers

            if cookies:
                data["cookies"] = [
                    {"name": k, "value": v} for k, v in cookies.items()
                ]
            
            response = requests.post(
                f"{self.server_url}/v1",
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "ok":
                    return result.get("solution", {})
            
            logger.error(f"FlareSolverr POST request failed: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"FlareSolverr POST request error: {e}")
            return None


def cookie_str_to_dict(cookie_str: str) -> Dict[str, str]:
    """将cookie字符串转换为字典格式"""
    cookie_dict = {}
    for item in cookie_str.split(';'):
        if '=' in item:
            key, value = item.split('=', 1)
            cookie_dict[key.strip()] = value.strip()
    return cookie_dict


def get_flaresolverr_client(config: dict) -> Optional[FlareSolverrClient]:
    """
    从配置中获取FlareSolverr客户端
    
    Args:
        config: 配置字典
        
    Returns:
        FlareSolverrClient: 客户端实例，或None如果未配置
    """
    flaresolverr_config = config.get('flaresolverr')
    if not flaresolverr_config:
        return None
    
    if isinstance(flaresolverr_config, str):
        # 简单字符串配置，仅包含服务器URL
        return FlareSolverrClient(flaresolverr_config)
    elif isinstance(flaresolverr_config, dict):
        # 详细配置
        server_url = flaresolverr_config.get('server_url')
        if not server_url:
            return None
        
        timeout = flaresolverr_config.get('timeout', 60)
        return FlareSolverrClient(server_url, timeout)
    
    return None


def should_use_flaresolverr(entry: SignInEntry, config: dict) -> bool:
    """
    判断是否应该使用FlareSolverr
    
    Args:
        entry: 签到条目
        config: 配置字典
        
    Returns:
        bool: 是否使用FlareSolverr
    """
    flaresolverr_config = config.get('flaresolverr')
    if not flaresolverr_config:
        return False
    
    # 检查全局启用设置
    if isinstance(flaresolverr_config, dict):
        # 检查是否全局启用
        if flaresolverr_config.get('enable_all', False):
            return True
        
        # 检查站点特定设置
        enabled_sites = flaresolverr_config.get('enabled_sites', [])
        site_name = entry.get('site_name', '')
        return site_name in enabled_sites
    
    # 如果是字符串配置，默认不启用（需要在站点配置中明确指定）
    return False
