from typing import Final

from ..schema.nexusphp import AttendanceHR
from ..utils import common


class MainClass(AttendanceHR):
    URL: Final = 'https://hdhome.org/'
    USER_CLASSES: Final = {
        'downloaded': [8796093022208],
        'share_ratio': [5.5],
        'points': [1000000],
        'days': [70]
    }

    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        common.dict_merge(selector, {
            'details': {
                'points': {
                    'regex': '做种积分([\\d.,]+)',
                }
            }
        })
        return selector

