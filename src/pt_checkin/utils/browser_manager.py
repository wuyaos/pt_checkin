#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一浏览器管理模块
合并了browser_manager、browser_automation、cloudflare_bypass的功能
支持Cloudflare绕过、验证码处理、特殊站点签到流程
"""

import os
import time
from typing import Optional, Dict, Any, List

from loguru import logger

# 动态导入DrissionPage
try:
    from DrissionPage import ChromiumPage, ChromiumOptions
    DRISSIONPAGE_AVAILABLE = True
except ImportError:
    DRISSIONPAGE_AVAILABLE = False
    ChromiumPage = None
    ChromiumOptions = None


class UnifiedBrowserManager:
    """统一浏览器管理器 - 集成所有浏览器相关功能"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化统一浏览器管理器

        Args:
            config: 浏览器配置字典
        """
        self.config = config or {}
        self.browser_config = self.config.get('browser_automation', {})
        self._main_page = None  # 主浏览器页面
        self._tab_cache = {}  # tab缓存，key为站点名，value为tab页面
        
    def is_available(self) -> bool:
        """检查DrissionPage是否可用"""
        return DRISSIONPAGE_AVAILABLE
    
    def get_missing_dependency_message(self) -> str:
        """获取缺失依赖的提示信息"""
        return "DrissionPage未安装，请运行: pip install DrissionPage"
        
    def create_browser_options(self, headless: bool = True, 
                             site_specific: bool = False) -> ChromiumOptions:
        """
        创建浏览器选项配置
        
        Args:
            headless: 是否使用无头模式
            site_specific: 是否使用站点特定配置
            
        Returns:
            ChromiumOptions: 配置好的浏览器选项
        """
        if not DRISSIONPAGE_AVAILABLE:
            raise ImportError(self.get_missing_dependency_message())
            
        co = ChromiumOptions()
        co.auto_port()
        co.set_timeouts(base=1)
        
        # 设置无头模式
        if headless and self.browser_config.get('headless', True):
            co.headless()
            logger.debug("启用无头模式（不显示浏览器窗口）")
        
        # 从配置文件获取浏览器设置
        logger.debug(f"浏览器配置: {self.browser_config}")
        browser_path = self.browser_config.get('browser_path', '')
        logger.debug(f"配置的浏览器路径: {browser_path}")
        
        if browser_path and os.path.exists(browser_path):
            co.set_browser_path(browser_path)
            logger.debug(f"使用配置的浏览器路径: {browser_path}")
        else:
            if browser_path:
                logger.warning(f"配置的浏览器路径不存在: {browser_path}")
            else:
                logger.warning("未配置浏览器路径，将使用DrissionPage自动检测")
        
        # 设置用户代理
        user_agent = self.browser_config.get('user_agent', 
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36')
        co.set_user_agent(user_agent)
        
        # 反检测参数
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        co.set_argument('--disable-web-security')
        co.set_argument('--allow-running-insecure-content')
        co.set_argument('--disable-extensions')
        co.set_argument('--disable-plugins')
        co.set_argument('--disable-images')  # 禁用图片加载以提高速度
        
        # 添加自定义参数
        additional_args = self.browser_config.get('browser_arguments', [])
        for arg in additional_args:
            co.set_argument(arg)
        
        logger.debug(f"浏览器参数配置完成，共{len(co._arguments)}个参数")
        return co
    
    def get_main_page(self, headless: bool = True) -> Optional[ChromiumPage]:
        """
        获取或创建主浏览器页面

        Args:
            headless: 是否使用无头模式

        Returns:
            ChromiumPage: 主浏览器页面实例
        """
        if not DRISSIONPAGE_AVAILABLE:
            logger.error("创建浏览器页面失败: DrissionPage不可用")
            return None

        # 检查主页面是否存在且有效
        if self._main_page:
            try:
                # 测试页面是否仍然有效
                _ = self._main_page.url
                logger.debug("使用现有的主浏览器页面")
                return self._main_page
            except Exception:
                # 页面已失效，重新创建
                self._main_page = None
                self._tab_cache.clear()  # 清空tab缓存
                logger.debug("主页面已失效，重新创建")

        try:
            # 创建新的主页面
            options = self.create_browser_options(headless=headless)
            self._main_page = ChromiumPage(addr_or_opts=options)

            logger.info("创建新的主浏览器页面")
            return self._main_page

        except Exception as e:
            logger.error(f"创建主浏览器页面失败: {e}")
            return None

    def get_site_tab(self, site_name: str, headless: bool = True) -> Optional[ChromiumPage]:
        """
        获取或创建站点专用tab页面

        Args:
            site_name: 站点名称
            headless: 是否使用无头模式

        Returns:
            ChromiumPage: 站点tab页面实例
        """
        # 确保主页面存在
        main_page = self.get_main_page(headless)
        if not main_page:
            return None

        # 检查站点tab是否已存在
        if site_name in self._tab_cache:
            tab = self._tab_cache[site_name]
            try:
                # 测试tab是否仍然有效
                _ = tab.url
                logger.debug(f"使用现有的站点tab: {site_name}")
                return tab
            except Exception:
                # tab已失效，从缓存中移除
                del self._tab_cache[site_name]
                logger.debug(f"站点tab已失效，重新创建: {site_name}")

        try:
            # 创建新tab
            new_tab = main_page.new_tab()
            self._tab_cache[site_name] = new_tab

            logger.info(f"为站点创建新tab: {site_name}")
            return new_tab

        except Exception as e:
            logger.error(f"创建站点tab失败: {site_name} - {e}")
            return None
    
    def set_cookies(self, page: ChromiumPage, cookie_str: str, domain: str):
        """
        设置页面cookies
        
        Args:
            page: 浏览器页面实例
            cookie_str: cookie字符串
            domain: 域名
        """
        try:
            # 先访问基础域名以设置cookie上下文
            if not domain.startswith('http'):
                domain = f"https://{domain}"
            
            logger.debug(f"访问基础域名设置cookie上下文: {domain}")
            page.get(domain)
            
            # 解析cookie字符串并设置
            cookies = self._parse_cookie_string(cookie_str)
            for cookie in cookies:
                try:
                    page.set.cookies(cookie)
                    logger.debug(f"设置cookie: {cookie['name']}")
                except Exception as e:
                    logger.warning(f"设置cookie失败: {cookie.get('name', 'unknown')} - {e}")
                    
            logger.info(f"Cookie设置完成，共{len(cookies)}个")
            
        except Exception as e:
            logger.error(f"设置cookies失败: {e}")
    
    def _parse_cookie_string(self, cookie_str: str) -> List[Dict[str, Any]]:
        """解析cookie字符串为字典列表"""
        cookies = []
        if not cookie_str:
            return cookies
            
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip()
                })
        return cookies
    
    def close_site_tab(self, site_name: str):
        """关闭指定站点的tab"""
        if site_name in self._tab_cache:
            try:
                tab = self._tab_cache[site_name]
                tab.close()
                del self._tab_cache[site_name]
                logger.debug(f"关闭站点tab: {site_name}")
            except Exception as e:
                logger.warning(f"关闭站点tab失败: {site_name} - {e}")

    def close_all_tabs(self):
        """关闭所有站点tab，但保留主页面"""
        for site_name in list(self._tab_cache.keys()):
            self.close_site_tab(site_name)
        logger.info("所有站点tab已关闭")

    def close_browser(self):
        """完全关闭浏览器"""
        try:
            # 先关闭所有tab
            self.close_all_tabs()

            # 关闭主页面
            if self._main_page:
                self._main_page.quit()
                self._main_page = None
                logger.info("主浏览器页面已关闭")

        except Exception as e:
            logger.warning(f"关闭浏览器失败: {e}")

        # 清空缓存
        self._tab_cache.clear()
        logger.info("浏览器资源清理完成")

    def cleanup(self):
        """清理资源（向后兼容）"""
        self.close_browser()

    # ==================== Cloudflare绕过功能 ====================

    def create_cloudflare_bypass(self, page: ChromiumPage, site_name: Optional[str] = None,
                               success_indicators: Optional[Dict[str, Any]] = None):
        """
        创建Cloudflare绕过处理器

        Args:
            page: 浏览器页面实例
            site_name: 站点名称
            success_indicators: 成功标识配置

        Returns:
            CloudflareBypass: Cloudflare绕过处理器实例
        """
        return CloudflareBypass(page, site_name, success_indicators)


class CloudflareBypass:
    """Cloudflare绕过处理类"""

    def __init__(self, page: ChromiumPage, site_name: Optional[str] = None,
                 success_indicators: Optional[Dict[str, Any]] = None):
        """
        初始化Cloudflare绕过处理器

        Args:
            page: DrissionPage的ChromiumPage实例
            site_name: 站点名称
            success_indicators: 站点特定的成功标识配置
        """
        self.page = page
        self.site_name = site_name
        self.success_indicators = success_indicators or {}

        # 默认成功标识配置
        self.default_indicators = {
            'btschool': {
                'logo': 'class="logo">BTSCHOOL</div>',
                'slogan': '汇聚每一个人的影响力',
                'keywords': ['种子', 'torrent', '用户']
            },
            'hdsky': {
                'logo': 'HDSky',
                'keywords': ['种子', 'torrent', '用户', '下载']
            },
            'hdtime': {
                'logo': 'HDTime',
                'keywords': ['种子', 'torrent', '用户', '下载']
            }
        }

    def detect_shield_type(self) -> str:
        """
        检测Cloudflare盾类型

        Returns:
            str: 盾类型 ('5s', 'turnstile', 'none', 'unknown')
        """
        try:
            page_source = self.page.html

            # 检测5秒盾
            if any(keyword in page_source for keyword in [
                'Checking your browser',
                '正在检查您的浏览器',
                'DDoS protection by Cloudflare',
                'cf-browser-verification'
            ]):
                logger.info("检测到Cloudflare 5秒盾")
                return '5s'

            # 检测Turnstile验证
            if any(keyword in page_source for keyword in [
                'cf-turnstile',
                'turnstile',
                'Verify you are human',
                '验证您是人类'
            ]):
                logger.info("检测到Cloudflare Turnstile验证")
                return 'turnstile'

            # 检测其他Cloudflare标识
            if any(keyword in page_source for keyword in [
                'cloudflare',
                'cf-ray',
                '__cf_bm'
            ]):
                logger.info("检测到Cloudflare，但类型未知")
                return 'unknown'

            # 检查是否已经成功进入站点
            if self._check_site_success():
                logger.info("检测到站点内容，无Cloudflare挑战")
                return 'none'

            logger.info("未检测到Cloudflare挑战")
            return 'none'

        except Exception as e:
            logger.error(f"检测盾类型失败: {e}")
            return 'unknown'

    def _check_site_success(self) -> bool:
        """检查是否成功进入站点"""
        try:
            page_source = self.page.html

            # 获取站点特定的成功标识
            indicators = self.success_indicators.get(self.site_name, {})
            if not indicators:
                indicators = self.default_indicators.get(self.site_name, {})

            # 检查logo
            if 'logo' in indicators:
                if indicators['logo'] in page_source:
                    logger.debug(f"检测到站点logo: {self.site_name}")
                    return True

            # 检查slogan
            if 'slogan' in indicators:
                if indicators['slogan'] in page_source:
                    logger.debug(f"检测到站点slogan: {self.site_name}")
                    return True

            # 检查关键词
            if 'keywords' in indicators:
                for keyword in indicators['keywords']:
                    if keyword in page_source:
                        logger.debug(f"检测到站点关键词: {keyword}")
                        return True

            return False

        except Exception as e:
            logger.error(f"检查站点成功标识失败: {e}")
            return False

    def bypass(self) -> bool:
        """
        执行Cloudflare绕过

        Returns:
            bool: 是否成功绕过
        """
        try:
            shield_type = self.detect_shield_type()

            if shield_type == 'none':
                logger.info("无需Cloudflare绕过")
                return True
            elif shield_type == '5s':
                return self._handle_5s_shield()
            elif shield_type == 'turnstile':
                return self._handle_turnstile()
            else:
                logger.warning(f"未知的盾类型: {shield_type}，尝试通用处理")
                return self._handle_unknown_shield()

        except Exception as e:
            logger.error(f"Cloudflare绕过失败: {e}")
            return False

    def _handle_5s_shield(self) -> bool:
        """处理5秒盾"""
        logger.info("开始处理5秒盾...")

        # 等待5秒盾自动通过
        max_wait = 15  # 最多等待15秒
        start_time = time.time()

        while time.time() - start_time < max_wait:
            time.sleep(1)

            # 检查是否已经通过
            if self._check_site_success():
                logger.success("5秒盾已通过")
                return True

            # 检查是否还在5秒盾页面
            current_type = self.detect_shield_type()
            if current_type != '5s':
                if current_type == 'none':
                    logger.success("5秒盾已通过")
                    return True
                else:
                    logger.info(f"盾类型变化: {current_type}")
                    break

        logger.warning("5秒盾处理超时")
        return False

    def _handle_turnstile(self) -> bool:
        """处理Turnstile验证"""
        logger.info("开始处理Turnstile验证...")

        try:
            # 查找Turnstile iframe
            turnstile_frame = self.page.ele('iframe[src*="turnstile"]', timeout=5)
            if not turnstile_frame:
                logger.warning("未找到Turnstile iframe")
                return False

            # 切换到iframe
            self.page.to_frame(turnstile_frame)

            # 查找验证按钮
            verify_button = self.page.ele('input[type="checkbox"]', timeout=5)
            if verify_button:
                logger.info("找到Turnstile验证按钮，尝试点击")
                verify_button.click()

                # 等待验证完成
                time.sleep(3)

                # 切回主页面
                self.page.to_main_frame()

                # 检查是否成功
                if self._check_site_success():
                    logger.success("Turnstile验证成功")
                    return True

            logger.warning("Turnstile验证失败")
            return False

        except Exception as e:
            logger.error(f"处理Turnstile验证异常: {e}")
            return False

    def _handle_unknown_shield(self) -> bool:
        """处理未知类型的盾"""
        logger.info("尝试通用Cloudflare绕过方法...")

        # 等待一段时间看是否自动通过
        time.sleep(5)

        if self._check_site_success():
            logger.success("通用方法成功")
            return True

        logger.warning("通用方法失败")
        return False





# 为了向后兼容，保持原有的类名和函数名
BrowserManager = UnifiedBrowserManager


def get_browser_manager(config: Optional[Dict[str, Any]] = None) -> UnifiedBrowserManager:
    """
    获取统一浏览器管理器实例

    Args:
        config: 浏览器配置字典

    Returns:
        UnifiedBrowserManager: 统一浏览器管理器实例
    """
    global _browser_manager

    # 如果传递了新的配置，或者实例不存在，则创建新实例
    if '_browser_manager' not in globals() or _browser_manager is None or (config and config != _browser_manager.config):
        _browser_manager = UnifiedBrowserManager(config)
        logger.debug(f"创建新的统一浏览器管理器实例，配置: {config is not None}")

    return _browser_manager


# 全局实例
_browser_manager = None


# 为了向后兼容，添加一个全局函数
def get_browser_manager(config: Optional[Dict[str, Any]] = None) -> UnifiedBrowserManager:
    """
    获取统一浏览器管理器实例

    Args:
        config: 浏览器配置字典

    Returns:
        UnifiedBrowserManager: 统一浏览器管理器实例
    """
    global _browser_manager

    # 如果传递了新的配置，或者实例不存在，则创建新实例
    if '_browser_manager' not in globals() or _browser_manager is None or (config and config != _browser_manager.config):
        _browser_manager = UnifiedBrowserManager(config)
        logger.debug(f"创建新的统一浏览器管理器实例，配置: {config is not None}")

    return _browser_manager


# 全局实例
_browser_manager = None
