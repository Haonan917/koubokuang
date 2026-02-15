# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/download_server_client.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""
DownloadServer 客户端 - 调用 MediaCrawlerPro-Downloader API 获取内容信息

通过 DownloadServer API 获取视频详情和下载链接，从 platform_cookies 表获取平台 cookies。
支持 B站、抖音、小红书、快手等平台。
"""
from typing import Optional, Tuple

import httpx

from config import settings
from schemas import Platform, ContentType, ContentParseResponse
from utils.logger import logger


class DownloadServerError(Exception):
    """DownloadServer API 错误"""
    pass


class ContentNotFoundError(DownloadServerError):
    """内容不存在"""
    pass


class CookiesNotFoundError(DownloadServerError):
    """未找到有效的 Cookies"""
    pass


# 平台名称映射: Platform enum -> API/数据库标识
# 用于 DownloadServer API platform 参数和数据库 platform_name
PLATFORM_MAPPING = {
    Platform.BILIBILI: "bili",
    Platform.DOUYIN: "dy",
    Platform.XHS: "xhs",
    Platform.KUAISHOU: "ks",
}


class DownloadServerClient:
    """
    DownloadServer API 客户端

    功能:
    1. 解析 URL 识别平台
    2. 从 platform_cookies 表获取对应平台的 cookies
    3. 调用 DownloadServer API 获取内容详情
    4. 返回结构化的 ContentParseResponse
    """

    def __init__(self):
        self.base_url = settings.DOWNLOAD_SERVER_BASE
        self.timeout = settings.DOWNLOAD_SERVER_TIMEOUT

    async def ping(self) -> bool:
        """
        检测 DownloadServer 服务是否可用

        Returns:
            True 如果服务可用

        Raises:
            DownloadServerError: 服务不可用
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/ping")
                response.raise_for_status()
                data = response.json()

                if data.get("biz_code") == 0:
                    return True
                raise DownloadServerError(f"DownloadServer 返回错误: {data.get('msg')}")
        except httpx.TimeoutException:
            raise DownloadServerError(f"DownloadServer 连接超时: {self.base_url}")
        except httpx.ConnectError:
            raise DownloadServerError(f"无法连接到 DownloadServer: {self.base_url}")
        except httpx.HTTPStatusError as e:
            raise DownloadServerError(f"DownloadServer HTTP 错误: {e.response.status_code}")
        except httpx.RequestError as e:
            raise DownloadServerError(f"DownloadServer 请求失败: {e}")

    def _parse_url(self, url: str) -> Platform:
        """
        解析 URL 识别平台

        Args:
            url: 原始链接

        Returns:
            Platform 枚举

        Raises:
            ValueError: 无法识别的 URL
        """
        url_lower = url.lower()

        # B站
        if 'bilibili.com' in url_lower or 'b23.tv' in url_lower:
            return Platform.BILIBILI

        # 抖音
        if 'douyin.com' in url_lower or 'v.douyin.com' in url_lower:
            return Platform.DOUYIN

        # 小红书
        if 'xiaohongshu.com' in url_lower or 'xhslink.com' in url_lower:
            return Platform.XHS

        # 快手
        if 'kuaishou.com' in url_lower or 'v.kuaishou.com' in url_lower:
            return Platform.KUAISHOU

        raise ValueError(f"不支持的平台: {url}")

    @staticmethod
    def _is_cookie_related_error(msg: str) -> bool:
        if not msg:
            return False
        m = msg.lower()
        keywords = [
            "cookies", "cookie", "登录", "失效", "过期",
            "verify", "captcha", "风控", "频次", "blocked",
        ]
        return any(k in m for k in keywords)

    async def fetch_content(self, url: str) -> ContentParseResponse:
        """
        获取内容详情

        Args:
            url: 原始链接

        Returns:
            ContentParseResponse

        Raises:
            DownloadServerError: API 调用失败
            ContentNotFoundError: 内容不存在
            CookiesNotFoundError: 未找到 cookies
        """
        # 1. 解析平台
        try:
            platform = self._parse_url(url)
        except ValueError as e:
            raise DownloadServerError(str(e))

        # 3. 调用 API
        api_platform = PLATFORM_MAPPING.get(platform)
        if not api_platform:
            raise DownloadServerError(f"未知平台: {platform}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/content_detail",
                    json={
                        "platform": api_platform,
                        "content_url": url,
                    }
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException:
            raise DownloadServerError(f"请求超时: {self.base_url}")
        except httpx.HTTPStatusError as e:
            raise DownloadServerError(f"HTTP 错误: {e.response.status_code}")
        except httpx.RequestError as e:
            raise DownloadServerError(f"请求失败: {e}")

        # 4. 解析响应
        if data.get("biz_code") != 0:
            msg = data.get("msg", "未知错误")
            if self._is_cookie_related_error(msg):
                logger.warning(f"[DownloadServerClient] cookie-related error from DownloadServer: {msg}")
            if "not found" in msg.lower() or "不存在" in msg:
                raise ContentNotFoundError(f"内容不存在: {msg}")
            raise DownloadServerError(f"API 错误: {msg}")

        content = data.get("data", {}).get("content", {})
        if not content:
            raise ContentNotFoundError("API 返回数据为空")

        # 5. 构建响应
        return self._build_response(platform, content)

    def _build_response(self, platform: Platform, content: dict) -> ContentParseResponse:
        """
        构建 ContentParseResponse

        Args:
            platform: 平台
            content: API 返回的 content 数据

        Returns:
            ContentParseResponse
        """
        # 提取内容 ID
        content_id = content.get("id", "")

        # 判断内容类型
        # 注意：DownloadServer API 返回的 content_type 可能是：
        # - "video": 视频内容
        # - "image": 图片内容
        # - "note": 图文笔记（小红书、抖音等平台的图文类型）
        # - 其他: 混合内容
        content_type_str = content.get("content_type", "video")
        if content_type_str == "video":
            content_type = ContentType.VIDEO
        elif content_type_str in ("image", "note"):
            # "note" 是小红书/抖音的图文笔记，本质上是图片内容
            content_type = ContentType.IMAGE
        else:
            content_type = ContentType.MIXED

        # 提取额外信息 (extria_info 包含 owner, duration, audio_url 等)
        extria_info = content.get("extria_info", {}) or {}

        # 提取视频/音频下载链接
        # B站: video_download_url 是纯视频 m4s，audio_url 是纯音频 m4s
        # 抖音/小红书/快手: video_download_url 包含完整视音频
        audio_url = extria_info.get("audio_url") or content.get("audio_url") or ""
        video_download_url = content.get("video_download_url") or content.get("video_url") or ""

        # 分开存储视频和音频 URL
        # - video_url: 视频下载链接（用于持久化）
        # - audio_url: 音频下载链接（用于 ASR，B站单独提供）
        # 注意：对于纯图片内容，即使 API 返回了 video_url 也应该忽略
        if content_type == ContentType.IMAGE:
            video_url = None
            audio_url = None
        else:
            video_url = video_download_url if video_download_url else None

        # 提取图片列表
        image_urls = content.get("image_urls", []) or content.get("images", []) or []
        if isinstance(image_urls, str):
            image_urls = [image_urls] if image_urls else []

        # 提取作者信息
        # 支持多种结构：
        # - extria_info.owner (B站: mid, name, face)
        # - content.author (小红书/抖音: user_id, nickname, avatar)
        # - content.owner (旧格式)
        author_info = content.get("author", {}) or {}
        owner = extria_info.get("owner", {}) or content.get("owner", {}) or {}

        author_id = str(
            author_info.get("user_id", "")
            or author_info.get("sec_uid", "")
            or owner.get("mid", "")
            or owner.get("id", "")
            or content.get("author_id", "")
        )
        author_name = (
            author_info.get("nickname", "")
            or owner.get("name", "")
            or content.get("author_name", "")
        )
        author_avatar = (
            author_info.get("avatar", "")
            or owner.get("face", "")
            or owner.get("avatar", "")
            or content.get("author_avatar", "")
        )

        # 提取互动数据
        # 支持多种结构：
        # - content.interaction (小红书/抖音: liked_count, collected_count, comment_count, share_count)
        # - content.stats (旧格式: like, reply, share, favorite)
        # - content 顶层字段 (like_count, comment_count 等)
        interaction = content.get("interaction", {}) or {}
        stats = content.get("stats", {}) or {}

        like_count = self._parse_count(
            interaction.get("liked_count")
            or stats.get("like")
            or content.get("like_count", 0)
        )
        comment_count = self._parse_count(
            interaction.get("comment_count")
            or stats.get("reply")
            or content.get("comment_count", 0)
        )
        share_count = self._parse_count(
            interaction.get("share_count")
            or stats.get("share")
            or content.get("share_count", 0)
        )
        collect_count = self._parse_count(
            interaction.get("collected_count")
            or stats.get("favorite")
            or content.get("collect_count", 0)
        )
        # 播放量（视频特有）
        view_count = self._parse_count(
            interaction.get("play_count")
            or stats.get("view")
            or content.get("view_count", 0)
        )
        # 弹幕数（B站特有）
        danmaku_count = self._parse_count(
            interaction.get("danmaku_count")
            or stats.get("danmaku")
            or content.get("danmaku_count", 0)
        )

        # 提取视频时长（秒）
        duration = extria_info.get("duration", 0) or content.get("duration", 0)

        # 提取发布时间
        publish_time = content.get("publish_time", 0) or content.get("create_time", 0)
        if publish_time and publish_time < 10000000000:  # 秒级时间戳
            publish_time = publish_time * 1000

        # 提取标签
        tags = content.get("tags", []) or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        return ContentParseResponse(
            platform=platform,
            content_id=str(content_id),
            content_type=content_type,
            title=content.get("title", "") or "",
            desc=content.get("desc", "") or content.get("description", "") or "",
            author_id=author_id,
            author_name=author_name,
            author_avatar=author_avatar,
            cover_url=content.get("cover_url", "") or content.get("cover", "") or "",
            video_url=video_url,
            audio_url=audio_url or None,  # B站单独提供音频，其他平台为空
            image_urls=image_urls,
            like_count=like_count,
            comment_count=comment_count,
            share_count=share_count,
            collect_count=collect_count,
            view_count=view_count,
            danmaku_count=danmaku_count,
            duration=int(duration) if duration else 0,
            publish_time=int(publish_time) if publish_time else 0,
            tags=tags,
        )

    @staticmethod
    def _parse_count(value) -> int:
        """
        解析数量字段，支持多种格式：
        - int: 直接返回
        - str (纯数字): "9883" -> 9883
        - str (逗号分隔): "1,234" -> 1234
        - str (中文单位): "1.3万" -> 13000, "1.2亿" -> 120000000
        """
        if isinstance(value, int):
            return value
        if value is None:
            return 0

        try:
            value_str = str(value).strip().replace(",", "")

            # 处理中文单位
            multiplier = 1
            if '亿' in value_str:
                multiplier = 100000000
                value_str = value_str.replace('亿', '')
            elif '万' in value_str:
                multiplier = 10000
                value_str = value_str.replace('万', '')

            # 解析数字部分（支持小数）
            if value_str:
                num = float(value_str)
                return int(num * multiplier)
            return 0
        except (ValueError, TypeError):
            return 0


# 创建全局客户端实例
download_server_client = DownloadServerClient()
