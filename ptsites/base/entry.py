import json
import logging
import pathlib

logger = logging.getLogger(__name__)


class SignInEntry(dict):
    def last_date(self) -> str:
        file_name = 'cookies_backup.json'
        site_name = self.get('site_name')
        cookies_backup_file = pathlib.Path.cwd().joinpath(file_name)
        if cookies_backup_file.is_file():
            cookies_text = cookies_backup_file.read_text(encoding='utf-8')
            cookies_backup_json = json.loads(cookies_text)
        else:
            cookies_backup_json = {}
        
        site_cookie = cookies_backup_json.get(site_name)
        if isinstance(site_cookie, dict):
            return site_cookie.get('date', '')
        return ''

    def fail_with_prefix(self, reason: str) -> None:
        logger.error(f"{self.get('prefix')}=> {reason}。 ({self.last_date()})")

