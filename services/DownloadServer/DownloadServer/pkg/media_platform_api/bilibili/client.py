# -*- coding: utf-8 -*-
import asyncio
import json
import re
import traceback
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from httpx import Response
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

from abs.abs_api_client import AbstractApiClient
from constant.bilibili import BILI_API_URL, BILI_INDEX_URL, BILI_SPACE_URL
from models.base_model import ContentTypeEnum
from models.content_detail import Content, ContentDetailResponse
from models.creator import CreatorContentListResponse, CreatorQueryResponse
from pkg.media_platform_api.bilibili.extractor import BiliExtractor
from pkg.rpc.sign_srv_client import BilibliSignRequest, SignServerClient
from pkg.tools import utils
from pkg.cache.cache_factory import CacheFactory

from .exception import DataFetchError
from .field import SearchOrderType

memory_cache = CacheFactory().create_cache("memory")


class BilibiliApiClient(AbstractApiClient):
    def __init__(
        self,
        timeout: int = 10,
        user_agent: str = None,
        cookies: str = "",
    ):
        """
        bilibili client constructor
        Args:
            timeout: 请求超时时间配置
            user_agent: 自定义的User-Agent
            cookies: 登录的cookies
        """
        self.timeout = timeout
        self._user_agent = user_agent or utils.get_user_agent()
        self._sign_client = SignServerClient()
        self._cookies = cookies
        self._extractor = BiliExtractor()
        self._w_webid = ""

    async def async_initialize(self):
        """
        异步初始化
        Returns:

        """
        try:
            pass
        except RetryError as e:
            utils.logger.error(
                f"[BilibiliClient.async_initialize] Get w_webid failed: {e}"
            )
            raise Exception("获取w_webid失败")

    @property
    def headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Cookie": self._cookies,
            "origin": BILI_INDEX_URL,
            "referer": BILI_INDEX_URL,
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

    async def pre_request_data(self, req_data: Dict) -> Dict:
        """
        发送请求进行请求参数签名
        :param req_data:
        :return:
        """
        if not req_data:
            return {}
        sign_req = BilibliSignRequest(req_data=req_data, cookies=self._cookies)
        sign_resp = await self._sign_client.bilibili_sign(sign_req)
        req_data.update({"wts": sign_resp.data.wts, "w_rid": sign_resp.data.w_rid})
        return req_data

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
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)
        try:
            data: Dict = response.json()
            if data.get("code") != 0:
                if (
                    data.get("code") == -404
                ):  # 这种情况多半是请求的资源不可见了（被隐藏了或者被删除了）
                    utils.logger.warn(
                        f"[BilibiliClient.request] 请求失败: {url}, error: {data.get('message')}"
                    )
                    return {}
                raise DataFetchError(data.get("message", "unkonw error"))
            else:
                return data.get("data", {})
        except Exception as e:
            utils.logger.error(
                f"[BilibiliClient.request] 请求失败: {url}, error: {e}, response: {response.text}"
            )
            raise DataFetchError("数据请求失败")

    async def get(
        self, uri: str, params=None, enable_params_sign: bool = True, **kwargs
    ) -> Union[Dict, Response]:
        """
        GET请求，对请求头参数进行签名

        Args:
            uri: 请求路径
            params: 请求参数
            enable_params_sign: 是否对请求参数进行签名

        Returns:

        """
        final_uri = uri
        if enable_params_sign:
            params = await self.pre_request_data(params)
        if isinstance(params, dict):
            final_uri = f"{uri}?{urlencode(params)}"
        return await self.request(
            method="GET",
            url=f"{BILI_API_URL}{final_uri}",
            headers=self.headers,
            **kwargs,
        )

    async def post(self, uri: str, data: dict) -> Union[Dict, Response]:
        """
        POST请求, 对请求参数进行签名

        Args:
            uri: 请求路径
            data: 请求参数

        Returns:

        """

        data = await self.pre_request_data(data)
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return await self.request(
            method="POST",
            url=f"{BILI_API_URL}{uri}",
            data=json_str,
            headers=self.headers,
        )

    async def pong(self) -> bool:
        """
        ping bilibili to check login state
        Returns:

        """
        utils.logger.info("[BilibiliClient.pong] Begin pong bilibili...")
        ping_flag = False
        try:
            check_login_uri = "/x/web-interface/nav"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BILI_API_URL}{check_login_uri}",
                    headers=self.headers,
                )
            res = response.json()
            if res and res.get("code") == 0 and res.get("data").get("isLogin"):
                ping_flag = True
        except Exception as e:
            utils.logger.error(f"[BilibiliClient.pong] Pong bilibili failed: {e}")
            ping_flag = False
        return ping_flag

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def get_w_webid(self, up_id: str) -> str:
        """
        获取w_webid

        Args:
            up_id (str): UP主ID

        Returns:
            str: w_webid
        """
        cache_key = f"w_webid_key"
        ttl = 3600 * 12
        if memory_cache.get(cache_key):
            return memory_cache.get(cache_key)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BILI_SPACE_URL}/{up_id}/dynamic", headers=self.headers
            )
            w_webid = self._extractor.extract_w_webid(response.text)
            memory_cache.set(cache_key, w_webid, ttl)
            if not w_webid:
                raise DataFetchError("获取w_webid失败")
        return w_webid

    async def get_video_info(
        self, aid: Optional[int] = None, bvid: Optional[str] = None
    ) -> Dict:
        """
        Bilibli web video detail api, aid 和 bvid任选一个参数
        Args:
            aid: 稿件avid
            bvid: 稿件bvid

        Returns:

        """
        if not aid and not bvid:
            raise ValueError("请提供 aid 或 bvid 中的至少一个参数")

        uri = "/x/web-interface/view/detail"
        params = dict()
        if aid:
            params.update({"aid": aid})
        else:
            params.update({"bvid": bvid})
        return await self.get(uri, params, enable_params_sign=True)

    async def get_up_info(self, up_id: str) -> Dict:
        """
        获取UP主信息

        Args:
            up_id: UP主ID

        Returns:

        """
        params = {
            "mid": up_id,
            "token": "",
            "platform": "web",
            "web_location": "1550101",            
            # 下面这个几个是浏览器指纹信息
            "dm_img_list": "[]",
            "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
            "dm_cover_img_str": "QU5HTEUgKEFwcGxlLCBBTkdMRSBNZXRhbCBSZW5kZXJlcjogQXBwbGUgTTEsIFVuc3BlY2lmaWVkIFZlcnNpb24pR29vZ2xlIEluYy4gKEFwcGxlKQ",
            "dm_img_inter": '{"ds":[],"wh":[4437,2834,85],"of":[321,642,321]}',
        }
        return await self.get("/x/space/wbi/acc/info", params)

    async def get_relation_state(self, up_id: str) -> Dict:
        """
        获取UP主关系状态

        Args:
            up_id: UP主ID

        Returns:

        """
        params = {"vmid": up_id, "web_location": 333.999}
        return await self.get("/x/relation/stat", params)

    async def get_space_navnum(self, up_id: str) -> Dict:
        """
        获取UP主空间导航栏数据

        Args:
            up_id: UP主ID

        Returns:

        """
        params = {"mid": up_id, "platform": "web", "web_location": 333.999}
        return await self.get("/x/space/navnum", params)

    async def get_space_upstate(self, up_id: str) -> Dict:
        """
        获取UP主空间状态

        Args:
            up_id: UP主ID

        Returns:

        """
        params = {"mid": up_id, "platform": "web", "web_location": 333.999}
        return await self.get("/x/space/upstat", params, enable_params_sign=False)

    async def get_creator_videos(
        self,
        creator_id: str,
        page_num: int,
        page_size: int = 30,
        order_mode: SearchOrderType = SearchOrderType.LAST_PUBLISH,
    ) -> Dict:
        """
        获取创作者的视频列表
        Args:
            creator_id: 创作者 ID
            page_num:
            page_size:
            order_mode:

        Returns:

        """
        uri = "/x/space/wbi/arc/search"
        post_data = {
            "mid": creator_id,
            "pn": page_num,
            "ps": page_size,
            "order": order_mode.value,
        }
        return await self.get(uri, post_data)

    async def get_all_videos_by_creator(
        self,
        creator_id: str,
        order_mode: SearchOrderType = SearchOrderType.LAST_PUBLISH,
    ) -> List[Dict]:
        """
        获取创作者的所有视频
        Args:
            creator_id: 创作者 ID
            order_mode: 排序方式

        Returns:

        """
        result = []
        page_num = 1
        page_size = 30
        has_more = True
        while has_more:
            videos_res = await self.get_creator_videos(
                creator_id, page_num, page_size, order_mode
            )
            video_list = videos_res.get("list", {}).get("vlist", [])
            result.extend(video_list)
            has_more = videos_res.get("page").get("count") > page_num * page_size
            page_num += 1
        return result

    async def get_creator_info(self, creator_id: str) -> Optional[CreatorQueryResponse]:
        """
        Get creator info

        Args:
            creator_id (str): 创作者ID

        Returns:
            CreatorQueryResponse: 创作者信息
        """
        up_info, relation_state, space_navnum = await asyncio.gather(
            self.get_up_info(creator_id),
            self.get_relation_state(creator_id),
            self.get_space_navnum(creator_id),
        )
        return self._extractor.extract_creator_info(
            up_info, relation_state, space_navnum
        )

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
        if not cursor:
            cursor = 1
        videos_res = await self.get_creator_videos(creator_id, cursor, 30)
        return self._extractor.extract_creator_contents(int(cursor), videos_res)

    async def get_video_info(
        self, aid: Union[int, None] = None, bvid: Union[str, None] = None
    ) -> Dict:
        """
        Bilibli web video detail api, aid 和 bvid任选一个参数
        :param aid: 稿件avid
        :param bvid: 稿件bvid
        :return:
        """
        if not aid and not bvid:
            raise ValueError("请提供 aid 或 bvid 中的至少一个参数")

        uri = "/x/web-interface/wbi/view"
        params = dict()
        if aid:
            params.update({"aid": aid})
        else:
            params.update({"bvid": bvid})
        return await self.get(uri, params, enable_params_sign=False)

    async def get_video_play_url(self, aid: int, cid: int) -> Dict:
        """
        Bilibli web video play url api
        :param aid: 稿件avid
        :param cid: cid
        :return:
        """
        if not aid or not cid or aid <= 0 or cid <= 0:
            raise ValueError("aid 和 cid 必须存在")
        uri = "/x/player/wbi/playurl"
        params = {
            "avid": aid,
            "cid": cid,
            "qn": 127,       # 请求最高清晰度(8K)，API会返回可用的最高质量
            "fnval": 4048,   # DASH格式 + 所有高级特性 (16|64|128|256|512|1024|2048)
            "fnver": 0,      # 固定值
            "fourk": 1,      # 允许4K
            "platform": "pc",
        }

        return await self.get(uri, params, enable_params_sign=True)

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
        try:
            # 解析视频ID
            bvid = None
            aid = None
            video_url = ori_content_url or content_id
            
            if video_url.startswith("BV"):
                bvid = content_id
            elif video_url.startswith("av") or content_id.isdigit():
                aid = int(content_id.replace("av", ""))
            elif "bilibili.com/video/" in video_url:
                # 从URL中提取BV号
                bv_match = re.search(r"/video/(BV\w+)", video_url)
                if bv_match:
                    bvid = bv_match.group(1)
                else:
                    # 尝试提取av号
                    av_match = re.search(r"/video/av(\d+)", video_url)
                    if av_match:
                        aid = int(av_match.group(1))
            else:
                # 如果都不匹配，尝试直接使用content_id作为bvid
                bvid = content_id

            if not bvid and not aid:
                utils.logger.error(
                    f"[BilibiliClient.get_content_detail] 无法解析视频ID: content_id={content_id}, url={ori_content_url}"
                )
                return None

            # 获取视频基本信息
            video_info = await self.get_video_info(aid=aid, bvid=bvid)
            if not video_info:
                utils.logger.error(
                    f"[BilibiliClient.get_content_detail] 获取视频信息失败"
                )
                return None

            # 获取视频播放URL
            video_aid = video_info.get("aid")
            video_cid = video_info.get("cid")
            if not video_aid or not video_cid:
                utils.logger.error(
                    f"[BilibiliClient.get_content_detail] 视频信息中缺少aid或cid"
                )
                return None

            play_url_info = await self.get_video_play_url(video_aid, video_cid)
            if not play_url_info:
                utils.logger.error(
                    f"[BilibiliClient.get_content_detail] 获取播放URL失败"
                )
                return None

            # 提取视频下载URL和格式信息
            video_download_url = ""
            media_format = ""
            format_info = {}
            
            dash_info = play_url_info.get("dash", {})
            durl_info = play_url_info.get("durl", [])
            
            if dash_info and (dash_info.get("video") or dash_info.get("audio")):
                # DASH格式（音视频分轨）
                media_format = "DASH"
                video_streams = dash_info.get("video", [])
                audio_streams = dash_info.get("audio", [])
                
                # 选择最高质量的视频流作为主下载URL
                if video_streams:
                    # 按清晰度ID排序，选择最高质量
                    video_streams.sort(key=lambda x: x.get("id", 0), reverse=True)
                    best_video = video_streams[0]
                    video_download_url = best_video.get("baseUrl", "") or best_video.get("base_url", "")
                
                # 整理DASH格式信息
                format_info = {
                    "format_type": "DASH",
                    "video_streams": [
                        {
                            "quality_id": stream.get("id"),
                            "quality_name": f"{stream.get('height', 0)}P" if stream.get("height") else f"ID_{stream.get('id')}",
                            "url": stream.get("baseUrl", "") or stream.get("base_url", ""),
                            "backup_urls": stream.get("backupUrl", []) or stream.get("backup_url", []),
                            "width": stream.get("width"),
                            "height": stream.get("height"),
                            "bandwidth": stream.get("bandwidth"),
                            "codecs": stream.get("codecs"),
                            "frame_rate": stream.get("frameRate", "") or stream.get("frame_rate", ""),
                            "codecid": stream.get("codecid")
                        }
                        for stream in video_streams
                    ],
                    "audio_streams": [
                        {
                            "quality_id": stream.get("id"),
                            "url": stream.get("baseUrl", "") or stream.get("base_url", ""),
                            "backup_urls": stream.get("backupUrl", []) or stream.get("backup_url", []),
                            "bandwidth": stream.get("bandwidth"),
                            "codecs": stream.get("codecs"),
                            "codecid": stream.get("codecid")
                        }
                        for stream in audio_streams
                    ],
                    "dolby_info": dash_info.get("dolby"),
                    "flac_info": dash_info.get("flac"),
                    "duration": dash_info.get("duration"),
                    "min_buffer_time": dash_info.get("minBufferTime") or dash_info.get("min_buffer_time")
                }
                
                # 如果没有视频流但有音频流，使用音频URL作为主URL
                if not video_download_url and audio_streams:
                    audio_streams.sort(key=lambda x: x.get("id", 0), reverse=True)
                    best_audio = audio_streams[0]
                    video_download_url = best_audio.get("baseUrl", "") or best_audio.get("base_url", "")
                    
            elif durl_info:
                # MP4格式（单路复合流）
                media_format = "MP4"
                video_download_url = durl_info[0].get("url", "")
                
                format_info = {
                    "format_type": "MP4",
                    "segments": [
                        {
                            "order": segment.get("order"),
                            "url": segment.get("url"),
                            "backup_urls": segment.get("backup_url", []),
                            "length": segment.get("length"),
                            "size": segment.get("size")
                        }
                        for segment in durl_info
                    ]
                }

            # 使用提取器提取作者信息和互动数据
            author = self._extractor.extract_author_info_from_video_detail(video_info)
            interaction = self._extractor.extract_interaction_info_from_video_detail(
                video_info
            )

            # 构建Content对象
            content = Content(
                id=str(video_info.get("bvid", video_info.get("aid", ""))),
                url=f"{BILI_INDEX_URL}/video/{video_info.get('bvid', 'av' + str(video_info.get('aid', '')))}",
                title=video_info.get("title", ""),
                desc=video_info.get("desc", ""),
                content_type=ContentTypeEnum.VIDEO,
                cover_url=video_info.get("pic", ""),
                image_urls=[],
                video_download_url=video_download_url,
                author=author,
                interaction=interaction,
                extria_info={
                    "media_format": media_format,
                    "audio_url": format_info.get("audio_streams", [{}])[0].get("url", "")
                    if media_format == "DASH" and format_info.get("audio_streams")
                    else "",
                    "duration": video_info.get("duration", 0),
                    "owner": video_info.get("owner", {}),
                },
            )

            return ContentDetailResponse(content=content)

        except Exception as e:
            utils.logger.error(
                f"[BilibiliClient.get_content_detail] 获取内容详情失败: {e}"
            )
            utils.logger.error(traceback.format_exc())
            return None
