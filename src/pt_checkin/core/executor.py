"""
执行器模块
重构自原FlexGet插件，移除FlexGet依赖
"""
from __future__ import annotations

import importlib
import json
import pathlib
import pkgutil
import threading
from datetime import datetime
from typing import List

from loguru import logger

from .entry import SignInEntry

lock = threading.Semaphore(1)


def build_sign_in_schema() -> dict:
    """构建签到配置架构"""
    module = None
    sites_schema: dict = {}
    try:
        # 导入基类
        from ..base.sign_in import SignIn

        sites_path = pathlib.Path(__file__).parent.parent / 'sites'
        for module in pkgutil.iter_modules(path=[str(sites_path)]):
            site_class = get_site_class(module.name)
            if issubclass(site_class, SignIn):
                sites_schema.update(site_class.sign_in_build_schema())
    except AttributeError as e:
        logger.error(f"site: {module.name if module else 'unknown'}, error: {e}")
        raise Exception(f"site: {module.name if module else 'unknown'}, error: {e}")
    return sites_schema


def build_sign_in_entry(entry: SignInEntry, config: dict) -> None:
    """构建签到条目"""
    try:
        # 导入基类
        from ..base.sign_in import SignIn

        site_class = get_site_class(entry['class_name'])
        if issubclass(site_class, SignIn):
            site_class.sign_in_build_entry(entry, config)
    except AttributeError as e:
        logger.error(f"site: {entry['site_name']}, error: {e}")
        raise Exception(f"site: {entry['site_name']}, error: {e}")


def save_cookie(entry: SignInEntry) -> None:
    """保存cookie到备份文件"""
    file_name = 'cookies_backup.json'
    site_name = entry['site_name']
    session_cookie = entry.get('session_cookie')
    if not session_cookie:
        return
    with lock:
        # 保存到配置文件目录
        config_dir = entry.get('config', {}).get('config_dir', '.')
        cookies_backup_file = pathlib.Path(config_dir).joinpath(file_name)
        if cookies_backup_file.is_file():
            try:
                cookies_backup_json = json.loads(cookies_backup_file.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                cookies_backup_json = {}
        else:
            cookies_backup_json = {}
        cookies_backup_json[site_name] = {'date': str(datetime.now().date()), 'cookie': session_cookie}
        cookies_backup_file.write_text(json.dumps(cookies_backup_json, indent=4), encoding='utf-8')


def sign_in(entry: SignInEntry, config: dict) -> SignInEntry:
    """执行签到"""
    try:
        # 导入基类
        from ..base.sign_in import SignIn
        from ..base.message import Message
        from ..base.detail import Detail

        site_class = get_site_class(entry['class_name'])
    except AttributeError as e:
        logger.error(f"site: {entry['class_name']}, error: {e}")
        raise Exception(f"site: {entry['class_name']}, error: {e}")

    site_object = site_class()

    if issubclass(site_class, SignIn):
        entry['prefix'] = 'Sign_in'
        site_object.sign_in(entry, config)
        if entry.failed:
            return entry
        if entry['result']:
            logger.info(f"{entry['title']} {entry['result']}".strip())

    if config.get('get_messages', True) and issubclass(site_class, Message):
        entry['prefix'] = 'Messages'
        site_object.get_messages(entry, config)
        if entry.failed:
            return entry
        if entry['messages']:
            logger.info(f"site_name: {entry['site_name']}, messages: {entry['messages']}")

    if config.get('get_details', True) and issubclass(site_class, Detail):
        entry['prefix'] = 'Details'
        site_object.get_details(entry, config)
        if entry.failed:
            return entry
        if entry['details']:
            logger.info(f"site_name: {entry['site_name']}, details: {entry['details']}")

    if config.get('cookie_backup', True):
        if entry.failed:
            return entry
        save_cookie(entry)
    clean_entry_attr(entry)
    return entry


def clean_entry_attr(entry: SignInEntry) -> None:
    """清理条目属性"""
    for attr in ['base_content', 'prefix']:
        if hasattr(entry, attr):
            delattr(entry, attr)


def get_site_class(class_name: str) -> type:
    """获取站点类"""
    try:
        # 使用绝对导入
        site_module = importlib.import_module(f'pt_checkin.sites.{class_name.lower()}')
        return getattr(site_module, 'MainClass')
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to import site class {class_name}: {e}")
        raise


def create_sign_in_entries(sites_config: dict, config: dict) -> List[SignInEntry]:
    """创建签到条目列表"""
    entries: List[SignInEntry] = []
    
    for site_name, site_configs in sites_config.items():
        if not isinstance(site_configs, list):
            site_configs = [site_configs]
        
        for sub_site_config in site_configs:
            entry = SignInEntry(
                title=f'{site_name} {datetime.now().date()}',
                url=''
            )
            entry['site_name'] = site_name
            entry['class_name'] = site_name
            entry['site_config'] = sub_site_config
            entry['config'] = config  # 添加全局配置
            entry['result'] = ''
            entry['messages'] = ''
            entry['details'] = ''
            
            try:
                build_sign_in_entry(entry, config)
                entries.append(entry)
            except Exception as e:
                logger.error(f"Failed to build entry for {site_name}: {e}")
                continue
    
    return entries
