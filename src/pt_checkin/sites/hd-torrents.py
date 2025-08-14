from typing import Final

# Removed reseed functionality
from ..schema.xbtit import XBTIT
from utils import net_utils


class MainClass(XBTIT):
    URL: Final = 'https://hd-torrents.org/'
    SUCCEED_REGEX: Final = 'Welcome back, .+?!'
    USER_CLASSES: Final = {
        'uploaded': [1099511627776],
        'share_ratio': [4]
    }
    
    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        net_utils.dict_merge(selector, {
            'detail_sources': {
                'default': {
                    'elements': {
                        'bar': 'body > div.mainmenu > table:nth-child(4)',
                    }
                }
            }
        })
        return selector
