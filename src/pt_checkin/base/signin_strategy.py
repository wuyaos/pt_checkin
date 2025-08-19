from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from requests import Response

from ..core.entry import SignInEntry
from .work import Work


class SignInStrategy(ABC):
    """签到策略抽象基类"""

    @abstractmethod
    def build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
        """构建签到工作流"""
        pass

    @abstractmethod
    def execute_signin(self, entry: SignInEntry, config: dict, work: Work, 
                      last_content: str = None) -> Response | None:
        """执行签到操作"""
        pass


class StandardSignInStrategy(SignInStrategy):
    """标准签到策略 - 适用于简单的GET/POST签到"""

    def build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
        """构建标准签到工作流"""
        return [
            Work(
                url='/',
                method=self.execute_signin,
                succeed_regex=['签到成功', 'success', '欢迎回来'],
                fail_regex='签到失败',
                is_base_content=True
            )
        ]

    def execute_signin(self, entry: SignInEntry, config: dict, work: Work, 
                      last_content: str = None) -> Response | None:
        """执行标准签到"""
        from .request import RequestHandler
        handler = RequestHandler(entry, config)
        return handler.request('GET', work.url)


class CaptchaSignInStrategy(SignInStrategy):
    """验证码签到策略 - 适用于需要处理验证码的签到"""

    def build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
        """构建验证码签到工作流"""
        return [
            Work(
                url='/',
                method=self.execute_signin,
                succeed_regex=['{"success":true'],
                fail_regex='{"success":false',
                is_base_content=True
            )
        ]

    def execute_signin(self, entry: SignInEntry, config: dict, work: Work, 
                      last_content: str = None) -> Response | None:
        """执行验证码签到"""
        # 这里将包含验证码处理逻辑
        return self._handle_captcha_signin(entry, config, work)

    def _handle_captcha_signin(self, entry: SignInEntry, config: dict, work: Work) -> Response | None:
        """处理验证码签到的具体逻辑"""
        # 这个方法将在子类中实现具体的验证码处理逻辑
        raise NotImplementedError("Subclasses must implement captcha handling")


class BrowserSignInStrategy(SignInStrategy):
    """浏览器签到策略 - 适用于需要浏览器自动化的签到"""

    def build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
        """构建浏览器签到工作流"""
        return [
            Work(
                url='/',
                method=self.execute_signin,
                succeed_regex=['签到成功', 'success'],
                fail_regex='签到失败',
                is_base_content=True
            )
        ]

    def execute_signin(self, entry: SignInEntry, config: dict, work: Work, 
                      last_content: str = None) -> Response | None:
        """执行浏览器签到"""
        from .request import RequestHandler
        # 强制使用浏览器模式
        entry['request_method'] = 'browser'
        handler = RequestHandler(entry, config)
        return handler.request('GET', work.url)


class SignInStrategyFactory:
    """签到策略工厂"""

    @staticmethod
    def create_strategy(entry: SignInEntry, config: dict) -> SignInStrategy:
        """
        根据配置创建合适的签到策略

        Args:
            entry: 签到条目
            config: 配置字典

        Returns:
            SignInStrategy实例
        """
        # 检查是否需要验证码处理
        if entry.get('has_captcha', False):
            return CaptchaSignInStrategy()

        # 检查是否强制使用浏览器
        if entry.get('request_method') == 'browser' or entry.get('force_browser', False):
            return BrowserSignInStrategy()

        # 默认使用标准策略
        return StandardSignInStrategy()
