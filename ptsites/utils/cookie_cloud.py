from pathlib import Path

from PyCookieCloud import PyCookieCloud
from ..utils.logger import logger


class CookieCloud:
    def __init__(self, url: str, uuid: str, password: str, data_path: Path):
        self.client = PyCookieCloud(url, uuid, password)
        self.cookies: dict | None = None
        self.data_path = data_path

    def _fetch_all_cookies(self):
        logger.info('从 CookieCloud 获取所有 cookies...')
        try:
            if (not self.client.get_the_key() or
                    not self.client.get_encrypted_data()):
                logger.error('从 CookieCloud 获取 key 或加密数据失败。')
                self.cookies = {}
                return

            decrypted_data = self.client.get_decrypted_data()
            if not decrypted_data:
                logger.error('从 CookieCloud 解密数据失败。')
                self.cookies = {}
                return

            self.cookies = self._process_cookies(decrypted_data)
            logger.success('成功从 CookieCloud 获取所有 cookies。')
        except Exception as e:
            logger.error(f'从 CookieCloud 获取所有 cookies 时发生错误: {e}')
            self.cookies = {}

    def _process_cookies(self, decrypted_data: dict) -> dict:
        processed_cookies = {}
        for domain, content_list in decrypted_data.items():
            if not content_list or all(
                c.get("name") == "cf_clearance" for c in content_list
            ):
                continue

            cookie_list = [
                f"{c.get('name')}={c.get('value')}"
                for c in content_list if c.get("name") and c.get("value")
            ]
            
            if domain.startswith('.'):
                domain = domain[1:]
            processed_cookies[domain] = "; ".join(cookie_list)
        return processed_cookies

    def get_cookies(self, domain: str) -> str | None:
        """
        Get cookies from CookieCloud for a specific domain.

        :param domain: The domain to get cookies for.
        :return: A string of cookies, or None if not found.
        """
        if isinstance(domain, bytes):
            try:
                domain = domain.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning('域名解码失败，无法获取 cookies。')
                return None

        if not domain:
            logger.warning('无效或空的域名，无法获取 cookies。')
            return None
        
        if self.cookies is None:
            self._fetch_all_cookies()

        if not self.cookies:
            logger.warning('在 CookieCloud 中未找到任何 cookies。')
            return None

        # Direct match
        if cookie := self.cookies.get(domain):
            logger.success(f'成功获取域名 {domain} 的 cookies。')
            return cookie

        # Subdomain match
        for d, c in self.cookies.items():
            if domain.endswith(d):
                logger.info(f"在 {domain} 未找到 cookie，但在 {d} 找到了。")
                return c
        
        logger.warning(f'未找到域名 {domain} 的 cookies。')
        return None

