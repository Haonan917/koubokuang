import argparse
import hashlib
import logging
import os
import uuid
from random import Random
from typing import Union

import config

from .crawler_util import *
from .time_util import *


def init_loging_config():
    """
    init loging config
    Returns:

    """
    level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _logger = logging.getLogger("MediaCrawlerDownloadBackend")
    _logger.setLevel(level)

    if config.ENABLE_LOG_FILE:
        # create logs dir
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        log_dir = os.path.join(project_root, "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = os.path.join(log_dir, f"{get_current_date()}.log")
        file_handler = logging.FileHandler(filename=log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        _logger.addHandler(file_handler)

    return _logger


logger = init_loging_config()


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def get_random_str(random_len: int = 12) -> str:
    """
    获取随机字符串
    :param random_len:
    :return:
    """
    random_str = ""
    chars = "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789"
    length = len(chars) - 1
    _random = Random()
    for i in range(random_len):
        random_str += chars[_random.randint(0, length)]
    return random_str


def random_delay_time(min_time: int = 1, max_time: int = 3) -> int:
    """
    获取随机延迟时间
    :param min_time:
    :param max_time:
    :return:
    """
    return random.randint(min_time, max_time)


def get_md5(bytes_content: Union[str, bytes]) -> str:
    """
    获取MD5值
    :param bytes_content:
    :return:
    """
    if type(bytes_content) == str:
        bytes_content = bytes_content.encode()
    md5obj = hashlib.md5()
    md5obj.update(bytes_content)
    hash_value = md5obj.hexdigest()
    return hash_value


def get_uuid_md5_value(default_len: int = 16) -> str:
    """
    根据UUID以及MD5生成一个唯一的识别码 16, 32位
    :param default_len: 默认长度
    :return:
    """
    if default_len == 16:
        return get_md5(uuid.uuid1().hex)[8:24]
    return get_md5(uuid.uuid1().hex)
