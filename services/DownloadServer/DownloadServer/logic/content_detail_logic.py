# -*- coding: utf-8 -*-
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from logic.base_logic import BaseLogic
from models.base_model import PlatformEnum
from models.content_detail import ContentDetailRequest, ContentDetailResponse
from pkg.tools import utils


class ContentDetailLogic(BaseLogic):

    def __init__(self, platform: PlatformEnum, cookies: str = ""):
        """
        content detail logic constructor

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

    def _is_douyin_short_url(self, url: str) -> bool:
        """
        检测是否为抖音短链接

        Args:
            url: URL字符串

        Returns:
            bool: 是否为短链接
        """
        parsed_url = urlparse(url)
        return parsed_url.netloc in ["v.douyin.com", "www.iesdouyin.com"]

    def extract_content_id(self, url: str) -> Tuple[bool, str, str]:
        """
        extract content id from url

        Args:
            url: media platform user url

        Returns:
            tuple:
                bool: is_valid
                str: extract_msg
                str: content_id (如果是短链接，返回 "SHORT_URL:{原始URL}")
        """
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        url_path = parsed_url.netloc + parsed_url.path
        if url_path.endswith("/"):
            url_path = url_path[:-1]
        mutile_patterns: List[str] = []
        if self.platform == PlatformEnum.DOUYIN:
            # 检测短链接
            if self._is_douyin_short_url(url):
                return True, "", f"SHORT_URL:{url}"

            if query_params and (
                query_params.get("aweme_id") or query_params.get("modal_id")
            ):
                return (
                    True,
                    "",
                    query_params.get("aweme_id", [None])[0]
                    or query_params.get("modal_id", [None])[0],
                )

            pattern_video = r"/video/(.*)"
            pattern_note = r"/note/(.*)"
            mutile_patterns.append(pattern_video)
            mutile_patterns.append(pattern_note)
        elif self.platform == PlatformEnum.XHS:
            pattern_video = r"/explore/(.*)"
            mutile_patterns.append(pattern_video)
        elif self.platform == PlatformEnum.BILIBILI:
            pattern_video = r"/video/(.*)"
            mutile_patterns.append(pattern_video)
        elif self.platform == PlatformEnum.KUAISHOU:
            # https://www.kuaishou.com/short-video/3xm56cbtcj4gsz4?authorId=3xe2y946ihptq99&streamSource=profile&area=profilexxnull
            pattern_video = r"/short-video/(.*)"
            mutile_patterns.append(pattern_video)
        else:
            return False, "无效的自媒体平台", ""

        for pattern in mutile_patterns:
            match = re.findall(pattern, url_path)
            if match:
                return True, "", match[0]
        else:
            return False, "无效的URL", ""

    async def _resolve_douyin_short_url_and_extract_id(
        self, short_url: str
    ) -> Tuple[bool, str, str]:
        """
        解析抖音短链接并提取内容ID

        Args:
            short_url: 短链接URL

        Returns:
            tuple:
                bool: 是否成功
                str: 错误信息
                str: 内容ID
        """
        # 调用client的resolve_short_url方法
        redirect_url = await self.api_client.resolve_short_url(short_url)
        if not redirect_url:
            return False, "短链接解析失败", ""

        utils.logger.info(
            f"[ContentDetailLogic] Resolved short URL: {short_url} -> {redirect_url}"
        )

        # 从重定向URL中提取内容ID
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)

        # 优先从query参数中提取
        if query_params and (
            query_params.get("aweme_id") or query_params.get("modal_id")
        ):
            content_id = query_params.get("aweme_id", [None])[0] or query_params.get(
                "modal_id", [None])[0]
            return True, "", content_id

        # 从路径中提取
        url_path = parsed_url.netloc + parsed_url.path
        if url_path.endswith("/"):
            url_path = url_path[:-1]

        patterns = [r"/video/(\d+)", r"/note/(\d+)"]
        for pattern in patterns:
            match = re.search(pattern, url_path)
            if match:
                return True, "", match.group(1)

        return False, "无法从重定向URL中提取内容ID", ""

    async def query_content_detail(
        self, content_id: str, ori_content_url: str = ""
    ) -> Optional[ContentDetailResponse]:
        """
        查询内容详情

        Args:
            content_id (str): 内容ID (如果是短链接，格式为 "SHORT_URL:{url}")
            ori_content_url (str): 原始内容URL

        Returns:
            ContentDetailResponse: 内容详情
        """
        # 检测是否为抖音短链接
        if content_id.startswith("SHORT_URL:"):
            short_url = content_id[len("SHORT_URL:"):]
            is_valid, err_msg, real_content_id = (
                await self._resolve_douyin_short_url_and_extract_id(short_url)
            )
            if not is_valid:
                utils.logger.error(
                    f"[ContentDetailLogic] Failed to resolve short URL: {err_msg}"
                )
                return None
            content_id = real_content_id
            utils.logger.info(
                f"[ContentDetailLogic] Extracted content ID from short URL: {content_id}"
            )

        return await self.api_client.get_content_detail(content_id, ori_content_url)
