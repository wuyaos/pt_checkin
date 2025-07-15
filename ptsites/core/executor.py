from __future__ import annotations

import importlib
from ptsites.base.entry import SignInEntry
from ptsites.base.sign_in import SignIn
from ptsites.data.database import DatabaseManager
from ptsites.utils import logger


class SignInError(Exception):
    pass


class Executor:
    def __init__(self, config: dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager

    def execute(self, entry: SignInEntry) -> dict:
        """
        Execute a single sign-in task.
        """
        logger.info(f'开始签到 {entry["site_name"]}')
        try:
            site_class = self._get_site_class(entry['class_name'])
            site_object = site_class()

            if issubclass(site_class, SignIn):
                site_object.sign_in(entry, self.config)
                result = entry.get('result')
                if (not result or
                        '失败' in result or
                        'error' in result.lower() or
                        'cookie' in result.lower()):
                    raise SignInError("Cookie可能已失效")

                logger.info(f"{entry.get('title', '')} {result}".strip())
                hr_status = entry.get('hr') or ''
                self.db_manager.add_log(
                    entry['site_name'], 'Success', result, hr_status
                )
                return {'status': '成功', 'details': result}

            logger.info(f'签到完成 {entry["site_name"]}')
            return {'status': 'info', 'details': '非签到任务，已跳过'}

        except SignInError as e:
            logger.warning(f"签到失败: {entry['site_name']}, 错误: {e}")
            self.db_manager.add_log(entry['site_name'], 'Failed', str(e))
            raise e
        except Exception as e:
            logger.error(f"签到失败: {entry['site_name']}, 错误: {e}")
            self.db_manager.add_log(entry['site_name'], 'Failed', str(e))
            raise SignInError(f"签到时发生未知错误: {e}") from e

    @staticmethod
    def _get_site_class(class_name: str) -> type:
        """
        Dynamically import and return the site class.
        """
        try:
            module_path = f'ptsites.sites.{class_name.lower()}'
            site_module = importlib.import_module(module_path)
            return getattr(site_module, 'MainClass')
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not find site {class_name}: {e}")
