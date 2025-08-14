from __future__ import annotations

import re
from io import BytesIO
from typing import Final
from urllib.parse import urljoin

from requests import Response

from ..core.entry import SignInEntry
from ..base.request import check_network_state, NetworkState
# Removed reseed functionality
from ..base.sign_in import check_final_state, SignState, check_sign_in_state
from ..base.work import Work
from ..schema.nexusphp import NexusPHP
from ..utils import baidu_ocr
from ..utils import net_utils

try:
    from PIL import Image
except ImportError:
    Image = None


class MainClass(NexusPHP):
    URL: Final = 'https://open.cd/'
    IGNORE_TITLE = '種子被刪除'
    USER_CLASSES: Final = {
        'downloaded': [644245094400, 3298534883328],
        'share_ratio': [3.5, 5],
        'days': [175, 210]
    }

    def sign_in_build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
        return [
            Work(
                url='/',
                method=self.sign_in_by_get,
                succeed_regex=['查看簽到記錄'],
                assert_state=(check_sign_in_state, SignState.NO_SIGN_IN),
                is_base_content=True,
            ),
            Work(
                url='/plugin_sign-in.php',
                method=self.sign_in_by_ocr,
                succeed_regex=['{"state":"success","signindays":"\\d+","integral":"\\d+"}'],
                fail_regex='验证码错误',
                response_urls=['/plugin_sign-in.php', '/plugin_sign-in.php?cmd=signin'],
                assert_state=(check_final_state, SignState.SUCCEED),
            ),
        ]

    def sign_in_by_ocr(self, entry: SignInEntry, config: dict, work: Work, last_content: str) -> Response | None:
        image_hash_response = self.request(entry, 'get', work.url, config)
        image_hash_network_state = check_network_state(entry, work, image_hash_response)
        if image_hash_network_state != NetworkState.SUCCEED:
            entry.fail_with_prefix('Get image hash failed.')
            return None
        # 尝试多种方式获取页面内容
        image_hash_content = None
        try:
            # 首先尝试使用response.text（自动处理编码和压缩）
            image_hash_content = image_hash_response.text
        except Exception:
            # 如果失败，使用net_utils.decode作为备用
            image_hash_content = net_utils.decode(image_hash_response)

        if not image_hash_content:
            entry.fail_with_prefix('Failed to decode response content.')
            return None

        # 检查是否被重定向到登录页面
        login_indicators = ['未登錄!', '錯誤: 該頁面必須在登錄後才能訪問']
        if any(indicator in image_hash_content for indicator in login_indicators):
            entry.fail_with_prefix('Not logged in. Please provide valid cookie.')
            return None

        image_hash_re = re.search('(?<=imagehash=).*?(?=")', image_hash_content)
        img_src_re = re.search('(?<=img src=").*?(?=")', image_hash_content)

        if image_hash_re and img_src_re:
            image_hash = image_hash_re.group()
            img_src = img_src_re.group()
            img_url = urljoin(entry['url'], img_src)
            img_response = self.request(entry, 'get', img_url, config)
            img_network_state = check_network_state(entry, img_url, img_response)
            if img_network_state != NetworkState.SUCCEED:
                entry.fail_with_prefix('Get image failed.')
                return None
        else:
            entry.fail_with_prefix(
                'Cannot find key: image_hash. '
                'Page content may have changed or login required.'
            )
            return None

        img = Image.open(BytesIO(img_response.content))
        code, img_byte_arr = baidu_ocr.get_ocr_code(img, entry, config)
        if not entry.failed:
            if len(code) == 6:
                params = {
                    'cmd': 'signin'
                }
                data = {
                    'imagehash': (None, image_hash),
                    'imagestring': (None, code)
                }
                return self.request(
                    entry, 'post', work.url, config, files=data, params=params
                )
        return None

    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        net_utils.dict_merge(selector, {
            'detail_sources': {
                'default': {
                    'elements': {
                        'bar': (
                            '#info_block > tbody > tr > td > table > '
                            'tbody > tr > td:nth-child(2)'
                        )
                    }
                }
            }
        })
        return selector

    def get_messages(self, entry: SignInEntry, config: dict) -> None:
        self.get_nexusphp_messages(
            entry, config, ignore_title=self.IGNORE_TITLE
        )
