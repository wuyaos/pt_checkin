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


def _determine_signin_type(site_class, entry: SignInEntry) -> str:
    """判断签到类型"""
    # 导入需要的基类
    try:
        from ..schema.nexusphp import AttendanceHR, BakatestHR, VisitHR
        from ..schema.gazelle import Gazelle
        from ..schema.unit3d import Unit3D

        # 检查是否有自定义的签到工作流
        if hasattr(site_class, 'sign_in_build_workflow'):
            # 创建一个临时实例来检查工作流
            temp_instance = site_class()
            workflow = temp_instance.sign_in_build_workflow(entry, {})

            # 检查工作流中是否包含OCR方法
            for work in workflow:
                if hasattr(work, 'method') and work.method:
                    method_name = getattr(work.method, '__name__', str(work.method))
                    if 'ocr' in method_name.lower():
                        return "OCR验证码签到成功"
                    elif 'question' in method_name.lower():
                        return "答题签到成功"

        # 根据站点类型判断签到方式
        if issubclass(site_class, BakatestHR):
            return "答题签到成功"
        elif issubclass(site_class, AttendanceHR):
            return "签到成功"
        elif issubclass(site_class, VisitHR):
            return "访问签到成功"
        elif issubclass(site_class, Gazelle):
            return "模拟登录成功"
        elif issubclass(site_class, Unit3D):
            return "模拟登录成功"
        else:
            return "签到成功"
    except Exception:
        return "签到成功"


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
        site_name = module.name if module else 'unknown'
        logger.error(f"站点架构 - 加载失败: {site_name} ({e})")
        raise Exception(f"site: {site_name}, error: {e}")
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
        logger.error(f"站点模块 - 加载失败: {entry['site_name']} ({e})")
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
        logger.error(f"站点类 - 加载失败: {entry['class_name']} ({e})")
        raise Exception(f"site: {entry['class_name']}, error: {e}")

    site_object = site_class()

    # 判断签到类型
    signin_type = _determine_signin_type(site_class, entry)
    entry['signin_type'] = signin_type  # 保存签到类型到entry中

    # 1. 执行签到 - 这是核心功能，失败则整个任务失败
    if issubclass(site_class, SignIn):
        entry['prefix'] = 'Sign_in'
        site_object.sign_in(entry, config)
        if entry.failed:
            return entry
        if entry['result']:
            logger.info(f"{entry['site_name']} - 签到完成: {entry['result']}")

    # 2. 获取消息 - 独立处理，失败不影响签到成功状态
    entry['messages_status'] = 'success'
    if config.get('get_messages', True) and issubclass(site_class, Message):
        entry['prefix'] = 'Messages'
        try:
            # 临时保存失败状态
            original_failed = entry.failed
            original_reason = entry.reason

            site_object.get_messages(entry, config)

            if entry.failed:
                # 消息获取失败，记录状态但不影响整体签到结果
                entry['messages_status'] = 'failed'
                entry['messages_error'] = entry.reason
                logger.warning(f"{entry['site_name']} - 消息获取失败: {entry.reason}")

                # 恢复签到成功状态
                entry.failed = original_failed
                entry.reason = original_reason
            else:
                if entry['messages']:
                    logger.info(f"{entry['site_name']} - 消息获取成功")
        except Exception as e:
            entry['messages_status'] = 'failed'
            entry['messages_error'] = str(e)
            logger.warning(f"{entry['site_name']} - 消息获取异常: {e}")

    # 3. 获取详情 - 独立处理，失败不影响签到成功状态
    entry['details_status'] = 'success'
    if config.get('get_details', True) and issubclass(site_class, Detail):
        entry['prefix'] = 'Details'
        try:
            # 临时保存失败状态
            original_failed = entry.failed
            original_reason = entry.reason

            site_object.get_details(entry, config)

            if entry.failed:
                # 详情获取失败，记录状态但不影响整体签到结果
                entry['details_status'] = 'failed'
                entry['details_error'] = entry.reason
                logger.warning(f"{entry['site_name']} - 详情获取失败: {entry.reason}")

                # 恢复签到成功状态
                entry.failed = original_failed
                entry.reason = original_reason
            else:
                if entry['details']:
                    logger.info(f"{entry['site_name']} - 详情获取成功")
        except Exception as e:
            entry['details_status'] = 'failed'
            entry['details_error'] = str(e)
            logger.warning(f"{entry['site_name']} - 详情获取异常: {e}")

    # 4. 备份Cookie
    if config.get('cookie_backup', True):
        if not entry.failed:  # 只有签到成功才备份Cookie
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
        module_name = f'pt_checkin.sites.{class_name.lower()}'
        site_module = importlib.import_module(module_name)
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
                logger.error(f"条目构建 - 失败: {site_name} ({e})")
                continue

    return entries
