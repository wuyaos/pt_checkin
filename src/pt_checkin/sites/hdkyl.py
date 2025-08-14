from typing import Final

# Removed reseed functionality
from ..schema.nexusphp import Attendance
from ..utils.value_handler import size


class MainClass(Attendance):
    URL: Final = 'https://www.hdkyl.in/'
    USER_CLASSES: Final = {
        'downloaded': [size(750, 'GiB'), size(10, 'TiB')],
        'share_ratio': [6, 10],
        'points': [400000, 1000000],
        'days': [280, 700]
    }
