from __future__ import annotations

from typing import Final
from urllib.parse import urljoin

from flexget.entry import Entry

from ..core.entry import SignInEntry
# Removed reseed functionality
from ..base.sign_in import SignState, check_final_state
from ..base.work import Work
from ..schema.gazelle import Gazelle
from utils import net_utils


class MainClass(Gazelle, Reseed):
    URL: Final = 'https://greatposterwall.com/'
    USER_CLASSES: Final = {
        'downloaded': [214748364800, 10995116277760],
        'share_ratio': [1.2, 1.2],
        'days': [14, 140]
    }

    @classmethod
    def sign_in_build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
        return [
            Work(
                url='/',
                method=self.sign_in_by_get,
                succeed_regex=[('class="HeaderProfile-name.*?">\n(.+?)</a>', 1)],
                assert_state=(check_final_state, SignState.SUCCEED),
                is_base_content=True
            )
        ]

    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        net_utils.dict_merge(selector, {
            'detail_sources': {
                'default': {
                    'elements': {
                        'table': 'div.SidebarItemStats.SidebarItem > ul',
                        'join_date': '#join-date-value'
                    }
                },
                'extend': {
                    'link': '/ajax.php?action=community_stats&userid={}'
                }
            },
            'details': {
                'points': None,
            }
        })
        return selector

    @classmethod
    