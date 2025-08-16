from typing import Final
import re
import requests
from requests import Response
from io import BytesIO

from ..core.entry import SignInEntry
from ..base.sign_in import check_final_state, SignState
from ..base.work import Work
from ..schema.nexusphp import Attendance
from ..utils import baidu_ocr

try:
    from PIL import Image
except ImportError:
    Image = None


class MainClass(Attendance):
    URL: Final = 'https://si-qi.xyz/'
    USER_CLASSES: Final = {
        'downloaded': [1073741824000],  # 1TB
        'share_ratio': [2.0],           # 分享率要求
        'days': [30]                    # 天数要求
    }

    def sign_in_build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
        return [
            Work(
                url='/attendance.php',
                method=self.sign_in_by_captcha,
                succeed_regex=[
                    '这是您的第.*?次签到，已连续签到.*?天，本次签到获得.*?个魔力值',
                    '您今天已经签到过了',
                    '签到成功',
                    '<h2.*?>签到成功</h2>'
                ],
                assert_state=(check_final_state, SignState.SUCCEED),
                is_base_content=True  # 添加这个标志，确保响应内容被设置为base_content
            ),
        ]

    def sign_in_by_captcha(self, entry: SignInEntry, config: dict,
                           work: Work, last_content: str) -> Response | None:
        """处理验证码签到"""
        # 获取签到页面
        response = self.request(entry, 'get', work.url)
        if not response:
            entry.fail_with_prefix('无法获取签到页面')
            return None
        last_content = response.text

        # 检查是否已经签到成功
        success_patterns = [
            r'这是您的第.*?次签到，已连续签到.*?天，本次签到获得.*?个魔力值',
            r'您今天已经签到过了',
            r'<h2.*?>签到成功</h2>'
        ]

        for pattern in success_patterns:
            if re.search(pattern, last_content):
                # 已经签到成功，创建成功响应
                mock_response = Response()
                mock_response._content = last_content.encode('utf-8')
                mock_response.status_code = 200
                mock_response.url = 'https://si-qi.xyz/attendance.php'
                return mock_response

        # 检查验证码表单
        imagehash_match = re.search(r'name="imagehash" value="([^"]+)"', last_content)
        if not imagehash_match:
            entry.fail_with_prefix('页面没有验证码表单')
            return None

        imagehash = imagehash_match.group(1)

        # 获取验证码图片（直接请求，不通过FlareSolverr）
        captcha_url = f'/image.php?action=regimage&imagehash={imagehash}&secret='
        full_url = self.URL.rstrip('/') + captcha_url

        try:
            # 使用标准requests获取验证码图片，避免FlareSolverr的开销
            captcha_response = self.request(
                entry, 'get', captcha_url, config,
                force_default=True,  # 强制使用标准requests
                timeout=30
            )
            if not captcha_response or captcha_response.status_code != 200:
                entry.fail_with_prefix('无法获取验证码图片')
                return None
        except Exception as e:
            entry.fail_with_prefix(f'获取验证码图片失败: {e}')
            return None

        # OCR识别验证码
        try:
            if Image is None:
                entry.fail_with_prefix('PIL库未安装')
                return None
            img = Image.open(BytesIO(captcha_response.content))
            captcha_text, _ = baidu_ocr.get_ocr_code(img, entry, config)
            if not captcha_text or len(captcha_text) < 4:
                entry.fail_with_prefix('验证码识别失败')
                return None
        except Exception as e:
            entry.fail_with_prefix(f'验证码处理失败: {e}')
            return None

        # 提交签到表单
        data = {
            'imagehash': imagehash,
            'imagestring': captcha_text
        }

        return self.request(entry, 'post', work.url, data=data)
