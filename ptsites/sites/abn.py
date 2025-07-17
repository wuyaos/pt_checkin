import re
from datetime import datetime
from typing import Final

from dateutil.relativedelta import relativedelta

from ..base.entry import SignInEntry
from ..base.request import check_network_state, NetworkState
from ..base.sign_in import SignState, check_final_state
from ..base.work import Work
from ..schema.private_torrent import PrivateTorrent
from ..utils.common import get_module_name


class MainClass(PrivateTorrent):
    URL: Final = 'https://abn.lol/'
    USER_CLASSES: Final = {
        'uploaded': [5368709120000],
        'share_ratio': [3.05]
    }

    @classmethod
    def sign_in_build_schema(cls) -> dict:
        return {
            get_module_name(cls): {
                'type': 'object',
                'properties': {
                    'login': {
                        'type': 'object',
                        'properties': {
                            'username': {'type': 'string'},
                            'password': {'type': 'string'}
                        },
                        'additionalProperties': False
                    }
                },
                'additionalProperties': False
            }
        }

    def sign_in_build_login_workflow(
        self, entry: SignInEntry, config: dict
    ) -> list[Work]:
        return [
            Work(
                url='/Home/Login?ReturnUrl=%2F',
                method=self.sign_in_by_get,
                assert_state=(check_network_state, NetworkState.SUCCEED),
            ),
            Work(
                url='/Home/Login',
                method=self.sign_in_by_login,
                succeed_regex=[r'Déconnexion'],
                assert_state=(check_final_state, SignState.SUCCEED),
                is_base_content=True,
                response_urls=['/'],
            )
        ]

    def sign_in_build_login_data(
        self, login: dict, last_content: str | None
    ) -> dict:
        if not last_content:
            raise ValueError("last_content is not provided")
        token_regex = r'(?<=name="__RequestVerificationToken" type="hidden" value=").*?(?=")'
        token_match = re.search(token_regex, last_content)
        if not token_match:
            raise ValueError("Can not find __RequestVerificationToken")
        return {
            'Username': login['username'],
            'Password': login['password'],
            'RememberMe': ['true', 'false'],
            '__RequestVerificationToken': token_match.group(),
        }

    @property
    def details_selector(self) -> dict:
        points_selector = (
            'div.navbar-collapse.collapse.d-sm-inline-flex > '
            'ul:nth-child(6) > li:nth-child(3)'
        )
        stats_selector = (
            'div.row.row-padding > div.col-lg-3 > '
            'div:nth-child(2) > div.box-body'
        )
        return {
            'detail_sources': {
                'default': {
                    'link': '/User',
                    'elements': {
                        'points': points_selector,
                        'stats': stats_selector,
                    }
                }
            },
            'details': {
                'uploaded': {
                    'regex': r"Upload\s*:\s*([\d,.]+\s*[ZEPTGMK]?o)",
                    'handle': self.handle_amount_of_data
                },
                'downloaded': {
                    'regex': r"Download\s*:\s*([\d,.]+\s*[ZEPTGMK]?o)",
                    'handle': self.handle_amount_of_data
                },
                'share_ratio': {
                    'regex': r"Ratio\s*:\s*(∞|[\d,.]+)",
                    'handle': self.handle_share_ratio
                },
                'points': {
                    'regex': r"Choco's\s*:\s*([\d,.]+)",
                    'handle': self.handle_points
                },
                'join_date': {
                    'regex': r"(?m)Inscrit\s*:\s*(.+?)$",
                    'handle': self.handle_join_date
                },
                'seeding': None,
                'leeching': None,
                'hr': None
            }
        }

    def handle_amount_of_data(self, value: str) -> str:
        return value.replace('o', 'B').replace(',', '.')

    def handle_share_ratio(self, value: str) -> str:
        return '0' if value == '∞' else value.replace(',', '.')

    def handle_points(self, value: str) -> str:
        return value.replace(',', '.')

    def handle_join_date(self, value: str) -> datetime:
        value = value.removeprefix('Il y a ').replace('et', '')
        value = value.replace('seconde', 'second').replace('heure', 'hour')
        value = value.replace('jour', 'day').replace('semaine', 'week')
        value = value.replace('mois', 'months').replace('an', 'year')
        value_split = value.replace('années', 'years').split()

        time_pairs = [
            value_split[i:i + 2] for i in range(0, len(value_split), 2)
        ]
        kwargs = {
            unit if unit.endswith('s') else f'{unit}s': int(amount)
            for amount, unit in time_pairs
        }
        return datetime.now() - relativedelta(**kwargs)  # type: ignore
