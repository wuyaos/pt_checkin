#!/usr/bin/env python3
"""
PT签到工具 - 统一日志管理器
提供统一的日志配置和管理功能
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

from loguru import logger


class LogManager:
    """统一日志管理器

    功能：
    1. 统一日志配置管理
    2. 支持配置文件驱动
    3. 提供结构化日志支持
    4. 性能优化的条件日志
    """

    _instance: Optional["LogManager"] = None
    _initialized: bool = False

    # 默认日志配置
    DEFAULT_CONFIG = {
        "level": "INFO",
        "console": {
            "enabled": True,
            "level": "INFO",
            "format": (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            "colorize": True,
        },
        "file": {
            "enabled": True,
            "level": "DEBUG",
            "path": "pt_checkin.log",
            "format": (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
                "{name}:{function}:{line} - {message}"
            ),
            "rotation": "10 MB",
            "retention": "30 days",
            "compression": "zip",
            "encoding": "utf-8",
        },
        "modules": {
            # 模块级别的日志配置
            "pt_checkin.utils.baidu_ocr": "DEBUG",
            "pt_checkin.core.scheduler": "INFO",
            "pt_checkin.base.sign_in": "INFO",
        },
    }

    def __new__(cls) -> "LogManager":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化日志管理器"""
        if not self._initialized:
            self.config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
            self.config_dir: Optional[Path] = None
            self._loggers: Dict[str, Any] = {}
            LogManager._initialized = True

    def initialize(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_dir: Optional[Path] = None,
        verbose: bool = False,
    ) -> None:
        """初始化日志系统

        Args:
            config: 日志配置字典
            config_dir: 配置目录路径
            verbose: 是否启用详细输出
        """
        # 移除所有现有的处理器
        logger.remove()

        # 更新配置
        if config:
            self._merge_config(config)

        # 设置配置目录
        if config_dir:
            self.config_dir = Path(config_dir)

        # 如果启用verbose，覆盖控制台日志级别
        if verbose:
            self.config["console"]["level"] = "DEBUG"

        # 配置控制台输出
        self._setup_console_logging()

        # 配置文件输出
        self._setup_file_logging()

    def _merge_config(self, user_config: Dict[str, Any]) -> None:
        """合并用户配置到默认配置"""

        def deep_merge(default: Dict, user: Dict) -> Dict:
            result = default.copy()
            for key, value in user.items():
                if (
                    key in result
                    and isinstance(result[key], dict)
                    and isinstance(value, dict)
                ):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        self.config = deep_merge(self.DEFAULT_CONFIG, user_config)

    def _setup_console_logging(self) -> None:
        """设置控制台日志输出"""
        console_config = self.config.get("console", {})
        if not console_config.get("enabled", True):
            return

        logger.add(
            sys.stdout,
            level=console_config.get("level", "INFO"),
            format=console_config.get(
                "format", self.DEFAULT_CONFIG["console"]["format"]
            ),
            colorize=console_config.get("colorize", True),
            filter=self._create_level_filter(),
        )

    def _setup_file_logging(self) -> None:
        """设置文件日志输出"""
        file_config = self.config.get("file", {})
        if not file_config.get("enabled", True):
            return

        # 确定日志文件路径
        log_path = file_config.get("path", "pt_checkin.log")
        if self.config_dir and not Path(log_path).is_absolute():
            log_path = self.config_dir / log_path

        try:
            logger.add(
                str(log_path),
                level=file_config.get("level", "DEBUG"),
                format=file_config.get("format", self.DEFAULT_CONFIG["file"]["format"]),
                rotation=file_config.get("rotation", "10 MB"),
                retention=file_config.get("retention", "30 days"),
                compression=file_config.get("compression", "zip"),
                encoding=file_config.get("encoding", "utf-8"),
                filter=self._create_level_filter(),
            )
            logger.info(f"日志文件输出: {Path(log_path).absolute()}")
        except Exception as e:
            logger.warning(f"日志文件配置失败: {e}")

    def _create_level_filter(self):
        """创建模块级别的日志过滤器"""
        modules_config = self.config.get("modules", {})

        def level_filter(record):
            module_name = record.get("name", "")

            # 检查是否有模块特定的级别配置
            for module_pattern, level in modules_config.items():
                if module_name.startswith(module_pattern):
                    record["level"].no = logger.level(level).no
                    break

            return True

        return level_filter if modules_config else None

    def get_logger(self, name: Optional[str] = None) -> Any:
        """获取logger实例

        Args:
            name: logger名称，默认使用调用模块名

        Returns:
            配置好的logger实例
        """
        if name is None:
            # 自动获取调用模块名
            import inspect

            frame = inspect.currentframe().f_back
            name = frame.f_globals.get("__name__", "unknown")

        # 返回绑定了模块名的logger
        return logger.bind(module=name)

    def get_contextual_logger(self, **context) -> Any:
        """获取带上下文的logger

        Args:
            **context: 上下文键值对

        Returns:
            绑定了上下文的logger实例
        """
        return logger.bind(**context)

    def is_debug_enabled(self) -> bool:
        """检查是否启用了DEBUG级别日志"""
        return logger.level("DEBUG").no >= logger._core.min_level

    def conditional_debug(self, message: str, condition: bool = True, **kwargs) -> None:
        """条件DEBUG日志，用于性能优化

        Args:
            message: 日志消息
            condition: 是否输出的条件
            **kwargs: 额外的上下文参数
        """
        if condition and self.is_debug_enabled():
            if kwargs:
                logger.bind(**kwargs).debug(message)
            else:
                logger.debug(message)


# 全局日志管理器实例
log_manager = LogManager()


def get_logger(name: Optional[str] = None) -> Any:
    """便捷函数：获取logger实例"""
    return log_manager.get_logger(name)


def get_contextual_logger(**context) -> Any:
    """便捷函数：获取带上下文的logger"""
    return log_manager.get_contextual_logger(**context)


def init_logging(
    config: Optional[Dict[str, Any]] = None,
    config_dir: Optional[Path] = None,
    verbose: bool = False,
) -> None:
    """便捷函数：初始化日志系统"""
    log_manager.initialize(config, config_dir, verbose)
