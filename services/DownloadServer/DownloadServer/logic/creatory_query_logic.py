# -*- coding: utf-8 -*-
import re
from typing import Dict, Optional, Tuple

import constant
from logic.base_logic import BaseLogic
from models.base_model import PlatformEnum
from models.creator import (
    CreatorContentListRequest,
    CreatorContentListResponse,
    CreatorQueryRequest,
    CreatorQueryResponse,
)
from pkg.tools import utils


class CreatorQueryLogic(BaseLogic):

    def __init__(self, platform: PlatformEnum, cookies: str = ""):
        """
        creatory query logic constructor

        Args:
            platform_name:
        """
        super().__init__(platform, cookies)

    async def async_initialize(self, **kwargs):
        """
        async initialize
        Returns:

        """
        await super().async_initialize(**kwargs)

    def extract_creator_id(self, url: str) -> Tuple[bool, str, str]:
        """
        extract creator id from url

        Args:
            url: media platform user url

        Returns:
            tuple:
                bool: is_valid
                str: extract_msg
                str: creator_id
        """
        url = url.split("?")[0] if "?" in url else url
        if self.platform == PlatformEnum.DOUYIN:
            pattern = r"/user/(.*)"
        elif self.platform == PlatformEnum.XHS:
            pattern = r"/user/profile/(.*)"
        elif self.platform == PlatformEnum.BILIBILI:
            pattern = r"/space.bilibili.com/(.*)"
        elif self.platform == PlatformEnum.KUAISHOU:
            pattern = r"/profile/(.*)"
        else:
            return False, "无效的自媒体平台", ""

        match = re.findall(pattern, url)
        if match:
            return True, "", match[0]
        else:
            return False, "无效的创作者URL", ""

    async def query_creator_info(
        self, req: CreatorQueryRequest
    ) -> Optional[CreatorQueryResponse]:
        """
        查询创作者主页信息

        Args:
            req (CreatorQueryRequest): 请求

        Returns:
            CreatorQueryResponse: 创作者主页信息
        """
        return await self.api_client.get_creator_info(req.creator_id)

    async def query_creator_contents(
        self, req: CreatorContentListRequest
    ) -> CreatorContentListResponse:
        """
        查询创作者内容

        Args:
            req (CreatorContentListRequest): 请求

        Returns:
            CreatorContentListResponse: 创作者内容列表
        """
        return await self.api_client.get_creator_contents(req.creator_id, req.cursor)
