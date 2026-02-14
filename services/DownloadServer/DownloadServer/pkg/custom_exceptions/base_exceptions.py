# -*- coding: utf-8 -*-


class MediaCrawlerBaseException(Exception):
    """基础异常类，所有也选相关的异常都应该继承这个类"""

    def __init__(self, message="基础错误", *args):
        super().__init__(message, *args)


class ReturnValueError(MediaCrawlerBaseException):
    """返回值错误"""

    def __init__(self, message="返回值错误", *args):
        super().__init__(message, *args)


class BusinessLogicError(MediaCrawlerBaseException):
    """业务逻辑错误"""

    def __init__(self, message="业务逻辑处理错误", *args):
        super().__init__(message, *args)
