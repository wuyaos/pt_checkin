from __future__ import annotations

import importlib
from urllib.parse import urlparse

from dependency_injector.wiring import Provide, inject

from ..base.entry import SignInEntry
from ..base.sign_in import SignIn
from ..data.database import DatabaseManager
from ..utils import logger
from ..utils.cookie_cloud import CookieCloud


class SignInError(Exception):
    pass


class Executor:
    @inject
    def __init__(self,
                 config: dict = Provide[".container.Container.config"],
                 db_manager: DatabaseManager = Provide[".container.Container.db_manager"],
                 cookie_cloud_client: CookieCloud = Provide[".container.Container.cookie_cloud_client"],
                 ):
        self.config = config
        self.db_manager = db_manager
        self.cookie_cloud_client = cookie_cloud_client

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

    def execute_with_retry(self, entry: SignInEntry) -> dict:
        site_name = entry["site_name"]

        if self.db_manager.has_signed_in_today(site_name):
            return {"site_name": site_name, "status": "今日已签到", "details": "跳过"}

        max_retries = self.config.get("user_config", {}).get("max_retries", 3)
        last_error = None

        cookie, source = self._get_cookie(entry)
        if not cookie:
            return {
                "site_name": site_name,
                "status": "失败",
                "details": "无法获取Cookie",
            }
        entry["cookie"] = cookie

        for attempt in range(max_retries):
            try:
                result = self.execute(entry)
                logger.info(f"站点 {site_name} 使用 {source} Cookie 签到成功。")
                return {"site_name": site_name, **result}
            except SignInError as e:
                last_error = e
                logger.warning(f"站点 {site_name} 第 {attempt + 1} 次尝试签到失败: {e}")
                use_cookie_cloud = entry.get("use_cookie_cloud", False)
                if (
                        attempt < max_retries - 1
                        and use_cookie_cloud
                        and self.cookie_cloud_client
                ):
                    logger.info(f"尝试从云端强制获取 {site_name} 的新 Cookie...")
                    try:
                        domain = urlparse(entry["url"]).netloc
                        new_cookie = self.cookie_cloud_client.get_cookies(domain=domain)
                        if new_cookie:
                            logger.success(f"成功从云端获取到 {site_name} 的新 Cookie。")
                            self.db_manager.save_cookie(site_name, new_cookie)
                            entry["cookie"] = new_cookie
                            source = "云端"
                            continue
                        else:
                            logger.error(f"无法从云端获取 {site_name} 的新 Cookie。")
                            break
                    except (ValueError, AttributeError):
                        logger.warning(
                            f"无法为站点 {site_name} 获取 URL，无法从 CookieCloud 获取 cookie。"
                        )
                        break
        return {
            "site_name": site_name,
            "status": "失败",
            "details": f"经过 {max_retries} 次尝试后仍然失败: {last_error}",
        }

    def _get_cookie(self, entry: SignInEntry) -> tuple[str | None, str]:
        site_name = entry["site_name"]
        cookie = None
        source = "配置"
        use_cookie_cloud = entry.get("use_cookie_cloud", False)

        if use_cookie_cloud and self.cookie_cloud_client:
            cookie = self.db_manager.load_cookie(site_name)
            source = "数据库"
            if cookie is None:
                try:
                    domain = urlparse(entry["url"]).netloc
                    cookie = self.cookie_cloud_client.get_cookies(domain=domain)
                    source = "云端"
                    if cookie:
                        self.db_manager.save_cookie(site_name, cookie)
                except (ValueError, AttributeError):
                    logger.warning(
                        f"无法为站点 {site_name} 获取 URL，无法从 CookieCloud 获取 cookie。"
                    )

        if not cookie:
            cookie = entry.get("cookie")

        return cookie, source

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
