import re
from abc import ABC

from .private_torrent import PrivateTorrent
from ..base.entry import SignInEntry
from ..base.request import NetworkState, check_network_state
from ..base.sign_in import SignState, check_final_state
from ..base.work import Work
from ..utils.common import get_module_name
from ..utils.value_handler import handle_infinite, handle_join_date


class Luminance(PrivateTorrent, ABC):
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
                url='/login',
                method=self.sign_in_by_get,
                assert_state=(check_network_state, NetworkState.SUCCEED),
            ),
            Work(
                url='/login',
                method=self.sign_in_by_login,
                succeed_regex=[r'Logout|Kilpés'],
                assert_state=(check_final_state, SignState.SUCCEED),
                is_base_content=True,
                response_urls=['/'],
            )
        ]

    @property
    def details_selector(self) -> dict:
        return {
            'user_id': fr"(?<={re.escape('user.php?id=')})(.+?)(?=\")",
            'detail_sources': {
                'default': {
                    'do_not_strip': True,
                    'link': '/user.php?id={}',
                    'elements': {
                        'stats': '#content > div > div.sidebar > div:nth-child(4)',  # noqa: E501
                        'credits': '#bonusdiv > h4',
                        'connected': '#content > div > div.sidebar > div:nth-child(10)',  # noqa: E501
                    }
                }
            },
            'details': {
                'uploaded': {
                    'regex': r'(?:Uploaded|Feltöltve): ([\d.]+ [ZEPTGMK]?i?B)'
                },
                'downloaded': {
                    'regex': r'(?:Downloaded|Letöltve): ([\d.]+ [ZEPTGMK]?i?B)'
                },
                'share_ratio': {
                    'regex': r'(?:Ratio|Arány): <.*?> (∞|[\d,.]+)',
                    'handle': handle_infinite
                },
                'points': {
                    'regex': r'(?:Credits|Bónuszpontok):\s*([\d,.]+)'
                },
                'join_date': {
                    'regex': (
                        r'(?:Joined|Regisztrált):.*?title="((\w+ ){2}\w+)'
                    ),
                    'handle': handle_join_date
                },
                'seeding': {
                    'regex': r'(?<=Seeding: )([\d,]+)'
                },
                'leeching': {
                    'regex': r'(?<=Leeching: )([\d,]+)'
                },
                'hr': None
            }
        }
