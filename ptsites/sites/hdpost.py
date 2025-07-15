from __future__ import annotations

import re
from typing import Final


from ..base.entry import SignInEntry
from bs4 import BeautifulSoup
from ..base.request import check_network_state, NetworkState, Response
from ..base.sign_in import check_final_state, SignState, Work
from ..schema.unit3d import Unit3D
from ..utils import common
from ..utils.common import get_module_name
from ..utils.value_handler import handle_join_date, handle_infinite


class MainClass(Unit3D):
    @property
    def URL(self) -> str:
        return 'https://pt.hdpost.top'
    USER_CLASSES: Final = {
        'uploaded': [109951162777600],
        'days': [365]
    }

    @classmethod
    def sign_in_build_schema(cls) -> dict:
        return {
            get_module_name(cls): {
                'type': 'object',
                'properties': {
                    'cookie': {'type': 'string'},
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
            self, entry: SignInEntry, config: dict) -> list[Work]:
        return [
            Work(
                url='/login',
                method=self.sign_in_by_get,
                assert_state=(check_network_state, NetworkState.SUCCEED),
            ),
            Work(
                url='/login',
                method=self.sign_in_by_login,
                assert_state=(check_network_state, NetworkState.SUCCEED),
                response_urls=['', '/pages/1'],
            )
        ]

    def sign_in_build_workflow(self, entry: SignInEntry,
                               config: dict) -> list[Work]:
        return [
            Work(
                url='/',
                method=self.sign_in_by_get,
                succeed_regex=[('https://pt.hdpost.top/users/(.*?)/', 1)],
                assert_state=(check_final_state, SignState.SUCCEED),
                use_last_content=True,
                is_base_content=True,
                response_urls=['', '/pages/1'],
            )
        ]

    def sign_in_by_login(self, entry: SignInEntry, config: dict, work: Work,
                         last_content: str) -> Response | None:
        login_page = BeautifulSoup(last_content, 'lxml')
        hidden_input = login_page.select_one('form > input:nth-last-child(2)')
        if not hidden_input:
            entry.fail_with_prefix('Cannot find hidden input')
            return None
        name = hidden_input.attrs['name']
        value = hidden_input.attrs['value']
        if not (login := entry['site_config'].get('login')):
            entry.fail_with_prefix('Login data not found!')
            return None
        if not (_token := re.search(r'(?<=name="_token" value=").+?(?=")',
                                   last_content)):
            entry.fail_with_prefix('Cannot find _token')
            return None
        if not (_captcha := re.search(r'(?<=name="_captcha" value=").+?(?=")',
                                     last_content)):
            entry.fail_with_prefix('Cannot find _captcha')
            return {}
        data = {
            '_token': _token.group(),
            'username': login['username'],
            'password': login['password'],
            'remember': 'on',
            '_captcha': _captcha.group(),
            '_username': '',
            name: value,
        }
        return self.request(entry, 'post', work.url, data=data)

    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        common.dict_merge(selector, {
            'user_id': '/users/(.*?)/',
            'detail_sources': {
                'default': {
                    'do_not_strip': True,
                    'elements': {
                        'bar': 'ul.top-nav__ratio-bar',
                        'header': '.profile__registration',
                        'data_table': 'aside'
                    }
                }
            },
            'details': {
                'uploaded': {
                    'regex': '上传.+?([\\d.]+ [ZEPTGMK]?iB)',
                             'handle': self.remove_symbol
                },
                'downloaded': {
                    'regex': '下载.+?([\\d.]+ [ZEPTGMK]?iB)',
                    'handle': self.remove_symbol
                },
                'share_ratio': {
                    'regex': '分享率.+?([\\d.]+)',
                    'handle': handle_infinite
                },
                'points': {
                    'regex': '魔力.+?(\\d[\\d,. ]*)',
                    'handle': self.handle_points
                },
                'join_date': {
                    'regex': r'注册日期.*?(\d{4}-\d{2}-\d{2})',
                    'handle': handle_join_date
                },
                'seeding': {
                    'regex': '做种.+?(\\d+)'
                },
                'leeching': {
                    'regex': '吸血.+?(\\d+)'
                },
                'hr': {
                    'regex': 'H&amp;R.+?(\\d+)'
                }
            }
        })
        return selector


    def remove_symbol(self, value: str):
        return value.replace('\xa0', '')
