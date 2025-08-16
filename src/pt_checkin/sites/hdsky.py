from __future__ import annotations

import time
from typing import Final

from requests import Response
from loguru import logger

from ..core.entry import SignInEntry
from ..base.sign_in import check_final_state, SignState
from ..base.work import Work
from ..schema.nexusphp import NexusPHP
from ..utils import net_utils
from ..utils.net_utils import get_module_name

try:
    from PIL import Image
except ImportError:
    Image = None


class MainClass(NexusPHP):
    URL: Final = 'https://hdsky.me/'
    TORRENT_PAGE_URL: Final = '/details.php?id={torrent_id}&hit=1'
    DOWNLOAD_URL_REGEX: Final = '/download\\.php\\?id=\\d+&passkey=.*?(?=")'
    USER_CLASSES: Final = {
        'downloaded': [8796093022208, 10995116277760],
        'share_ratio': [5, 5.5],
        'days': [315, 455]
    }

    @classmethod
    def sign_in_build_entry(cls, entry: SignInEntry, config: dict) -> None:
        """构建签到条目，启用浏览器模拟以绕过验证码"""
        super().sign_in_build_entry(entry, config)

        # 为HDSky启用浏览器模拟
        entry['site_name'] = 'hdsky'
        entry['request_method'] = 'browser'  # 强制使用浏览器模拟

        # 添加成功标识配置
        entry['success_indicators'] = {
            'logo': 'HDSky',
            'keywords': ['种子', 'torrent', '用户', '下载', '签到']
        }

    @classmethod
    def sign_in_build_schema(cls) -> dict:
        return {
            get_module_name(cls): {
                'type': 'object',
                'properties': {
                    'cookie': {'type': 'string'},
                    'join_date': {'type': 'string', 'format': 'date'}
                },
                'additionalProperties': False
            }
        }

    def sign_in_build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
        """构建签到工作流 - 使用SmartRequest处理验证码"""
        return [
            Work(
                url='/',
                method=self.sign_in_with_smart_request,  # 使用新的SmartRequest处理验证码
                succeed_regex=['{"success":true'],
                fail_regex='{"success":false',
                assert_state=(check_final_state, SignState.SUCCEED),
                is_base_content=True  # 添加这个标志，确保响应内容被设置为base_content
            ),
        ]

    def sign_in_with_smart_request(self, entry: SignInEntry, config: dict, work: Work, last_content: str) -> Response | None:
        """使用SmartRequest系统处理hdsky验证码签到"""
        try:
            # 使用浏览器模式进行hdsky特殊签到流程
            return self._hdsky_signin_with_browser(entry, config, work)

        except Exception as e:
            entry.fail_with_prefix(f'HDSky签到失败: {e}')
            return None

    def _hdsky_signin_with_browser(self, entry: SignInEntry, config: dict, work: Work) -> Response | None:
        """HDSky签到流程：访问页面 -> 点击签到按钮 -> 获取验证码 -> 处理验证码"""
        try:
            # 获取浏览器管理器
            from ..utils.browser_manager import get_browser_manager
            browser_manager = get_browser_manager(config)

            if not browser_manager or not browser_manager.is_available():
                entry.fail_with_prefix('浏览器管理器不可用')
                return None

            # 获取hdsky站点专用tab页面
            headless = config.get('browser_automation', {}).get('headless', True)
            page = browser_manager.get_site_tab('hdsky', headless=headless)
            if not page:
                entry.fail_with_prefix('无法创建浏览器页面')
                return None

            try:
                # 访问首页
                if work.url.startswith('https'):
                    full_url = work.url
                else:
                    full_url = 'https://hdsky.me' + work.url
                page.get(full_url)
                logger.info(f'访问HDSky首页: {full_url}')

                # 设置cookies
                cookie_str = entry.get('cookie', '')
                if cookie_str:
                    self._set_cookies_like_test(page, cookie_str)

                # 刷新页面以应用cookies
                page.refresh()
                time.sleep(2)

                # 1. 查找并点击签到按钮
                signin_result = self._click_signin_button(page, entry)
                if signin_result == "already_signed":
                    # 已经签到
                    logger.info('HDSky今日已签到')
                    mock_response = self._create_success_response(full_url, '{"success":true,"message":"already_signed"}')
                    # 设置页面HTML作为base_content，用于详情获取
                    entry['base_content'] = page.html
                    return mock_response
                elif not signin_result:
                    entry.fail_with_prefix('点击签到按钮失败')
                    return None

                # 2. 等待验证码弹窗出现并获取imagehash
                imagehash = self._get_imagehash_from_captcha(page, entry)
                if not imagehash:
                    entry.fail_with_prefix('无法获取验证码imagehash')
                    return None

                # 调试：检查验证码相关元素
                self._debug_captcha_elements(page)

                # 3. 下载验证码图片
                captcha_image_path = self._download_captcha_image(imagehash, entry)
                if not captcha_image_path:
                    entry.fail_with_prefix('无法下载验证码图片')
                    return None

                # 4. 识别验证码（这里需要集成OCR或手动输入）
                captcha_text = self._recognize_captcha(captcha_image_path, entry, config)
                if not captcha_text:
                    entry.fail_with_prefix('验证码识别失败')
                    return None

                # 5. 提交验证码
                success = self._submit_captcha_form(page, imagehash, captcha_text, entry)

                # 清理验证码图片
                self._cleanup_captcha_image(captcha_image_path)

                if success:
                    logger.info('HDSky签到成功')
                    mock_response = self._create_success_response(full_url, '{"success":true,"message":"signin_success"}')
                    entry['base_content'] = page.html
                    return mock_response
                else:
                    entry.fail_with_prefix('验证码提交失败')
                    return None

            finally:
                # 签到完成后关闭hdsky站点的tab页面
                try:
                    browser_manager.close_site_tab('hdsky')
                    logger.info('HDSky站点tab页面已关闭')
                except Exception as e:
                    logger.warning(f'关闭HDSky站点tab失败: {e}')

        except Exception as e:
            entry.fail_with_prefix(f'HDSky浏览器签到失败: {e}')
            return None

    def _create_success_response(self, url: str, content: str):
        """创建成功响应对象"""
        from requests import Response as RequestsResponse
        mock_response = RequestsResponse()
        mock_response.status_code = 200
        mock_response._content = content.encode('utf-8')
        mock_response.url = url
        return mock_response

    def _set_cookies_like_test(self, page, cookie_str: str):
        """按照测试文件的方式设置cookies"""
        try:
            # 解析cookie字符串
            cookies = {}
            if cookie_str:
                for item in cookie_str.split(';'):
                    item = item.strip()
                    if '=' in item:
                        name, value = item.split('=', 1)
                        cookies[name.strip()] = value.strip()

            # 逐个设置cookie（参考测试文件）
            for name, value in cookies.items():
                page.set.cookies({name: value})

            logger.info(f"设置了 {len(cookies)} 个cookies")

        except Exception as e:
            logger.error(f"设置cookies失败: {e}")

    def _debug_captcha_elements(self, page):
        """调试验证码相关元素"""
        try:
            logger.info("=== 调试验证码元素 ===")

            # 检查验证码图片
            captcha_img = page.ele('#showupimg', timeout=2)
            if captcha_img:
                logger.info(f"✅ 找到验证码图片: {captcha_img.attr('src')}")
            else:
                logger.warning("❌ 未找到验证码图片 #showupimg")

            # 检查验证码输入框
            input_box = page.ele('#imagestring', timeout=2)
            if input_box:
                logger.info("✅ 找到验证码输入框 #imagestring")
            else:
                logger.warning("❌ 未找到验证码输入框 #imagestring")
                # 尝试其他选择器
                input_box2 = page.ele('input[name="imagestring"]', timeout=2)
                if input_box2:
                    logger.info("✅ 通过name属性找到验证码输入框")
                else:
                    logger.warning("❌ 通过name属性也未找到验证码输入框")

            # 检查提交按钮
            submit_btn = page.ele('#showupbutton', timeout=2)
            if submit_btn:
                logger.info(f"✅ 找到提交按钮: {submit_btn.attr('value')}")
            else:
                logger.warning("❌ 未找到提交按钮 #showupbutton")
                # 尝试其他选择器
                submit_btn2 = page.ele('input[type="button"]', timeout=2)
                if submit_btn2:
                    logger.info(f"✅ 通过type属性找到按钮: {submit_btn2.attr('value')}")
                else:
                    logger.warning("❌ 通过type属性也未找到按钮")

            logger.info("=== 调试完成 ===")

        except Exception as e:
            logger.error(f"调试验证码元素失败: {e}")

    def _click_signin_button(self, page, entry) -> str | bool | None:
        """点击签到按钮，返回签到状态"""
        try:
            # 首先检查页面是否已显示"已签到"状态
            page_source = page.html
            if '[已签到]' in page_source or '已签到' in page_source:
                logger.info('检测到页面显示已签到状态')
                return "already_signed"

            # 查找签到按钮
            signin_button = page.ele('#showup', timeout=10)
            if not signin_button:
                logger.warning('未找到签到按钮，可能已经签到')
                # 再次检查是否有已签到的文本
                if '[已签到]' in page_source or '已签到' in page_source:
                    logger.info('确认用户已经签到')
                    return "already_signed"
                # 如果既没有签到按钮，也没有已签到文本，可能是页面加载问题
                logger.error('既未找到签到按钮，也未找到已签到标识')
                return None

            logger.info('找到签到按钮')

            # 检查按钮文本
            button_text = signin_button.text or ""
            logger.info(f'签到按钮文本: {button_text}')

            if "已签到" in button_text or "Showed Up" in button_text:
                logger.info('按钮显示已签到状态')
                return "already_signed"

            # 点击签到按钮
            signin_button.click()
            logger.info('点击签到按钮')

            # 等待弹窗出现
            time.sleep(3)

            return True

        except Exception as e:
            entry.fail_with_prefix(f'点击签到按钮失败: {e}')
            return None

    def _get_imagehash_from_captcha(self, page, entry) -> str | None:
        """从验证码弹窗中获取imagehash"""
        try:
            # 查找验证码图片
            # 方法1: 通过ID查找
            captcha_img = page.ele('#showupimg', timeout=5)
            if captcha_img:
                src = captcha_img.attr('src')
                logger.info(f"通过ID找到验证码图片: {src}")
            else:
                # 方法2: 通过src属性查找
                captcha_img = page.ele('tag:img@src*=imagehash', timeout=5)
                if captcha_img:
                    src = captcha_img.attr('src')
                    logger.info(f"通过src属性找到验证码图片: {src}")
                else:
                    logger.warning("未找到验证码图片")
                    # 保存页面源码用于调试
                    import datetime as dt
                    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                    try:
                        debug_path = f"hdsky_debug_{ts}.html"
                        with open(debug_path, 'w', encoding='utf-8') as f:
                            f.write(page.html)
                        logger.info(f"调试页面源码已保存到: {debug_path}")
                    except:
                        pass
                    return None

            # 提取验证码hash
            if src:
                import re
                match = re.search(r'imagehash=([a-f0-9]+)', src)
                if match:
                    hash_value = match.group(1)
                    logger.info(f"提取到验证码hash: {hash_value}")
                    return hash_value
                else:
                    logger.warning(f"无法从URL中提取imagehash: {src}")
                    return None
            else:
                logger.warning("验证码图片没有src属性")
                return None

        except Exception as e:
            entry.fail_with_prefix(f'获取imagehash失败: {e}')
            return None

    def _download_captcha_image(self, hash_value: str, entry) -> str | None:
        """下载验证码图片并保存到本地"""
        try:
            import requests
            import datetime as dt

            # 获取cookie
            cookie_str = entry.get('cookie', '')
            cookies = {}
            if cookie_str:
                for item in cookie_str.split(';'):
                    item = item.strip()
                    if '=' in item:
                        name, value = item.split('=', 1)
                        cookies[name.strip()] = value.strip()

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://hdsky.me/",
            }

            # 下载验证码图片
            img_url = f"https://hdsky.me/image.php?action=regimage&imagehash={hash_value}"
            logger.info(f"下载验证码图片: {img_url}")

            response = requests.get(img_url, cookies=cookies, headers=headers, timeout=30)
            if response.status_code == 200:
                # 保存图片
                ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                img_path = f"hdsky_captcha_{ts}_{hash_value}.png"

                with open(img_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"验证码图片已保存到: {img_path}")

                # 验证图片是否有效
                try:
                    from PIL import Image
                    img = Image.open(img_path)
                    logger.info(f"验证码图片尺寸: {img.size}")
                    return img_path
                except Exception as e:
                    logger.warning(f"图片验证失败: {e}")
                    return img_path  # 即使验证失败也返回路径
            else:
                logger.error(f"下载验证码图片失败: {response.status_code}")
                return None

        except Exception as e:
            entry.fail_with_prefix(f"下载验证码图片异常: {e}")
            return None

    def _recognize_captcha(self, image_path: str, entry, config: dict) -> str | None:
        """识别验证码（直接使用百度OCR工具）"""
        try:
            # 检查是否配置了百度OCR
            if 'aipocr' not in config:
                logger.warning("未配置百度OCR，无法自动识别验证码")
                return None

            from ..utils import baidu_ocr
            from PIL import Image

            # 打开验证码图片并直接使用百度OCR
            img = Image.open(image_path)
            logger.info(f"使用百度OCR识别验证码，图片尺寸: {img.size}")

            code, _ = baidu_ocr.get_ocr_code(img, entry, config)

            if code:
                logger.info(f"验证码识别成功: {code}")
                return code
            else:
                logger.warning("验证码识别失败")
                return None

        except Exception as e:
            logger.error(f"验证码识别异常: {e}")
            return None

    def _cleanup_captcha_image(self, image_path: str):
        """清理验证码图片文件"""
        try:
            from ..utils.baidu_ocr import cleanup_captcha_image
            cleanup_captcha_image(image_path, "hdsky")
        except Exception as e:
            logger.warning(f"清理验证码图片失败: {e}")

    def _submit_captcha_form(self, page, imagehash: str, captcha_text: str, entry) -> bool:
        """提交验证码表单（使用正确的选择器和AJAX提交）"""
        try:
            # 填写验证码（使用正确的选择器）
            captcha_input = page.ele('#imagestring', timeout=5)
            if not captcha_input:
                # 备用选择器
                captcha_input = page.ele('input[name="imagestring"]', timeout=5)

            if captcha_input:
                captcha_input.clear()
                captcha_input.input(captcha_text)
                logger.info(f"填写验证码: {captcha_text}")
            else:
                logger.warning("未找到验证码输入框")
                return False

            # 点击提交按钮（使用正确的选择器）
            submit_button = page.ele('#showupbutton', timeout=5)
            if not submit_button:
                # 备用选择器
                submit_button = page.ele('input[type="button"][value="Let\'s Go"]', timeout=5)

            if submit_button:
                submit_button.click()
                logger.info("点击验证码提交按钮")
                time.sleep(5)  # 等待AJAX提交结果

                # 检查提交结果（可能需要检查页面变化或AJAX响应）
                page_source = page.html

                # 检查多种成功标识
                success_indicators = [
                    '{"success":true',
                    '签到成功',
                    'showup success',
                    'already signed',
                    '已签到'
                ]

                for indicator in success_indicators:
                    if indicator in page_source:
                        logger.info(f"验证码提交成功，检测到标识: {indicator}")
                        return True

                # 检查是否有错误信息
                error_indicators = [
                    '验证码错误',
                    'captcha error',
                    'wrong captcha',
                    '{"success":false'
                ]

                for error in error_indicators:
                    if error in page_source:
                        logger.warning(f"验证码提交失败，检测到错误: {error}")
                        return False

                logger.warning("验证码提交结果未知，页面内容未包含明确的成功或失败标识")
                # 保存页面源码用于调试
                import datetime as dt
                ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                try:
                    debug_path = f"hdsky_submit_result_{ts}.html"
                    with open(debug_path, 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    logger.info(f"提交结果页面源码已保存到: {debug_path}")
                except:
                    pass

                return False
            else:
                logger.warning("未找到提交按钮")
                return False

        except Exception as e:
            entry.fail_with_prefix(f"提交验证码失败: {e}")
            return False

    def _extract_imagehash_from_page(self, page, entry) -> str | None:
        """从页面中提取imagehash值"""
        try:
            # 方法1: 从隐藏输入框中获取
            imagehash_input = page.ele('input[name="imagehash"]', timeout=5)
            if imagehash_input:
                imagehash = imagehash_input.attr('value')
                if imagehash:
                    entry.info(f"从input元素获取imagehash: {imagehash}")
                    return imagehash

            # 方法2: 从验证码图片URL中提取
            captcha_img = page.ele('tag:img@src*=imagehash', timeout=5)
            if captcha_img:
                src = captcha_img.attr('src')
                if src and 'imagehash=' in src:
                    import re
                    match = re.search(r'imagehash=([^&]+)', src)
                    if match:
                        imagehash = match.group(1)
                        entry.info(f"从图片URL获取imagehash: {imagehash}")
                        return imagehash

            # 方法3: 从页面源码中搜索
            page_source = page.html
            import re
            patterns = [
                r'name="imagehash"\s+value="([^"]+)"',
                r'imagehash["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'imagehash=([a-f0-9]+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    imagehash = match.group(1)
                    entry.info(f"从页面源码获取imagehash: {imagehash}")
                    return imagehash

            entry.warning("所有方法都未能获取到imagehash")
            return None

        except Exception as e:
            entry.fail_with_prefix(f'提取imagehash失败: {e}')
            return None

    def _get_captcha_image_data(self, page, entry) -> bytes | None:
        """获取验证码图片数据"""
        try:
            captcha_img = None
            src = None

            # 方法1: 通过ID查找
            captcha_img = page.ele('#showupimg', timeout=10)
            if captcha_img:
                src = captcha_img.attr('src')
                logger.info(f"通过ID找到验证码图片: {src}")

            # 方法2: 通过src属性查找
            if not captcha_img:
                captcha_img = page.ele('tag:img@src*=imagehash', timeout=5)
                if captcha_img:
                    src = captcha_img.attr('src')
                    logger.info(f"通过src属性找到验证码图片: {src}")

            if not captcha_img or not src:
                logger.warning("未找到验证码图片")
                return None

        except Exception as e:
            logger.error(f"获取验证码图片数据失败: {e}")
            return None

    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        net_utils.dict_merge(selector, {
            'user_id': r'userdetails\.php\?id=(\d+)',  # 从用户链接中提取用户ID的正则表达式
            'detail_sources': {
                'default': {
                    'link': None,
                    'elements': {
                        'bar': '#info_block td.bottom span.medium',
                        'table': None
                    }
                }
            },
            'details': {
                'join_date': None,
                'hr': None
            }
        })
        return selector
