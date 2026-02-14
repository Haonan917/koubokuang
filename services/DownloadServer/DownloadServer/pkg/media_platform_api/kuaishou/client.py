# -*- coding: utf-8 -*-
import json
from typing import Dict, Optional, Union

import httpx
from httpx import Response

from abs.abs_api_client import AbstractApiClient
from constant.kuaishou import KUAISHOU_API
from models.content_detail import ContentDetailResponse
from models.creator import CreatorContentListResponse, CreatorQueryResponse
from pkg.media_platform_api.kuaishou.extractor import KuaishouExtractor
from pkg.media_platform_api.kuaishou.help import DataFetchError
from pkg.media_platform_api.kuaishou.graphql import KuaishouGraphQL
from pkg.tools import utils


class KuaishouApiClient(AbstractApiClient):
    def __init__(
        self,
        timeout: int = 10,
        user_agent: str = None,
        cookies: str = "",
    ):
        """
        Kuaishou client constructor

        Args:
            timeout: 请求超时时间配置
            user_agent: 自定义的User-Agent
            cookies: cookies字符串
        """
        self.timeout = timeout
        self._user_agent = (
            user_agent
            or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        self._cookies = cookies
        self._extractor = KuaishouExtractor()
        self._graphql = KuaishouGraphQL()

    async def async_initialize(self):
        """
        async initialize
        """
        pass

    @property
    def _headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Cookie": self._cookies,
            "origin": "https://www.kuaishou.com",
            "referer": "https://www.kuaishou.com/",
            "user-agent": self._user_agent,
        }

    async def request(self, method, url, **kwargs) -> Union[Response, Dict]:
        """
        封装httpx的公共请求方法，对请求响应做一些处理

        Args:
            method: 请求方法
            url: 请求的URL
            **kwargs: 其他请求参数，例如请求头、请求体等

        Returns:

        """
        need_return_ori_response = kwargs.get("return_response", False)
        if "return_response" in kwargs:
            del kwargs["return_response"]

        if "headers" not in kwargs:
            kwargs["headers"] = self._headers

        # 简单重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method, url, timeout=self.timeout, **kwargs
                    )

                if need_return_ori_response:
                    return response

                data = response.json()
                if data.get("errors"):
                    raise DataFetchError(f"API returned errors: {data.get('errors')}")
                return data.get("data", {})

            except Exception as e:
                if attempt == max_retries - 1:  # 最后一次重试
                    raise DataFetchError(f"Failed after {max_retries} attempts: {e}")
                utils.logger.warning(
                    f"Request failed (attempt {attempt + 1}): {e}, retrying..."
                )
                continue

    async def post(self, uri: str, data: dict, **kwargs) -> Dict:
        """
        POST请求

        Args:
            uri: 请求的URI
            data: 请求体参数

        Returns:

        """
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return await self.request(
            method="POST", url=f"{KUAISHOU_API}{uri}", data=json_str, **kwargs
        )

    async def pong(self) -> bool:
        """
        测试接口是否可用

        Returns:
            bool: 是否可用

        """
        try:
            post_data = {
                "operationName": "visionProfileUserList",
                "variables": {"ftype": 1},
                "query": self._graphql.get("vision_profile_user_list"),
            }
            response = await self.post("", post_data)
            vision_profile_user_list = response.get("visionProfileUserList")
            return (
                vision_profile_user_list and vision_profile_user_list.get("result") == 1
            )
        except Exception as e:
            utils.logger.error(f"[KuaishouApiClient.pong] pong failed: {e}")
            return False

    async def get_creator_info(self, user_id: str) -> Optional[CreatorQueryResponse]:
        """
        获取创作者信息

        Args:
            user_id: 用户ID

        Returns:
            CreatorQueryResponse: 创作者信息
        """
        post_data = {
            "operationName": "visionProfile",
            "variables": {"userId": user_id},
            "query": self._graphql.get("vision_profile"),
        }
        response = await self.post("", post_data)
        return self._extractor.extract_creator_info(response)

    async def get_creator_contents(
        self, creator_id: str, cursor: str = ""
    ) -> CreatorContentListResponse:
        """
        获取创作者内容列表

        Args:
            creator_id: 创作者ID
            cursor: 分页游标

        Returns:
            CreatorContentListResponse: 创作者内容列表
        """
        post_data = {
            "operationName": "visionProfilePhotoList",
            "variables": {"pcursor": cursor, "userId": creator_id, "page": "profile"},
            "query": self._graphql.get("vision_profile_photo_list"),
        }
        response = await self.post("", post_data)
        return self._extractor.extract_contents(response)

    async def get_content_detail(
        self, content_id: str, ori_content_url: str = ""
    ) -> Optional[ContentDetailResponse]:
        """
        获取内容详情

        Args:
            content_id: 内容ID
            ori_content_url: 原始内容URL (保留接口兼容性，暂未使用)

        Returns:
            ContentDetailResponse: 内容详情
        """
        # ori_content_url 参数保留为了接口兼容性，快手API不需要此参数
        post_data = {
            "operationName": "visionVideoDetail",
            "variables": {"photoId": content_id, "page": "search"},
            "query": self._graphql.get("video_detail"),
        }
        response = await self.post("", post_data)
        return self._extractor.extract_content_detail(response)
