from __future__ import annotations

import io
from typing import TYPE_CHECKING, Optional, Tuple

from PIL import Image

from ..base.entry import SignInEntry
from ..utils.logger import logger

if TYPE_CHECKING:
    from aip import AipOcr


class BaiduOcrClient:
    def __init__(self, entry: SignInEntry, config: dict):
        self.entry = entry
        self.client: Optional[AipOcr] = self._get_client(config)

    def _get_client(self, config: dict) -> Optional[AipOcr]:
        try:
            from aip import AipOcr
        except ImportError:
            self.entry.fail_with_prefix(
                'Dependency does not exist: [baidu-aip, pillow]')
            return None

        aipocr_config = config.get('aipocr')
        required_keys = ['app_id', 'api_key', 'secret_key']
        if not aipocr_config or not all(
            aipocr_config.get(key) for key in required_keys
        ):
            self.entry.fail_with_prefix('AipOcr not configured.')
            return None

        return AipOcr(
            aipocr_config['app_id'], aipocr_config['api_key'],
            aipocr_config['secret_key']
        )

    def get_jap_ocr(self, img: Image.Image) -> Optional[str]:
        if not self.client:
            return None
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        try:
            result = self.client.basicAccurate(
                img_byte_arr.getvalue(), {'language_type': 'JAP'}
            )
        except Exception:
            return None
        logger.info(f"OCR 识别结果: {result}")
        if result.get('error_msg'):
            return None
        words_result = result.get('words_result')
        if isinstance(words_result, list) and words_result:
            first_result = words_result[0]
            if isinstance(first_result, dict):
                return first_result.get('words', '').replace(' ', '')
        return None

    def get_ocr_code(
            self, img: Image.Image
    ) -> Tuple[Optional[str], Optional[bytes]]:
        if not self.client:
            return None, None
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        width, height = img.size
        for i in range(0, width):
            for j in range(0, height):
                if self._detect_noise(img, i, j, width, height):
                    img.putpixel((i, j), 255)
        try:
            result = self.client.basicAccurate(
                img_byte_arr.getvalue(), {"language_type": "ENG"}
            )
        except Exception as e:
            logger.error(f"OCR 请求失败: {e}")
            return None, None
        logger.info(f"OCR 识别结果: {result}")
        if result.get('error_msg'):
            return None, None
        words_result = result.get('words_result')
        if isinstance(words_result, list) and words_result:
            first_result = words_result[0]
            if isinstance(first_result, dict):
                words = first_result.get('words', '').replace(' ', '')
                return words, img_byte_arr.getvalue()
        return None, None

    @staticmethod
    def _detect_noise(img: Image.Image, i: int, j: int, width: int,
                      height: int) -> bool:
        if i == 0 or i == (width - 1) or j == 0 or j == (height - 1):
            return False
        pixel = img.getpixel((i, j))
        if not isinstance(pixel, tuple) or len(pixel) < 3:
            return False
        if pixel[0] < 220 and pixel[1] < 220 and pixel[2] < 220:
            if (img.getpixel((i - 1, j)) == (255, 255, 255)
                    and img.getpixel((i + 1, j)) == (255, 255, 255)
                    and img.getpixel((i, j - 1)) == (255, 255, 255)
                    and img.getpixel((i, j + 1)) == (255, 255, 255)):
                return True
        return False

