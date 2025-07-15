import sqlite3
from datetime import datetime
from pathlib import Path

from ptsites.utils import logger


class DatabaseManager:
    """
    Manages all database operations for the PT Check-in application.
    """

    def __init__(self, db_path: Path):
        """
        Initializes the DatabaseManager, connects to the database,
        and ensures necessary tables are created.

        Args:
            db_path (Path): The full path to the SQLite database file.
        """
        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path)
            self._create_tables()
        except sqlite3.Error as e:
            logger.error(f"数据库连接失败于 {self.db_path}: {e}")
            raise  # Re-raise the exception to be handled by the caller

    def _create_tables(self):
        """Creates database tables if they don't exist."""
        if not self.conn:
            return
        try:
            with self.conn:
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS sign_in_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        site_name TEXT NOT NULL,
                        sign_in_time TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT,
                        hr TEXT
                    )
                ''')
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS cookie_cache (
                        site_name TEXT PRIMARY KEY,
                        cookie TEXT,
                        last_updated TEXT
                    )
                ''')
                logger.info(
                    "数据库表 'sign_in_log' 和 'cookie_cache' 已准备就绪。"
                )
        except sqlite3.Error as e:
            logger.error(f"创建表时发生数据库错误: {e}")

    def add_log(self, site_name: str, status: str,
                message: str = '', hr: str = ''):
        """Adds a new sign-in log entry to the database."""
        if not self.conn:
            return
        sign_in_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with self.conn:
                self.conn.execute('''
                    INSERT INTO sign_in_log
                        (site_name, sign_in_time, status, message, hr)
                    VALUES (?, ?, ?, ?, ?)
                ''', (site_name, sign_in_time, status, message, hr))
            logger.info(f"已为站点添加日志: {site_name}, 状态: {status}")
        except sqlite3.Error as e:
            logger.error(
                f"为站点 {site_name} 添加日志失败。错误: {e}"
            )

    def has_signed_in_today(self, site_name: str) -> bool:
        """Checks if the site has a successful sign-in record for today."""
        if not self.conn:
            return False
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM sign_in_log "
                    "WHERE site_name = ? AND status = 'Success' AND "
                    "DATE(sign_in_time) = DATE('now', 'localtime') "
                    "LIMIT 1",
                    (site_name,)
                )
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(
                f"为 {site_name} 检查签到状态失败。错误: {e}"
            )
            return False

    def save_cookie(self, site_name: str, cookie: str):
        """Saves or updates a site's cookie in the database."""
        if not self.conn:
            return
        last_updated = datetime.now().isoformat()
        try:
            with self.conn:
                self.conn.execute(
                    'INSERT OR REPLACE INTO cookie_cache '
                    '(site_name, cookie, last_updated) VALUES (?, ?, ?)',
                    (site_name, cookie, last_updated)
                )
            logger.info(f"已为站点保存 Cookie: {site_name}")
        except sqlite3.Error as e:
            logger.error(
                f"为站点 {site_name} 保存 Cookie 失败。错误: {e}"
            )

    def load_cookie(self, site_name: str) -> str | None:
        """Loads a site's cookie from the database."""
        if not self.conn:
            return None
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT cookie FROM cookie_cache WHERE site_name = ?
                ''', (site_name,))
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(
                f"为站点 {site_name} 加载 Cookie 失败。错误: {e}"
            )
            return None

    def __del__(self):
        """Closes the database connection upon object destruction."""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭。")
