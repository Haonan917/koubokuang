# -*- coding: utf-8 -*-
import copy
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Union

import httpx
from httpx import Response
from tenacity import retry, stop_after_attempt, wait_fixed

from abs.abs_api_client import AbstractApiClient
from constant.douyin import DOUYIN_API_URL, DOUYIN_FIXED_USER_AGENT
from models.content_detail import Content, ContentDetailResponse
from models.creator import CreatorContentListResponse, CreatorQueryResponse
from pkg.media_platform_api.douyin.extractor import DouyinExtractor
from pkg.media_platform_api.douyin.help import (CommonVerfiyParams,
                                                DataFetchError,
                                                get_common_verify_params)
from pkg.rpc.sign_srv_client import DouyinSignRequest, SignServerClient
from pkg.tools import utils


class DouYinApiClient(AbstractApiClient):
    def __init__(
        self,
        timeout: int = 10,
        user_agent: str = None,
        cookies: str = "",
    ):
        """
        dy client constructor

        Args:
            timeout: 请求超时时间配置
            user_agent: 自定义的User-Agent
        """
        self.timeout = timeout
        self._user_agent = user_agent or DOUYIN_FIXED_USER_AGENT
        self._sign_client = SignServerClient()
        self._cookies = cookies
        self.common_verfiy_params: Optional[CommonVerfiyParams] = None
        self._extractor = DouyinExtractor()

    async def async_initialize(self):
        """
        async initialize

        Returns:

        """
        self.common_verfiy_params = await get_common_verify_params(self._user_agent)

    @property
    def _headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "Cookie": self._cookies,
            "origin": "https://www.douyin.com",
            "referer": "https://www.douyin.com/",
            "user-agent": self._user_agent,
        }

    @property
    def _common_params(self):
        return {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "publish_video_strategy_type": 2,
            "update_version_code": 170400,
            "pc_client_type": 1,
            "version_code": 170400,
            "version_name": "17.4.0",
            "cookie_enabled": "true",
            "screen_width": 2560,
            "screen_height": 1440,
            "browser_language": "zh-CN",
            "browser_platform": "MacIntel",
            "browser_name": "Chrome",
            "browser_version": "127.0.0.0",
            "browser_online": "true",
            "engine_name": "Blink",
            "engine_version": "127.0.0.0",
            "os_name": "Mac+OS",
            "os_version": "10.15.7",
            "cpu_core_num": 8,
            "device_memory": 8,
            "platform": "PC",
            "downlink": 4.45,
            "effective_type": "4g",
            "round_trip_time": 100,
        }

    @property
    def _verify_params(self):
        return {
            "webid": self.common_verfiy_params.webid,
            "msToken": self.common_verfiy_params.ms_token,
        }

    async def _pre_url_params(self, uri: str, url_params: Dict) -> Dict:
        """
        预处理URL参数，获取a_bogus参数

        Args:
            uri:
            url_params:

        Returns:

        """
        final_url_params = copy.copy(url_params)
        final_url_params.update(self._common_params)
        final_url_params.update(self._verify_params)
        query_params = urllib.parse.urlencode(final_url_params)
        sign_req: DouyinSignRequest = DouyinSignRequest(
            uri=uri,
            query_params=query_params,
            user_agent=self._user_agent,
            cookies=self._cookies,
        )
        dy_sign_resp = await self._sign_client.douyin_sign(sign_req=sign_req)
        final_url_params["a_bogus"] = dy_sign_resp.data.a_bogus
        return final_url_params

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
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

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if need_return_ori_response:
            return response

        try:
            if response.text == "" or response.text == "blocked":
                utils.logger.error(
                    f"request params incrr, response.text: {response.text}"
                )
                raise Exception("account blocked")
            return response.json()
        except Exception as e:
            raise DataFetchError(f"{e}, {response.text}")

    async def get(self, uri: str, params: Optional[Dict] = None, **kwargs):
        """
        GET请求

        Args:
            uri: 请求的URI
            params: 请求参数

        Returns:

        """

        params = await self._pre_url_params(uri, params)
        return await self.request(
            method="GET", url=f"{DOUYIN_API_URL}{uri}", params=params, **kwargs
        )

    async def pong(self) -> bool:
        """
        测试接口是否可用

        Returns:
            bool: 是否可用

        """
        res = await self.query_user_self_info()
        if res and res.get("user_uid") and res.get("id"):
            # 这个res中会返回当前登录用户的相关信息，其中包含了：user_agent,则更新当前的user_agent
            if res.get("user_agent"):
                self._user_agent = res.get("user_agent")
            return True
        utils.logger.error(
            f"[DouYinApiClient.pong] pong failed, query user self response: {res}"
        )
        return False

    async def query_user_self_info(self) -> Dict:
        """
        查询用户自己的信息

        Returns:
            Dict: 用户信息
        """
        uri = "/aweme/v1/web/query/user/"
        params = {}
        params.update(self._common_params)
        params.update(self._verify_params)
        return await self.get(uri, params)

    async def get_video_by_id(self, aweme_id: str) -> Any:
        """
        DouYin Video Detail API

        Args:
            aweme_id: 视频ID

        Returns:

        """
        params = {"aweme_id": aweme_id}
        headers = copy.copy(self._headers)
        if "Origin" in headers:
            del headers["Origin"]
        res = await self.get("/aweme/v1/web/aweme/detail/", params, headers=headers)
        return res.get("aweme_detail", {})

    async def get_creator_info(self, user_id: str) -> Optional[CreatorQueryResponse]:
        """
        获取指定sec_user_id用户信息

        Args:
            user_id:

        Returns:

        """
        uri = "/aweme/v1/web/user/profile/other/"
        params = {
            "sec_user_id": user_id,
            "publish_video_strategy_type": 2,
            "personal_center_strategy": 1,
        }
        response = await self.get(uri, params)
        return self._extractor.extract_creator_info(response)

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
        uri = "/aweme/v1/web/aweme/post/"
        params = {
            "sec_user_id": creator_id,
            "count": 18,
            "max_cursor": cursor,
            "locate_query": "false",
            "publish_video_strategy_type": 2,
            "verifyFp": self.common_verfiy_params.verify_fp,
            "fp": self.common_verfiy_params.verify_fp,
        }
        response = await self.get(uri, params)
        return self._extractor.extract_contents(response)

    async def resolve_short_url(self, short_url: str) -> str:
        """
        解析抖音短链接，获取重定向后的真实URL

        Args:
            short_url: 短链接，如 https://v.douyin.com/iF12345ABC/

        Returns:
            重定向后的完整URL
        """
        async with httpx.AsyncClient(follow_redirects=False) as client:
            try:
                utils.logger.info(
                    f"[DouYinApiClient.resolve_short_url] Resolving short URL: {short_url}"
                )
                response = await client.get(short_url, timeout=10)

                # 短链接通常返回302重定向
                if response.status_code in [301, 302, 303, 307, 308]:
                    redirect_url = response.headers.get("Location", "")
                    utils.logger.info(
                        f"[DouYinApiClient.resolve_short_url] Resolved to: {redirect_url}"
                    )
                    return redirect_url
                else:
                    utils.logger.warning(
                        f"[DouYinApiClient.resolve_short_url] Unexpected status code: {response.status_code}"
                    )
                    return ""
            except Exception as e:
                utils.logger.error(
                    f"[DouYinApiClient.resolve_short_url] Failed to resolve short URL: {e}"
                )
                return ""

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
        uri = "/aweme/v1/web/aweme/detail/"
        params = {"aweme_id": content_id}
        response = await self.get(uri, params)
        return self._extractor.extract_content_detail(response)
