"""
PT站点自动签到工具

一个独立的PT站点自动签到工具，支持多种站点类型和调度模式。
"""

__version__ = "0.2.0"
__author__ = "wuyaos"
__email__ = ""
__description__ = "PT站点自动签到工具 - 独立版本，移除FlexGet依赖"

# 导出主要类和函数
from .core.config_manager import ConfigManager
from .core.scheduler import TaskScheduler
from .core.signin_status import SignInStatusManager

__all__ = [
    "ConfigManager",
    "TaskScheduler",
    "SignInStatusManager",
    "__version__",
    "__author__",
    "__email__",
    "__description__",
]
