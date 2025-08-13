"""
签到状态管理器
记录每日签到状态，避免重复签到
"""
import json
import pathlib
from datetime import datetime
from typing import Dict, Any, Optional

from loguru import logger


class SignInStatusManager:
    """签到状态管理器"""
    
    def __init__(self, status_file: str = 'signin_status.json'):
        self.status_file = pathlib.Path(status_file)
        self.status_data: Dict[str, Any] = {}
        self.load_status()
    
    def load_status(self) -> None:
        """加载签到状态"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    self.status_data = json.load(f)
                logger.debug(f"签到状态加载成功: {self.status_file}")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"加载签到状态失败: {e}")
                self.status_data = {}
        else:
            self.status_data = {}
    
    def save_status(self) -> None:
        """保存签到状态"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"签到状态保存成功: {self.status_file}")
        except Exception as e:
            logger.error(f"保存签到状态失败: {e}")
    
    def get_today_key(self) -> str:
        """获取今日日期键"""
        return datetime.now().strftime('%Y-%m-%d')
    
    def is_signed_today(self, site_name: str) -> bool:
        """检查今日是否已签到"""
        today = self.get_today_key()
        return (
            today in self.status_data and
            site_name in self.status_data[today] and
            self.status_data[today][site_name].get('status') == 'success'
        )
    
    def get_site_status(self, site_name: str) -> Optional[Dict[str, Any]]:
        """获取站点今日状态"""
        today = self.get_today_key()
        if today in self.status_data and site_name in self.status_data[today]:
            return self.status_data[today][site_name]
        return None
    
    def record_signin_success(self, site_name: str, result: str, messages: str = '', details: str = '') -> None:
        """记录签到成功"""
        today = self.get_today_key()
        if today not in self.status_data:
            self.status_data[today] = {}

        self.status_data[today][site_name] = {
            'status': 'success',
            'result': result,
            'messages': messages,
            'details': details,
            'time': datetime.now().strftime('%H:%M:%S'),
            'timestamp': datetime.now().isoformat(),
            'failed_count': 0  # 成功后重置失败次数
        }
        self.save_status()
        logger.debug(f"记录签到成功: {site_name}")
    
    def record_signin_failed(self, site_name: str, reason: str) -> None:
        """记录签到失败"""
        today = self.get_today_key()
        if today not in self.status_data:
            self.status_data[today] = {}

        # 获取当前失败次数
        current_failed_count = 0
        if site_name in self.status_data[today]:
            current_failed_count = self.status_data[today][site_name].get('failed_count', 0)
            # 如果当前状态是成功，重置失败次数
            if self.status_data[today][site_name].get('status') == 'success':
                current_failed_count = 0

        self.status_data[today][site_name] = {
            'status': 'failed',
            'reason': reason,
            'time': datetime.now().strftime('%H:%M:%S'),
            'timestamp': datetime.now().isoformat(),
            'failed_count': current_failed_count + 1
        }
        self.save_status()
        logger.debug(f"记录签到失败: {site_name} - {reason} (失败次数: {current_failed_count + 1})")
    
    def clear_site_status(self, site_name: str, keep_failed_count: bool = False) -> None:
        """清除站点今日状态（用于强制重新签到）"""
        today = self.get_today_key()
        if today in self.status_data and site_name in self.status_data[today]:
            if keep_failed_count:
                # 保留失败次数
                failed_count = self.status_data[today][site_name].get('failed_count', 0)
                del self.status_data[today][site_name]
                # 如果有失败次数，创建一个新的记录保留失败次数
                if failed_count > 0:
                    self.status_data[today][site_name] = {
                        'failed_count': failed_count
                    }
            else:
                del self.status_data[today][site_name]
            self.save_status()
            logger.debug(f"清除站点状态: {site_name} (保留失败次数: {keep_failed_count})")

    def get_failed_count(self, site_name: str) -> int:
        """获取站点今日失败次数"""
        today = self.get_today_key()
        if today in self.status_data and site_name in self.status_data[today]:
            return self.status_data[today][site_name].get('failed_count', 0)
        return 0

    def should_skip_due_to_failures(self, site_name: str, max_failed_attempts: int, retry_interval_hours: int = 2) -> tuple[bool, str]:
        """检查是否应该因为失败次数过多而跳过站点"""
        failed_count = self.get_failed_count(site_name)

        if failed_count < max_failed_attempts:
            return False, ""

        # 检查最后失败时间
        site_status = self.get_site_status(site_name)
        if site_status and site_status.get('status') == 'failed':
            try:
                last_failed_time = datetime.fromisoformat(site_status['timestamp'])
                time_since_failure = datetime.now() - last_failed_time
                hours_since_failure = time_since_failure.total_seconds() / 3600

                if hours_since_failure < retry_interval_hours:
                    return True, f"连续失败{failed_count}次，{retry_interval_hours}小时内不再尝试"
                else:
                    # 超过重试间隔，可以重新尝试
                    return False, ""
            except (ValueError, KeyError):
                # 时间解析失败，允许重试
                return False, ""

        return True, f"连续失败{failed_count}次，暂时跳过"

    def reset_failed_count(self, site_name: str) -> None:
        """重置站点失败次数"""
        today = self.get_today_key()
        if today in self.status_data and site_name in self.status_data[today]:
            self.status_data[today][site_name]['failed_count'] = 0
            self.save_status()
            logger.info(f"重置站点失败次数: {site_name}")
    
    def clear_all_status(self) -> None:
        """清除今日所有状态（用于强制重新签到所有站点）"""
        today = self.get_today_key()
        if today in self.status_data:
            del self.status_data[today]
            self.save_status()
            logger.debug("清除今日所有签到状态")
    
    def get_today_summary(self) -> Dict[str, Any]:
        """获取今日签到摘要"""
        today = self.get_today_key()
        if today not in self.status_data:
            return {'total': 0, 'success': 0, 'failed': 0, 'sites': {}}
        
        sites_data = self.status_data[today]
        success_count = sum(1 for site in sites_data.values() if site.get('status') == 'success')
        failed_count = sum(1 for site in sites_data.values() if site.get('status') == 'failed')
        
        return {
            'total': len(sites_data),
            'success': success_count,
            'failed': failed_count,
            'sites': sites_data
        }
    
    def cleanup_old_records(self, keep_days: int = 7) -> None:
        """清理旧记录"""
        if not self.status_data:
            return
        
        today = datetime.now()
        keys_to_remove = []
        
        for date_key in self.status_data.keys():
            try:
                record_date = datetime.strptime(date_key, '%Y-%m-%d')
                days_diff = (today - record_date).days
                if days_diff > keep_days:
                    keys_to_remove.append(date_key)
            except ValueError:
                # 无效的日期格式，也删除
                keys_to_remove.append(date_key)
        
        for key in keys_to_remove:
            del self.status_data[key]
        
        if keys_to_remove:
            self.save_status()
            logger.info(f"清理了 {len(keys_to_remove)} 天的旧签到记录")
