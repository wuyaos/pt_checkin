from __future__ import annotations

from typing import Final
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..base.entry import SignInEntry
from ..base.request import NetworkState, check_network_state
from ..base.sign_in import SignState
from ..base.sign_in import check_final_state
from ..base.work import Work
from ..schema.gazelle import Gazelle
from ..utils import common
from ..utils.common import get_module_name
from ..utils.value_handler import handle_infinite


class MainClass(Gazelle):
    @property
    def URL(self) -> str:
        return 'https://gazellegames.net/'

    @property
    def API_URL(self) -> str:
        return urljoin(self.URL, '/api.php')

    @property
    def MESSAGE_URL(self) -> str:
        return urljoin(self.URL, '/inbox.php?action=viewconv&id={conv_id}')
    USER_CLASSES: Final = {
        'points': [1200, 6000],
    }

    @classmethod
    def sign_in_build_schema(cls) -> dict:
        return {
            get_module_name(cls): {
                'type': 'object',
                'properties': {
                    'cookie': {'type': 'string'},
                    'key': {'type': 'string'},
                    'name': {'type': 'string'}
                },
                'additionalProperties': False
            }
        }

    def sign_in_build_workflow(
        self, entry: SignInEntry, config: dict
    ) -> list[Work]:
        return [
            Work(
                url='/',
                method=self.sign_in_by_get,
                succeed_regex=['Welcome, <a.+?</a>'],
                assert_state=(check_final_state, SignState.SUCCEED),
                is_base_content=True
            )
        ]

    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        common.dict_merge(selector, {
            'detail_sources': {
                'default': {
                    'do_not_strip': True,
                    'elements': {
                        'bar': '#community_stats > ul:nth-child(3)',
                        'table': ('#content > div > div.sidebar > '
                                  'div.box_main_info'),
                        'join_date': '.nobullet span.time'
                    }
                },
                'achievements': {
                    'link': '/user.php?action=achievements',
                    'elements': {
                        'total_point': '#content > div[class=linkbox]'
                    }
                }
            },
            'details': {
                'points': {
                    'regex': 'Total Points: (\\d+)'
                },
                'hr': {
                    'regex': 'Hit \'n\' Runs">(\\d+)'
                },
            }
        })
        return selector

    def get_details(self, entry: SignInEntry, config: dict) -> None:
        site_config = entry['site_config']
        key = site_config.get('key')
        name = site_config.get('name')
        if not (key and name):
            entry.fail_with_prefix('key or name not found')
            return
        params = {
            'request': 'user',
            'key': key,
            'name': name
        }
        details_response_json = self.get_api_response_json(entry, params)
        if not details_response_json:
            return
        response = details_response_json.get('response')
        if not response:
            return

        stats = response.get('stats') or {}
        community = response.get('community') or {}
        personal = response.get('personal') or {}
        achievements = response.get('achievements') or {}

        entry['details'] = {
            'uploaded': f'{stats.get("uploaded", 0)} B',
            'downloaded': f'{stats.get("downloaded", 0)} B',
            'share_ratio': handle_infinite(str(stats.get("ratio", 0))),
            'points': str(achievements.get('totalPoints', 0)),
            'seeding': str(community.get('seeding', 0)),
            'leeching': str(community.get('leeching', 0)),
            'hr': str(personal.get('hnrs', 0))
        }

    def get_messages(self, entry: SignInEntry, config: dict) -> None:
        site_config = entry['site_config']
        key = site_config.get('key')
        if not key:
            entry.fail_with_prefix('key not found')
            return
        params = {'request': 'inbox', 'sort': 'unread', 'key': key}

        messages_response_json = self.get_api_response_json(entry, params)
        if not messages_response_json:
            return

        response = messages_response_json.get('response')
        if not response:
            return
        messages = response.get('messages')
        if not messages:
            return

        unread_messages = filter(lambda m: m.get('unread'), messages)
        failed = False
        for message in unread_messages:
            title = message.get('subject')
            conv_id = message.get('convId')
            message_url = self.MESSAGE_URL.format(conv_id=conv_id)
            message_response = self.request(entry, 'get', message_url)
            if not message_response:
                failed = True
                continue

            network_state = check_network_state(entry, message_url,
                                                message_response)
            message_body = 'Can not read message body!'
            if network_state == NetworkState.SUCCEED:
                decoded_content = common.decode(message_response)
                if not decoded_content:
                    failed = True
                    continue
                body_element = BeautifulSoup(
                    decoded_content, 'lxml'
                ).select_one('.body')
                if body_element:
                    message_body = body_element.text.strip()
            else:
                failed = True

            entry['messages'] = entry['messages'] + (
                f'\nTitle: {title}\nLink: {message_url}\n{message_body}')
        if failed:
            entry.fail_with_prefix('Can not read one or more message body!')

    def get_api_response_json(self, entry: SignInEntry,
                              params: dict) -> dict | None:
        api_url = self.API_URL
        api_response = self.request(entry, 'get', api_url, params=params)
        if not api_response:
            return None
        network_state = check_network_state(entry, api_url, api_response)
        if network_state != NetworkState.SUCCEED:
            return None
        api_response_json = api_response.json()
        if not api_response_json.get('status') == 'success':
            entry.fail_with_prefix(str(api_response_json))
            return None
        return api_response_json

