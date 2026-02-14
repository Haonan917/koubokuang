# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Optional

from models.content_detail import ContentDetailResponse
from models.creator import CreatorContentListResponse, CreatorQueryResponse


class AbstractApiClient(ABC):

    async def async_initialize(self):
        """
        Initialize the API client

        Returns:

        """
        raise NotImplementedError

    @abstractmethod
    async def pong(self) -> bool:
        """
        Check if the API is alive

        Returns:
            bool: 是否存活
        """
        raise NotImplementedError

    @abstractmethod
    async def get_creator_info(self, creator_id: str) -> Optional[CreatorQueryResponse]:
        """
        Get creator info

        Args:
            creator_id (str): 创作者ID

        Returns:
            CreatorQueryResponse: 创作者信息
        """
        raise NotImplementedError

    @abstractmethod
    async def get_creator_contents(
        self, creator_id: str, cursor: str
    ) -> CreatorContentListResponse:
        """
        获取创作者内容

        Args:
            creator_id (str): 创作者ID
            cursor (str): 分页游标

        Returns:
            CreatorContentListResponse: 创作者内容列表
        """
        raise NotImplementedError

    @abstractmethod
    async def get_content_detail(
        self, content_id: str, ori_content_url: str = ""
    ) -> Optional[ContentDetailResponse]:
        """
        获取内容详情

        Args:
            content_id (str): 内容ID
            ori_content_url (str): 原始内容URL
        Returns:
            ContentDetailResponse: 内容详情
        """
        raise NotImplementedError
