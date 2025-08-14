"""
配置管理器
负责加载和验证配置文件
"""
import pathlib
from typing import Dict, Any

import yaml
from loguru import logger


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = 'config.yml'):
        self.config_path = pathlib.Path(config_path)
        self.config_dir = self.config_path.parent  # 配置文件所在目录
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        if not self.config_path.exists():
            logger.error(f"配置文件不存在: {self.config_path}")
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
            logger.info(f"配置文件加载成功: {self.config_path}")
            logger.info(f"FlareSolverr配置: {self.config.get('flaresolverr', 'Not found')}")
            logger.info(f"站点配置: {list(self.config.get('sites', {}).keys())}")
            self._validate_config()
        except yaml.YAMLError as e:
            logger.error(f"配置文件格式错误: {e}")
            raise
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _validate_config(self) -> None:
        """验证配置文件"""
        # 设置默认值
        self.config.setdefault('max_workers', 1)
        self.config.setdefault('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.config.setdefault('get_messages', True)
        self.config.setdefault('get_details', True)
        self.config.setdefault('cookie_backup', True)
        self.config.setdefault('schedule_time', '08:30')
        self.config.setdefault('sites', {})
        
        # 验证必要配置
        if not self.config.get('sites'):
            logger.warning("未配置任何站点")
        
        # 验证站点配置格式
        sites = self.config.get('sites', {})
        for site_name, site_config in sites.items():
            if isinstance(site_config, str):
                # 简单cookie配置，转换为标准格式
                self.config['sites'][site_name] = {'cookie': site_config}
            elif isinstance(site_config, dict):
                # 详细配置，保持不变
                pass
            else:
                logger.warning(f"站点 {site_name} 配置格式不正确")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)
    
    def get_sites(self) -> Dict[str, Any]:
        """获取站点配置"""
        return self.config.get('sites', {})
    
    def get_user_agent(self) -> str:
        """获取User-Agent"""
        return self.config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    def get_max_workers(self) -> int:
        """获取最大工作线程数"""
        return self.config.get('max_workers', 1)
    
    def get_schedule_time(self) -> str:
        """获取调度时间"""
        return self.config.get('schedule_time', '08:30')

    def get_max_failed_attempts(self) -> int:
        """获取最大失败次数"""
        return self.config.get('max_failed_attempts', 3)

    def get_failed_retry_interval(self) -> int:
        """获取失败重试间隔（小时）"""
        return self.config.get('failed_retry_interval', 2)
    
    def get_baidu_ocr_config(self) -> Dict[str, str]:
        """获取百度OCR配置
        统一使用新格式 aipocr: {app_id, api_key, secret_key}
        """
        if isinstance(self.config.get('aipocr'), dict):
            a = self.config['aipocr']
            return {
                'app_id': a.get('app_id', ''),
                'api_key': a.get('api_key', ''),
                'secret_key': a.get('secret_key', ''),
            }
        # 如果没有新格式配置，返回空配置
        return {
            'app_id': '',
            'api_key': '',
            'secret_key': ''
        }
    
    def prepare_config_for_executor(self) -> Dict[str, Any]:
        """为执行器准备配置"""
        return {
            'user-agent': self.get_user_agent(),
            'max_workers': self.get_max_workers(),
            'get_messages': self.get('get_messages', True),
            'get_details': self.get('get_details', True),
            'cookie_backup': self.get('cookie_backup', True),
            'aipocr': self.get_baidu_ocr_config(),
            'flaresolverr': self.config.get('flaresolverr', {}),
            'config_dir': str(self.config_dir),  # 配置文件目录路径
            'sites': self.get_sites()
        }
