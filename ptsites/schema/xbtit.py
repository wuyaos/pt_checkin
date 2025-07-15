import re
from abc import ABC, abstractmethod
from datetime import date
from urllib.parse import urljoin

from dateutil.parser import parse
from bs4 import BeautifulSoup, Tag

from .private_torrent import PrivateTorrent
from ..base.entry import SignInEntry
from ..base.request import check_network_state, NetworkState
from ..base.sign_in import check_final_state, SignState, Work
from ..utils import common


class XBTIT(PrivateTorrent, ABC):
    @property
    @abstractmethod
    def SUCCEED_REGEX(self) -> str:
        pass

    def sign_in_build_workflow(
        self, entry: SignInEntry, config: dict
    ) -> list[Work]:
        return [
            Work(
                url='/',
                method=self.sign_in_by_get,
                succeed_regex=[self.SUCCEED_REGEX],
                assert_state=(check_final_state, SignState.SUCCEED),
                is_base_content=True
            )
        ]

    @property
    def details_selector(self) -> dict:
        return {
            'user_id': r'usercp\.php\?uid=(\d+)',
            'detail_sources': {
                'default': {
                    'link': '/usercp.php?uid={}',
                    'elements': {
                        'bar': 'body > div.mainmenu > table:nth-child(5)',
                        'table': '#CurrentDetailsHideShowTR'
                    }
                }
            },
            'details': {
                'uploaded': {
                    'regex': r'↑.([\d,.]+ [ZEPTGMK]?iB)'
                },
                'downloaded': {
                    'regex': r'↓.([\d,.]+ [ZEPTGMK]?iB)'
                },
                'share_ratio': {
                    'regex': r'Ratio: ([\d.]+)'
                },
                'points': {
                    'regex': r'Bonus Points:.+?([\d,.]+)'
                },
                'join_date': {
                    'regex': r'Joined on.*?(\d{2}/\d{2}/\d{4})',
                    'handle': self.handle_join_date
                },
                'seeding': {
                    'regex': r'Seeding (\d+)'
                },
                'leeching': {
                    'regex': r'Leeching (\d+)'
                },
                'hr': None
            }
        }

    def get_XBTIT_message(
        self, entry: SignInEntry, config: dict,
        messages_url_regex: str = r'usercp\.php\?uid=\d+&do=pm&action=list'
    ) -> None:
        if not (base_content := entry.get('base_content')) or not (
            messages_url_match := re.search(messages_url_regex, base_content)
        ):
            entry.fail_with_prefix('Can not found messages_url.')
            return

        messages_url = urljoin(entry['url'], messages_url_match.group())
        message_box_response = self.request(entry, 'get', messages_url)
        if not (
            message_box_response and
            check_network_state(
                entry, messages_url, message_box_response
            ) == NetworkState.SUCCEED and
            (decode_response := common.decode(message_box_response))
        ):
            entry.fail_with_prefix(
                f'Can not read message box! url:{messages_url}')
            return

        message_elements = BeautifulSoup(decode_response, 'lxml').select(
            'tr > td.lista:nth-child(1)')
        unread_elements = filter(lambda element: element.get_text(
            strip=True) == 'no', message_elements)
        failed = False
        for unread_element in unread_elements:
            next_siblings = list(unread_element.find_next_siblings('td'))
            if len(next_siblings) < 3:
                continue
            td = next_siblings[2]
            title = td.text.strip()
            if not isinstance(td, Tag) or not (
                a_tag := td.find('a')
            ) or not isinstance(a_tag, Tag) or not (
                href := a_tag.get('href')
            ):
                continue

            if isinstance(href, str):
                message_url = urljoin(messages_url, href)
            else:
                continue
            message_response = self.request(entry, 'get', message_url)
            message_body = 'Can not read message body!'
            if not (
                message_response and
                check_network_state(
                    entry, message_url, message_response
                ) == NetworkState.SUCCEED and
                (decode_response := common.decode(message_response))
            ):
                failed = True
            else:
                body_element = BeautifulSoup(
                    decode_response, 'lxml'
                ).select_one(
                    '#PrivateMessageHideShowTR > td > table:nth-child(1) > '
                    'tbody > tr:nth-child(2) > td'
                )
                if body_element:
                    message_body = body_element.text.strip()
                else:
                    failed = True

            entry['messages'] = entry['messages'] + (
                f'\nTitle: {title}\nLink: {message_url}\n{message_body}')
        if failed:
            entry.fail_with_prefix('Can not read one or more message body!')

    def get_messages(self, entry: SignInEntry, config: dict) -> None:
        self.get_XBTIT_message(entry, config)

    def handle_join_date(self, value: str) -> date:
        return parse(value, dayfirst=True).date()

