# -*- coding: utf-8 -*-
from abs.abs_api_client import AbstractApiClient
from models.base_model import PlatformEnum

from .bilibili.client import BilibiliApiClient
from .douyin.client import DouYinApiClient
from .xhs.client import XhsApiClient
from .kuaishou.client import KuaishouApiClient


async def create_media_platform_client(
    platform: PlatformEnum, cookies: str, **kwargs
) -> AbstractApiClient:
    """
    create media platform api client

    Args:
        platform: platform enum
        cookies: cookies

    Returns:
        AbstractApiClient: api client
    """
    if platform == PlatformEnum.DOUYIN:
        instance = DouYinApiClient(cookies=cookies, **kwargs)
    elif platform == PlatformEnum.XHS:
        instance = XhsApiClient(cookies=cookies, **kwargs)
    elif platform == PlatformEnum.BILIBILI:
        instance = BilibiliApiClient(cookies=cookies, **kwargs)
    elif platform == PlatformEnum.KUAISHOU:
        instance = KuaishouApiClient(cookies=cookies, **kwargs)
    else:
        raise ValueError(f"platform {platform} not supported")
    await instance.async_initialize()
    return instance
