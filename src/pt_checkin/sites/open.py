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

            # 处理HTML实体编码，将&amp;转换为&
            img_src = img_src.replace('&amp;', '&')
            img_url = urljoin(entry['url'], img_src)

            # 验证码图片使用普通requests下载，不使用FlareSolverr和cookie
            import requests
            import os
            from datetime import datetime

            try:
                # 直接使用requests下载图片，不经过FlareSolverr
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://open.cd/plugin_sign-in.php'
                }
                img_response = requests.get(img_url, headers=headers, timeout=30)

                if img_response.status_code != 200:
                    entry.fail_with_prefix(f'Get image failed: HTTP {img_response.status_code}')
                    return None

                # 保存验证码图片到配置文件同级目录
                config_dir = config.get('config_dir', '.')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                captcha_filename = f'open_captcha_{timestamp}.png'
                captcha_path = os.path.join(config_dir, captcha_filename)

                # 清理旧的验证码图片
                try:
                    for file in os.listdir(config_dir):
                        if file.startswith('open_captcha_') and file.endswith('.png'):
                            old_path = os.path.join(config_dir, file)
                            os.remove(old_path)
                except Exception as cleanup_e:
                    # 清理失败不影响主流程
                    pass

                # 保存新的验证码图片
                with open(captcha_path, 'wb') as f:
                    f.write(img_response.content)

            except Exception as e:
                entry.fail_with_prefix(f'Get image failed: {e}')
                return None
        else:
            entry.fail_with_prefix(
                'Cannot find key: image_hash. '
                'Page content may have changed or login required.'
            )
            return None

        # 处理图片内容（现在是标准的requests响应）
        try:
            img_content = img_response.content

            # 验证图片数据
            if len(img_content) < 100:  # 图片数据太小，可能有问题
                entry.fail_with_prefix(f'Image data too small: {len(img_content)} bytes')
                return None

            # 检查是否是HTML页面（有时服务器返回错误页面）
            if img_content.startswith(b'<html') or img_content.startswith(b'<!DOCTYPE'):
                entry.fail_with_prefix('Received HTML instead of image data.')
                return None

            img = Image.open(BytesIO(img_content))

        except Exception as e:
            entry.fail_with_prefix(f'Failed to process image: {e}')
            return None
        code, img_byte_arr = baidu_ocr.get_ocr_code(img, entry, config)
        if not entry.failed:
            if len(code) >= 4:  # 验证码长度可能不是固定6位
                # 构建POST URL
                signin_url = f"{work.url}?cmd=signin"

                # 构建POST数据
                data = {
                    'action': 'signin',
                    'imagehash': image_hash,
                    'imagestring': code
                }
                return self.request(
                    entry, 'post', signin_url, config, data=data
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
