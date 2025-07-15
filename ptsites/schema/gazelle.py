import datetime
import re
from abc import ABC


from .private_torrent import PrivateTorrent
from ..utils.value_handler import handle_infinite


class Gazelle(PrivateTorrent, ABC):


    @property
    def details_selector(self) -> dict:
        return {
            'user_id': r'user\.php\?id=(\d+)',
            'detail_sources': {
                'default': {
                    'link': '/user.php?id={}',
                    'elements': {
                        'table': (
                            '#content > div > div.sidebar > '
                            'div.box.box_info.box_userinfo_stats > ul'
                        )
                    }
                }
            },
            'details': {
                'uploaded': {
                    'regex': (r'(Upload|上传量).+?([\d.]+ ?[ZEPTGMK]?i?B)', 2)
                },
                'downloaded': {
                    'regex': (r'(Download|下载量).+?([\d.]+ ?[ZEPTGMK]?i?B)', 2)
                },
                'share_ratio': {
                    'regex': (r'(Ratio|分享率).*?(∞|[\d,.]+)', 2),
                    'handle': handle_infinite
                },
                'points': {
                    'regex': (r'(Gold|积分|Bonus|Credits|Nips).*?([\d,.]+)', 2)
                },
                'join_date': {
                    'regex': ('(Joined|加入时间).*?(.*?)(ago|前|Last seen)', 2),
                    'handle': self.handle_join_date
                },
                'seeding': {
                    'regex': r'[Ss]eeding.+?([\d,]+)'
                },
                'leeching': {
                    'regex': r'[Ll]eeching.+?([\d,]+)'
                },
                'hr': None
            }
        }


    def handle_join_date(self, value: str) -> datetime.date:
        year_regex = '(\\d+) (年|years?)'
        month_regex = '(\\d+) (月|months?)'
        week_regex = '(\\d+) (周|weeks?)'
        year = 0
        month = 0
        week = 0
        if year_match := re.search(year_regex, value):
            year = int(year_match.group(1))
        if month_match := re.search(month_regex, value):
            month = int(month_match.group(1))
        if week_match := re.search(week_regex, value):
            week = int(week_match.group(1))
        return (datetime.datetime.now() - datetime.timedelta(
            days=year * 365 + month * 31 + week * 7)).date()

