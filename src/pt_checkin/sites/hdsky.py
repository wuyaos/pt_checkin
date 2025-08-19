from __future__ import annotations

from typing import Final

from ..core.entry import SignInEntry
from ..base.work import Work
from ..schema.nexusphp import NexusPHP
from ..utils.net_utils import get_module_name


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

    def sign_in_build_workflow(self, entry: SignInEntry,
                              config: dict) -> list[Work]:
        """构建签到工作流 - 使用策略模式处理验证码"""
        from ..utils.hdsky_strategy import HDSkyCaptchaStrategy

        # HDSky 站点特殊处理：强制使用验证码策略
        entry['has_captcha'] = True
        entry['request_method'] = 'browser'

        # 使用 HDSky 专用的验证码策略
        strategy = HDSkyCaptchaStrategy()
        return strategy.build_workflow(entry, config)

    @property
    def details_selector(self) -> dict:
        """使用 SelectorBuilder 构建选择器"""
        from ..base.selector_builder import SelectorBuilderFactory

        # 创建标准选择器构建器
        base_selector = super().details_selector
        builder = SelectorBuilderFactory.create_standard_builder(base_selector)

        # 配置 HDSky 特定的选择器
        hdsky_config = {
            'user_id': None,
            'detail_sources': {
                'default': {
                    'link': None,
                    'elements': {
                        'bar': ('#info_block > tbody > tr > td > table > '
                               'tbody > tr > td:nth-child(1) > span'),
                        'table': None
                    }
                }
            },
            'details': {
                'join_date': None,
                'hr': None
            }
        }

        return builder.with_config(hdsky_config).build()
