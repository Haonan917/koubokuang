# -*- coding: utf-8 -*-

from httpx import RequestError


class DataFetchError(RequestError):
    """Data fetch error when fetching from Kuaishou API"""
    pass


class IPBlockError(RequestError):
    """IP block error when request frequency is too high"""
    pass