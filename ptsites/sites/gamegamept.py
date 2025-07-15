from typing import Final

from ..schema.nexusphp import Attendance


class MainClass(Attendance):
    URL: Final = 'https://www.gamegamept.com/'
    USER_CLASSES: Final = {
        'downloaded': [4398046511104, 10995116277760],
        'share_ratio': [3.5, 5],
        'days': [210, 364]
    }