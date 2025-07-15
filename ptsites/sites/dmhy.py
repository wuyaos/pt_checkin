import re
import time
from io import BytesIO
from typing import Any
from urllib.parse import urljoin

from PIL import Image
from requests import Response

from ..base.entry import SignInEntry
from ..base.request import check_network_state
from ..base.sign_in import SignState, Work, check_sign_in_state
from ..schema.private_torrent import PrivateTorrent
from ..utils.baidu_ocr import BaiduOcrClient
from ..utils.logger import logger

try:
    from fuzzywuzzy import fuzz, process
except ImportError:
    fuzz = process = None


class MainClass(PrivateTorrent):
    @property
    def URL(self) -> str:
        return 'https://u2.dmhy.org/'

    SUCCEED_REGEX = '(?<=魔力值)[^>]*>([\\d,.]+)'
    USERNAME_REGEX = '<a href="userdetails.php\\?id=\\d+">(?P<username>.*)</a>'
    DOWNLOADED_REGEX = '(?<=下载量)[^>]*>([\\d.]+\\s[ZEPTGMK]B)'
    UPLOADED_REGEX = '(?<=上传量)[^>]*>([\\d.]+\\s[ZEPTGMK]B)'
    BONUS_REGEX = '(?<=魔力值)[^>]*>([\\d,.]+)'
    MESSAGE_REGEX = '(?<=短消息)[^>]*>(\\d+)'
    RATIO_REGEX = '(?<=分享率)[^>]*>(∞|[\\d.]+)'
    DATA_REGEX = {
        'regex_keys': [
            '<input type="submit" name="(captcha_.*?)" value="(.*?)" />'
        ],
        'data': {
            'answer':
                '{<textarea name="answer" rows="5" cols="40">'
                '(.*?)</textarea>}',
            'question_id':
                '{<input type="hidden" name="questionid" value="(\\d)" />}',
            'uid':
                '{<input type="hidden" name="uid" value="(\\d+)" />}',
            'verify':
                '{<input type="hidden" name="verify" value="([a-z0-9]{8})" />}'
        }
    }

    def sign_in_build_workflow(self, entry: SignInEntry,
                               config: dict) -> list[Work]:
        site_config = entry['site_config']
        succeed_regex: list[str | tuple] = [
            (self.USERNAME_REGEX.format(
                username=site_config.get('username')) + self.SUCCEED_REGEX),
            '大変恐縮ながら、認証に失敗いたしました。'
        ]
        return [
            Work(
                url='/index.php',
                method=self.sign_in_by_get,
                succeed_regex=succeed_regex,
                assert_state=(check_sign_in_state, SignState.NO_SIGN_IN),
                is_base_content=True),
            Work(
                url='/showup.php',
                method=self.sign_in_by_get,
                succeed_regex=succeed_regex,
                assert_state=(check_sign_in_state, SignState.NO_SIGN_IN),
                is_base_content=True),
            Work(
                url='/showup.php?action=show',
                method=self.sign_in_by_post,
                data=self.DATA_REGEX['data'],
                succeed_regex=succeed_regex,
                assert_state=(check_sign_in_state, SignState.NO_SIGN_IN),
                reload_regex='image\\.php\\?action=reload_adbc2&div=showup&rand=\\d+'
            ),
            Work(
                url='/showup.php?action=show',
                method=self.sign_in_by_anime,
                succeed_regex=succeed_regex,
                assert_state=(check_sign_in_state, SignState.NO_SIGN_IN),
                img_regex='(?<=(<img src=")).*?(?=(" alt="showup"))',
                **self.DATA_REGEX)
        ]

    def sign_in_by_anime(self, entry: SignInEntry, config: dict, work: Work,
                         last_content: str | None) -> Response | None:
        ocr_config = config.get('ocr', {})
        if not ocr_config.get('enable'):
            return None
        self.times = 0
        if not (data := self.build_data(entry, config, work, last_content,
                                        ocr_config)):
            entry.fail_with_prefix(
                'Maximum number of retries reached'
                if self.times == ocr_config.get('retry') else
                'build_data failed')
            return None
        logger.info(data)
        return self.request(entry, 'post', work.url, data=data)

    def build_data(self, entry: SignInEntry, config: dict, work: Work,
                   base_content: str | None, ocr_config: dict) -> dict | None:
        if not base_content:
            return None
        if entry.get('failed'):
            return None
        self.times += 1
        img_regex = getattr(work, 'img_regex', None)
        if not (img_regex and
                (img_url_match := re.search(img_regex, base_content))):
            entry.fail_with_prefix(
                f'Cannot find img_url_match, url: {work.url}')
            return None
        img_url = img_url_match.group()
        entry_url = entry.get('url')
        if not entry_url:
            return None
        data: dict[str, Any] = {}
        char_count = ocr_config.get('char_count', 0)
        if images := self.get_image(entry, config, img_url, char_count):
            if not (process and fuzz):
                entry.fail_with_prefix(
                    'Dependency does not exist: [fuzzywuzzy]')
                return None
            image1, image2, new_image = images
            if entry.get('failed'):
                return None
            baidu_ocr_client = BaiduOcrClient(entry, config)
            ocr_text1 = baidu_ocr_client.get_jap_ocr(image1)
            ocr_text2 = baidu_ocr_client.get_jap_ocr(image2)
            if not (ocr_text1 and ocr_text2):
                return None
            oct_text = (ocr_text1
                        if len(ocr_text1) > len(ocr_text2) else ocr_text2)
            if oct_text and len(oct_text) > char_count:
                if not (work_data := work.data):
                    return None
                for key, regex in work_data.items():
                    if not (value_search := re.search(
                            regex, base_content, re.DOTALL)):
                        entry.fail_with_prefix(
                            f'Cannot find key: {key}, url: {work.url}')
                        return None
                    value = value_search.group(1)
                    if key == 'answer':
                        ratio_score = 0
                        regex_keys = getattr(work, 'regex_keys', [])
                        for regex_key in regex_keys:
                            if not (regex_key_search := re.findall(
                                    regex_key, base_content, re.DOTALL)):
                                entry.fail_with_prefix(
                                    'Cannot find regex_key: {}, url: {}'.format(
                                        regex_key, work.url))
                                return None
                            for captcha_value, captcha_text in regex_key_search:
                                answer_list = list(
                                    filter(
                                        lambda x2: len(x2) > 0,
                                        map(
                                            lambda x: ''.join(
                                                re.findall(
                                                    r'[\u2E80-\u9FFF]', x)),
                                            value.split('\n'))))
                                if answer_list:
                                    extract_result = process.extractOne(
                                        oct_text,
                                        answer_list,
                                        scorer=fuzz.partial_ratio)
                                    if extract_result and len(extract_result) == 2:
                                        split_value, partial_ratio = extract_result
                                        if partial_ratio > ratio_score:
                                            data['answer'] = captcha_value
                                            data['id'] = split_value
                                            ratio_score = partial_ratio
                            if (ratio_score and
                                    ratio_score > ocr_config.get('score', 80)):
                                break
                    else:
                        data[key] = value
                if data.get('answer'):
                    return data
        if self.times >= ocr_config.get('retry', 5):
            return None
        reload_regex = getattr(work, 'reload_regex', None)
        if not (reload_regex and
                (reload_url_match := re.search(reload_regex, base_content))):
            return None
        reload_url = reload_url_match.group()
        real_reload_url = urljoin(entry_url, reload_url)
        reload_response = self.request(entry, 'get', real_reload_url)
        reload__net_state = check_network_state(entry, real_reload_url,
                                                reload_response)
        if reload__net_state:
            entry.fail_with_prefix(
                f'reload failed, net_state: {reload__net_state}')
            return None
        reload_content_response = self.request(entry, 'get', work.url)
        if not reload_content_response:
            return None
        return self.build_data(entry, config, work,
                               reload_content_response.text, ocr_config)

    def get_image(self, entry: SignInEntry, config: dict, img_url: str,
                  char_count: int) -> tuple | None:
        dmhy_image = DmhyImage()
        if not (new_image := self.get_new_image(entry, img_url)):
            return None
        self.save_iamge(new_image, 'new_image.png')
        if not dmhy_image.check_analysis(new_image):
            self.save_iamge(new_image, 'z_failed.png')
            return None
        baidu_ocr_client = BaiduOcrClient(entry, config)
        original_text = baidu_ocr_client.get_jap_ocr(new_image)
        if original_text is None or len(original_text) < char_count:
            return None
        image_last = None
        image_a_split_1, image_a_split_2 = dmhy_image.split_image(
            new_image, dmhy_image.template_a)
        self.save_iamge(image_a_split_1, 'a_split_1.png')
        self.save_iamge(image_a_split_2, 'a_split_2.png')
        image_b_split_1, image_b_split_2 = dmhy_image.split_image(
            new_image, dmhy_image.template_b)
        self.save_iamge(image_b_split_1, 'b_split_1.png')
        self.save_iamge(image_b_split_2, 'b_split_2.png')
        image_last = dmhy_image.compare_images(image_a_split_1,
                                               image_b_split_1)
        image_last2 = dmhy_image.compare_images(image_a_split_2,
                                                image_b_split_2)
        if image_last and image_last2:
            self.save_iamge(image_last[0], 'a_split_1_diff.png')
            self.save_iamge(image_last[1], 'b_split_1_diff.png')
            self.save_iamge(image_last[2], 'split_1_diff.png')
            self.save_iamge(image_last2[0], 'a_split_2_diff.png')
            self.save_iamge(image_last2[1], 'b_split_2_diff.png')
            self.save_iamge(image_last2[2], 'split_2_diff.png')
            return image_last[2], image_last2[2], new_image
        elif image_last:
            self.save_iamge(image_last[0], 'identical.png')
            return image_last[0], image_last[0], new_image
        elif image_last2:
            self.save_iamge(image_last2[0], 'identical.png')
            return image_last2[0], image_last2[0], new_image
        else:
            return None

    def get_new_image(self, entry: SignInEntry,
                      img_url: str) -> Image.Image | None:
        time.sleep(3)
        entry_url = entry.get('url')
        if not entry_url:
            return None
        real_img_url = urljoin(entry_url, img_url)
        base_img_response = self.request(entry, 'get', real_img_url)
        if not (base_img_response and base_img_response.status_code == 200 and
                base_img_response.url !=
                urljoin(entry_url, '/adbc.php?see=HENTAI')):
            return None
        new_image = Image.open(BytesIO(base_img_response.content))
        return new_image

    def save_iamge(self, new_image: Image.Image | None, path: str) -> None:
        if new_image:
            new_image.save(path)


class DmhyImage:
    template_a = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    template_b = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]

    def check_analysis(self, image: Image.Image):
        pixel1 = image.getpixel((0, 0))
        pixel2 = image.getpixel((image.width - 1, 0))
        pixel3 = image.getpixel((0, image.height - 1))
        pixel4 = image.getpixel((image.width - 1, image.height - 1))
        if isinstance(pixel1, (int, float)) or isinstance(
                pixel2, (int, float)) or isinstance(
                    pixel3, (int, float)) or isinstance(pixel4, (int, float)):
            return False
        if not all(isinstance(p, (tuple, list)) for p in [pixel1, pixel2, pixel3, pixel4]):
            return False
        if pixel1 is None or pixel2 is None or pixel3 is None or pixel4 is None:
            return False
        return not (pixel1[:3] == pixel2[:3] and pixel3[:3] == pixel4[:3])

    def split_image(self, image: Image.Image, template: list):
        image_a = Image.new('RGB', (120, 20))
        image_b = Image.new('RGB', (120, 20))
        for i in range(12):
            image_a.paste(
                image.crop(
                    (template[i] * 10, 0, template[i] * 10 + 10, 20)),
                (i * 10, 0))
            image_b.paste(
                image.crop(
                    (template[i] * 10, 20, template[i] * 10 + 10, 40)),
                (i * 10, 0))
        return image_a, image_b

    def compare_images(self, image_a: Image.Image, image_b: Image.Image):
        if image_a.tobytes() == image_b.tobytes():
            return image_a, image_a, image_a
        image_p = Image.new('RGB', (120, 20))
        for i in range(120):
            for j in range(20):
                p_a = image_a.getpixel((i, j))
                p_b = image_b.getpixel((i, j))
                if isinstance(p_a, (int, float)) or isinstance(p_b, (int, float)):
                    continue
                if p_a == p_b:
                    image_p.putpixel((i, j), (255, 255, 255))
                else:
                    if p_a:
                        image_p.putpixel((i, j), p_a)
        return image_a, image_b, image_p
