from typing import Final

from ..core.entry import SignInEntry
from ..schema.nexusphp import NexusPHP


class MainClass(NexusPHP):
    URL: Final = 'https://hdchina.org/'
    SUCCEED_REGEX: Final = '签到已得\\d+魔力值'
    USER_CLASSES: Final = {
        'downloaded': [3298534883328],
        'share_ratio': [4.55],
        'days': [700]
    }

    def sign_in(self, entry: SignInEntry, config: dict) -> None:
        self.sign_in_by_get(entry, config, work_name='attendance')
