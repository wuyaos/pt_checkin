from typing import Final

from ..schema.nexusphp import Attendance
from ..utils import common
from ..utils.value_handler import size


class MainClass(Attendance):
    @property
    def URL(self) -> str:
        return 'https://zmpt.cc/'
    USER_CLASSES: Final = {
        'downloaded': [size(750, 'GiB'), size(3, 'TiB')],
        'share_ratio': [3.05, 4.55],
        'days': [280, 700]
    }

    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        common.dict_merge(selector, {
            'details': {
                'points': {
                    'regex': r'电力值.*?([\d,.]+)'
                },
            }
        })
        return selector

