"""
签到条目类
移除FlexGet依赖的独立实现
"""
import json
import pathlib
from typing import Any, Dict


class SignInEntry:
    """签到条目类，替代FlexGet的Entry"""
    
    def __init__(self, title: str, url: str = ''):
        self.data: Dict[str, Any] = {
            'title': title,
            'url': url
        }
        self.failed = False
        self.reason = ''
    
    def __getitem__(self, key: str) -> Any:
        """获取条目属性"""
        return self.data.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """设置条目属性"""
        self.data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取条目属性，支持默认值"""
        return self.data.get(key, default)
    
    def fail(self, reason: str) -> None:
        """标记条目失败"""
        self.failed = True
        self.reason = reason
    
    def fail_with_prefix(self, reason: str) -> None:
        """带前缀的失败标记"""
        prefix = self.get('prefix', '')
        last_date = self.last_date()
        full_reason = f"{prefix}=> {reason}. ({last_date})" if prefix else f"{reason}. ({last_date})"
        self.fail(full_reason)
    
    def last_date(self) -> str:
        """获取上次签到日期"""
        file_name = 'cookies_backup.json'
        site_name = self.get('site_name')
        if not site_name:
            return ''

        # 从配置文件目录读取
        config_dir = self.get('config', {}).get('config_dir', '.')
        cookies_backup_file = pathlib.Path(config_dir).joinpath(file_name)
        if cookies_backup_file.is_file():
            try:
                cookies_backup_json = json.loads(cookies_backup_file.read_text(encoding='utf-8'))
                if isinstance(cookies_backup_json.get(site_name), dict):
                    return cookies_backup_json.get(site_name, {}).get('date', '')
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return ''
    
    @property
    def title(self) -> str:
        """获取标题"""
        return self.get('title', '')
    
    @property
    def url(self) -> str:
        """获取URL"""
        return self.get('url', '')
    
    def __str__(self) -> str:
        return f"SignInEntry(title='{self.title}', failed={self.failed})"
    
    def __repr__(self) -> str:
        return self.__str__()
