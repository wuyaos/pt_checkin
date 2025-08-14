from typing import Final

# Removed reseed functionality
from ..schema.nexusphp import Visit
from ..utils import net_utils


class MainClass(Visit):
    URL: Final = 'https://pt.sjtu.edu.cn/'
    SUCCEED_REGEX: Final = '魔力值 \\(\\d+\\)'
    USER_CLASSES: Final = {
        'downloaded': [805306368000, 3298534883328],
        'share_ratio': [3.05, 4.55],
        'days': [280, 700]
    }

    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        net_utils.dict_merge(selector, {
            'detail_sources': {
                'default': {
                    'elements': {
                        'bar': None,
                        'table': 'table[border="1"]'
                    }
                },
                'extend': {
                    'link': '/viewpeerstatus.php',
                    'elements': {
                        'bar': 'li'
                    },
                    'do_not_strip': True
                }
            }
        })
        return selector
