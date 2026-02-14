# -*- coding: utf-8 -*-
import asyncio
import json
import random
import re
from typing import Callable, Dict, List, Optional, Union
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from httpx import Response
from tenacity import retry, stop_after_attempt, wait_random

from abs.abs_api_client import AbstractApiClient
from constant.xiaohongshu import XHS_API_URL, XHS_INDEX_URL
from models.content_detail import ContentDetailResponse
from models.creator import CreatorContentListResponse, CreatorQueryResponse
from pkg.media_platform_api.xhs.extractor import XhsExtractor
from pkg.rpc.sign_srv_client import SignServerClient, XhsSignRequest
from pkg.tools import utils

from .exception import (
    AccessFrequencyError,
    DataFetchError,
    ErrorEnum,
    IPBlockError,
    SignError,
)
from .field import SearchNoteType, SearchSortType
from .help import get_search_id


class XhsApiClient(AbstractApiClient):
    def __init__(
        self,
        timeout: int = 10,
        user_agent: str = None,
        cookies: str = "",
    ):
        """
        xhs client constructor
        Args:
            timeout: 请求超时时间配置
            user_agent: 自定义的User-Agent
            cookies: 自定义的cookies
        """
        self.timeout = timeout
        self._user_agent = user_agent or utils.get_user_agent()
        self._sign_client = SignServerClient()
        self._cookies = cookies
        self._extractor = XhsExtractor()

    async def async_initialize(self):
        """
        异步初始化
        Returns:

        """
        pass

    @property
    def headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Cookie": self._cookies,
            "origin": "https://www.xiaohongshu.com",
            "referer": "https://www.xiaohongshu.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

    async def _pre_headers(self, uri: str, data=None) -> Dict:
        """
        请求头参数签名
        Args:
            uri:
            data:

        Returns:

        """
        sign_req: XhsSignRequest = XhsSignRequest(
            uri=uri,
            data=data,
            cookies=self._cookies,
        )
        xhs_sign_resp = await self._sign_client.xiaohongshu_sign(sign_req)
        headers = {
            "X-S": xhs_sign_resp.data.x_s,
            "X-T": xhs_sign_resp.data.x_t,
            "x-S-Common": xhs_sign_resp.data.x_s_common,
            "X-B3-Traceid": xhs_sign_resp.data.x_b3_traceid,
        }
        headers.update(self.headers)
        return headers

    @retry(stop=stop_after_attempt(5), wait=wait_random(2, 10))
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

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if need_return_ori_response:
            return response

        try:
            if response.status_code == 200:
                data = response.json()
            else:
                raise DataFetchError(response.text)
        except json.decoder.JSONDecodeError:
            return response

        if response.status_code == 471 or response.status_code == 461:
            # someday someone maybe will bypass captcha
            verify_type = response.headers["Verifytype"]
            verify_uuid = response.headers["Verifyuuid"]
            raise Exception(
                f"出现验证码，请求失败，Verifytype: {verify_type}，Verifyuuid: {verify_uuid}, Response: {response}"
            )
        elif data.get("success"):
            return data.get("data", data.get("success"))
        elif data.get("code") == ErrorEnum.IP_BLOCK.value.code:
            raise IPBlockError(ErrorEnum.IP_BLOCK.value.msg)
        elif data.get("code") == ErrorEnum.SIGN_FAULT.value.code:
            raise SignError(ErrorEnum.SIGN_FAULT.value.msg)
        elif data.get("code") == ErrorEnum.ACCEESS_FREQUENCY_ERROR.value.code:
            # 访问频次异常, 再随机延时一下
            utils.logger.error(
                f"[XiaoHongShuClient.request] 访问频次异常，尝试随机延时一下..."
            )
            await asyncio.sleep(utils.random_delay_time(2, 10))
            raise AccessFrequencyError(ErrorEnum.ACCEESS_FREQUENCY_ERROR.value.msg)
        else:
            raise DataFetchError(data)

    async def get(self, uri: str, params=None, **kwargs) -> Union[Response, Dict]:
        """
        GET请求，对请求头签名
        Args:
            uri: 请求路由
            params: 请求参数

        Returns:

        """
        final_uri = uri
        if isinstance(params, dict):
            final_uri = f"{uri}?" f"{urlencode(params)}"

        headers = await self._pre_headers(final_uri)
        res = await self.request(
            method="GET", url=f"{XHS_API_URL}{final_uri}", headers=headers, **kwargs
        )
        return res

    async def post(self, uri: str, data: dict, **kwargs) -> Union[Dict, Response]:
        """
        POST请求，对请求头签名
        Args:
            uri: 请求路由
            data: 请求体参数

        Returns:

        """
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        headers = await self._pre_headers(uri, data)
        res = await self.request(
            method="POST",
            url=f"{XHS_API_URL}{uri}",
            data=json_str,
            headers=headers,
            **kwargs,
        )
        return res

    async def pong(self) -> bool:
        """
        用于检查登录态和签名服务是否失效了
        Returns:

        """
        await self._sign_client.pong_sign_server()
        utils.logger.info("[XiaoHongShuClient.pong] Begin to check login state...")
        ping_flag = False
        try:
            self_info: Dict = await self.query_self()
            if self_info.get("result", {}).get("success"):
                ping_flag = True
        except Exception as e:
            raise e
            utils.logger.error(f"[XiaoHongShuClient.pong] Ping xhs failed: {e}")
            ping_flag = False
        utils.logger.info(f"[XiaoHongShuClient.pong] Login state result: {ping_flag}")
        return ping_flag

    async def query_self(self) -> Optional[Dict]:
        """
        查询自己信息
        """
        uri = "/api/sns/web/v1/user/selfinfo"
        res = await self.get(uri)
        return res

    async def get_note_by_id(
        self, note_id: str, xsec_source: str = "", xsec_token: str = ""
    ) -> Dict:
        """
        获取笔记详情API
        Args:
            note_id:笔记ID
            xsec_source: 渠道来源
            xsec_token: 搜索关键字之后返回的比较列表中返回的token

        Returns:

        """
        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
        }
        if xsec_token:
            data["xsec_token"] = xsec_token
            data["xsec_source"] = xsec_source

        uri = "/api/sns/web/v1/feed"
        res = await self.post(uri, data)
        if res and res.get("items"):
            res_dict: Dict = res["items"][0]["note_card"]
            return res_dict
        # 爬取频繁了可能会出现有的笔记能有结果有的没有
        utils.logger.error(
            f"[XiaoHongShuClient.get_note_by_id] get note id:{note_id} empty and res:{res}"
        )
        return dict()

    async def get_creator_info(self, creator_id: str) -> Optional[CreatorQueryResponse]:
        """
        通过解析网页版的用户主页HTML，获取用户个人简要信息
        PC端用户主页的网页存在window.__INITIAL_STATE__这个变量上的，解析它即可
        eg: https://www.xiaohongshu.com/user/profile/59d8cb33de5fb4696bf17217
        """
        uri = f"/user/profile/{creator_id}"
        response: Response = await self.request(
            "GET", XHS_INDEX_URL + uri, return_response=True, headers=self.headers
        )
        match = re.search(
            r"<script>window.__INITIAL_STATE__=(.+)<\/script>", response.text, re.M
        )

        if match is None:
            return {}

        info = json.loads(match.group(1).replace(":undefined", ":null"), strict=False)
        if info is None:
            return None
        creator_info = self._extractor.extract_creator_info(info)
        if creator_info:
            creator_info.user_id = creator_id
        return creator_info

    async def get_creator_contents(
        self, creator_id: str, cursor: str
    ) -> Optional[CreatorContentListResponse]:
        """
        获取创作者内容

        Args:
            creator_id: 创作者ID
            cursor: 上一页最后一条笔记的ID

        Returns:
            CreatorContentListResponse: 创作者内容列表响应
        """
        response = await self.get_notes_by_creator(creator_id, cursor)
        return self._extractor.extract_contents_from_user_profile(response)

    async def get_notes_by_creator(
        self, creator: str, cursor: str, page_size: int = 30
    ) -> Dict:
        """
        获取博主的笔记
        Args:
            creator: 博主ID
            cursor: 上一页最后一条笔记的ID
            page_size: 分页数据长度

        Returns:

        """
        uri = "/api/sns/web/v1/user_posted"
        data = {
            "user_id": creator,
            "cursor": cursor,
            "num": page_size,
            "image_formats": "jpg,webp,avif",
        }
        return await self.get(uri, data)

    async def get_note_by_id_from_html(
        self, note_id: str, xsec_source: str, xsec_token: str
    ) -> Optional[Dict]:
        """
        通过解析网页版的笔记详情页HTML，获取笔记详情

        Args:
            note_id: 笔记ID
            xsec_source: 渠道来源
            xsec_token: 搜索关键字之后返回的比较列表中返回的token

        Returns:

        """
        req_url = f"{XHS_INDEX_URL}/explore/{note_id}?xsec_token={xsec_token}&xsec_source={xsec_source}"
        retry_times = 5
        for current_retry in range(1, retry_times + 1):
            copy_headers = self.headers.copy()
            if current_retry <= 3:
                # 前三次删除cookie，直接不带登录态请求网页
                del copy_headers["Cookie"]

            async with httpx.AsyncClient() as client:
                try:
                    reponse = await client.get(req_url, headers=copy_headers)
                    note_dict = self._extractor.extract_note_detail_from_html(
                        note_id, reponse.text
                    )
                    if note_dict:
                        utils.logger.info(
                            f"[XiaoHongShuClient.get_note_by_id_from_html] get note_id:{note_id} detail from html success"
                        )
                        return note_dict

                    utils.logger.info(
                        f"[XiaoHongShuClient.get_note_by_id_from_html] current retried times: {current_retry}"
                    )
                    await asyncio.sleep(random.random())
                except Exception as e:
                    utils.logger.error(
                        f"[XiaoHongShuClient.get_note_by_id_from_html] 请求笔记详情页失败: {e}"
                    )
                    await asyncio.sleep(random.random())
        return None

    async def get_content_detail(
        self, content_id: str, ori_content_url: str = ""
    ) -> Optional[ContentDetailResponse]:
        """
        获取内容详情

        Args:
            content_id: 内容ID
            ori_content_url: 原始内容URL

        Returns:
            ContentDetailResponse: 内容详情
        """
        parsed_url = urlparse(ori_content_url)
        query_params = parse_qs(parsed_url.query)
        xsec_token = query_params.get("xsec_token", [None])[0]
        xsec_source = query_params.get("xsec_source", [None])[0]
        try:            
            note_dict = await self.get_note_by_id(
                content_id, xsec_source, xsec_token
            )
        except Exception as e:
            utils.logger.error(
                f"[XiaoHongShuClient.get_content_detail] 请求笔记详情页失败: {e}"
            )
            note_dict = await self.get_note_by_id_from_html(content_id, xsec_source, xsec_token)
            if not note_dict:
                raise Exception("获取笔记详情失败")

        return self._extractor.extract_content_detail(note_dict)
