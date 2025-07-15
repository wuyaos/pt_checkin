from typing import Final

from ..schema.nexusphp import Visit
from ..utils import common


class MainClass(Visit):
    URL: Final = 'https://www.joyhd.net/'
    USER_CLASSES: Final = {
        'downloaded': [644245094400, 5368709120000],
        'share_ratio': [4.5, 6],
        'days': [175, 350]
    }

    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        common.dict_merge(selector, {
            'details': {
                'points': {
                    'regex': '银元.*?([\\d,.]+)'
                }
            }
        })
        return selector

