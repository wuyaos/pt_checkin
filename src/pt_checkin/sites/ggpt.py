from typing import Final

from ..core.entry import SignInEntry
from ..schema.nexusphp import AttendanceHR
from ..utils import net_utils
from ..utils.value_handler import size


class MainClass(AttendanceHR):
    URL: Final = "https://www.gamegamept.com/"
    USER_CLASSES: Final = {
        "downloaded": [size(500, "GiB"), size(2, "TiB")],
        "share_ratio": [2.0, 3.0],
        "points": [200000, 500000],
        "days": [180, 365],
    }

    def get_messages(self, entry: SignInEntry, config: dict) -> None:
        """获取站内消息"""
        self.get_nexusphp_messages(entry, config)

    @property
    def details_selector(self) -> dict:
        """用户详情选择器配置"""
        selector = super().details_selector
        net_utils.dict_merge(
            selector,
            {
                "detail_sources": {
                    "default": {
                        "elements": {
                            "bar": "#info_block",
                            "table": "#outer table.main:last-child",
                        }
                    }
                },
                "details": {"points": {"regex": r"G值.*?([0-9,]+\.?[0-9]*)"}},
            },
        )
        return selector
