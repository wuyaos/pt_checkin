import sys

from loguru import logger


def setup_logger(data_path):
    logger.remove()
    level = 'INFO'
    log_path = data_path / 'pt_checkin.log'
    format_ = (
        '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
        '<level>{level:<8}</level> | '
        '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
        '<level>{message}</level>'
    )
    logger.add(sys.stdout, level=level, format=format_)
    logger.add(log_path, level=level, format=format_,
               rotation="10 MB", encoding='utf-8')
