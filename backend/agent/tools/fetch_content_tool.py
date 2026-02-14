# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/tools/fetch_content_tool.py
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
内容获取工具 - 从社交媒体平台获取内容详情

通过 DownloadServer API 获取内容详情和视频下载链接。
支持 B站、抖音、小红书、快手等平台。

基于 LangChain 1.0 ToolRuntime 模式。
"""

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agent.state import RemixContext
from agent.errors import RemixToolException, RemixErrorCode, build_tool_user_message
from i18n import t
from schemas import Platform, ContentType, ContentParseResponse


class MockCrawlerClient:
    """Mock 客户端，用于测试和开发"""

    async def fetch_content(self, url: str) -> ContentParseResponse:
        """返回模拟数据"""
        return ContentParseResponse(
            platform=Platform.DOUYIN,
            content_id="mock_123456789",
            content_type=ContentType.VIDEO,
            title="【干货分享】3个提高效率的小技巧，让你的工作事半功倍！",
            desc="今天给大家分享3个我亲测有效的效率提升技巧，适合所有职场人士。看完记得点赞收藏哦~",
            author_id="12345678",
            author_name="效率达人小王",
            author_avatar="https://example.com/avatar.jpg",
            cover_url="https://example.com/cover.jpg",
            video_url="https://example.com/video.mp4",
            image_urls=[],
            like_count=10240,
            comment_count=528,
            share_count=256,
            collect_count=1024,
            publish_time=1704067200000,
            tags=["效率", "职场", "干货", "技巧"],
        )


@tool
async def fetch_content(url: str, runtime: ToolRuntime[RemixContext]) -> Command:
    """从社交媒体平台获取内容详情。

    通过 DownloadServer API 获取内容信息，包括:
    - 标题、描述
    - 作者信息
    - 封面图、视频下载链接
    - 互动数据（点赞、评论、收藏等）

    支持的平台: B站、抖音、小红书、快手

    Args:
        url: 社交媒体链接

    Returns:
        Command 更新 content_info 状态
    """
    from services.download_server_client import (
        DownloadServerClient,
        DownloadServerError,
        ContentNotFoundError,
        CookiesNotFoundError,
    )

    # 发送进度更新
    runtime.stream_writer({"stage": "fetching", "message": t("progress.fetchingContent")})

    try:
        # 从 context 获取配置，选择客户端
        use_mock = getattr(runtime.context, 'use_mock', False)

        if use_mock:
            # Mock 模式
            client = MockCrawlerClient()
            try:
                content = await client.fetch_content(url)
            except Exception as e:
                raise RemixToolException(
                    RemixErrorCode.FETCH_FAILED,
                    f"Mock 获取失败: {str(e)}",
                    {"url": url},
                )
        else:
            # 通过 DownloadServer API 获取
            client = DownloadServerClient()
            try:
                content = await client.fetch_content(url)
            except ContentNotFoundError as e:
                raise RemixToolException(
                    RemixErrorCode.CONTENT_NOT_FOUND,
                    t("errors.contentNotFound"),
                    {"url": url, "detail": str(e)},
                )
            except CookiesNotFoundError as e:
                raise RemixToolException(
                    RemixErrorCode.COOKIES_NOT_FOUND,
                    t("errors.cookiesNotFound"),
                    {"url": url, "detail": str(e)},
                )
            except DownloadServerError as e:
                raise RemixToolException(
                    RemixErrorCode.FETCH_FAILED,
                    t("errors.fetchFailed"),
                    {"url": url, "detail": str(e)},
                )

        content_dict = content.model_dump()

        # 添加原始链接 URL（用于前端 "Original" 按钮跳转到平台详情页）
        content_dict["original_url"] = url

        platform_name = t(f"platforms.{content.platform.value}")

        # 下载封面图到本地（避免前端跨域问题）
        from config import settings
        if settings.DOWNLOAD_COVER and content.cover_url:
            from services.asset_storage import AssetStorageService, AssetStorageError
            from utils.logger import logger

            asset_service = AssetStorageService()
            try:
                local_cover_url = await asset_service.download_cover(
                    content.cover_url,
                    content.platform.value,
                    content.content_id
                )
                content_dict["local_cover_url"] = local_cover_url
                logger.info(f"Cover downloaded to: {local_cover_url}")
            except AssetStorageError as e:
                logger.warning(f"Failed to download cover: {e}")
                # 封面下载失败不影响主流程，继续使用远程 URL

        # 下载图片列表到本地（用于多模态分析）
        # 只针对图文/混合类型内容，且 image_urls 非空时下载
        if content.content_type in (ContentType.IMAGE, ContentType.MIXED) and content.image_urls:
            from services.image_utils import download_and_process_images, ImageProcessError
            from utils.logger import logger

            try:
                runtime.stream_writer({
                    "stage": "fetching",
                    "message": t("progress.downloadingImages", count=len(content.image_urls[:settings.MULTIMODAL_MAX_IMAGES])),
                })

                processed_images = await download_and_process_images(
                    image_urls=content.image_urls,
                    platform=content.platform.value,
                    content_id=content.content_id,
                    max_images=settings.MULTIMODAL_MAX_IMAGES,
                )
                content_dict["local_image_paths"] = [img.local_path for img in processed_images]
                logger.info(f"Downloaded {len(processed_images)} images for multimodal analysis")
            except ImageProcessError as e:
                logger.warning(f"Failed to download images for multimodal: {e}")
                content_dict["local_image_paths"] = []
            except Exception as e:
                logger.warning(f"Unexpected error downloading images: {e}")
                content_dict["local_image_paths"] = []

        title_preview = content.title[:30] + "..." if len(content.title) > 30 else content.title
        runtime.stream_writer({
            "stage": "fetching",
            "message": t("progress.fetchComplete", title=title_preview),
            "result": {
                "platform": platform_name,
                "title": content.title,
                "has_video": bool(content.video_url),
            },
        })

        # 对于图文内容（非视频），立即发送 content_info 事件
        # 视频内容由 process_video 完成后发送（确保 local_video_url 已填充）
        is_image_content = content.content_type in (ContentType.IMAGE, ContentType.MIXED) or not content.video_url
        if is_image_content:
            await adispatch_custom_event(
                "content_info",
                {"content_info": content_dict},
            )

        # 返回包含 ToolMessage 的 Command
        # 构建包含完整信息的结果文本，让 Agent 能看到 desc
        result_parts = [
            f"**标题**: {content.title}",
            f"**平台**: {platform_name}",
        ]
        if content.desc:
            result_parts.append(f"**描述**: {content.desc}")
        result_parts.append(f"**有视频**: {'是' if content.video_url else '否'}")

        # 添加图片信息（用于多模态分析）
        local_image_paths = content_dict.get("local_image_paths", [])
        if local_image_paths:
            result_parts.append(f"**图片**: 已下载 {len(local_image_paths)} 张图片，可进行视觉分析")
        elif content.image_urls:
            result_parts.append(f"**图片**: 有 {len(content.image_urls)} 张图片（未下载）")

        result_text = "内容获取成功\n\n" + "\n".join(result_parts)

        return Command(update={
            "messages": [ToolMessage(content=result_text, tool_call_id=runtime.tool_call_id)],
            "content_info": content_dict,
            "current_stage": "内容获取完成",
        })
    except RemixToolException as e:
        error_message = build_tool_user_message(e)
        return Command(update={
            "messages": [ToolMessage(content=error_message, tool_call_id=runtime.tool_call_id)],
            "current_stage": "内容获取失败",
        })
