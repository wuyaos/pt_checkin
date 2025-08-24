from __future__ import annotations

import re
from typing import Final
from urllib.parse import urljoin

from requests import Response

from ..base.request import NetworkState, check_network_state
from ..base.sign_in import SignState, check_final_state
from ..base.work import Work
from ..core.entry import SignInEntry
from ..schema.nexusphp import NexusPHP
from ..utils import net_utils


class MainClass(NexusPHP):
    URL: Final = "https://pt.btschool.club/"
    USER_CLASSES: Final = {
        "downloaded": [1099511627776, 10995116277760],
        "share_ratio": [3.05, 4.55],
        "points": [600000, 1000000],
        "days": [280, 700],
    }

    @classmethod
    def sign_in_build_entry(cls, entry: SignInEntry, config: dict) -> None:
        """构建签到条目，启用浏览器模拟以绕过Cloudflare"""
        super().sign_in_build_entry(entry, config)
        # 添加成功标识配置
        entry["success_indicators"] = {
            "logo": 'class="logo">BTSCHOOL</div>',
            "slogan": "汇聚每一个人的影响力",
            "keywords": ["种子", "torrent", "用户", "做种积分"],
        }

    def sign_in_build_workflow(self, entry: SignInEntry, config: dict) -> list[Work]:
        return [
            Work(
                url="/index.php?action=addbonus",
                method=self.sign_in_by_location,
                succeed_regex=["欢迎回来"],
                assert_state=(check_final_state, SignState.SUCCEED),
                is_base_content=True,
            ),
        ]

    @property
    def details_selector(self) -> dict:
        selector = super().details_selector
        net_utils.dict_merge(
            selector,
            {
                "details": {
                    "points": {
                        "regex": r"做种积分:.*?([\d.,]+)",
                    }
                }
            },
        )
        return selector

    def sign_in_by_location(
        self, entry: SignInEntry, config: dict, work: Work, last_content: str
    ) -> Response | None:
        response = self.request(entry, "get", work.url, config)
        reload__net_state = check_network_state(entry, work.url, response)
        if reload__net_state != NetworkState.SUCCEED:
            return None
        content = net_utils.decode(response)
        location_search = re.search("(?<=window\\.location=).*?(?=;)", content)
        if not location_search:
            return response
        location_url = re.sub('["+ ]', "", location_search.group(0))
        work.url = urljoin(MainClass.URL, location_url)
        return self.sign_in_by_get(entry, config, work)
