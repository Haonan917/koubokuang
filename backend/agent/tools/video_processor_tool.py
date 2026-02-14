# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/tools/video_processor_tool.py
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
视频处理工具 - 下载视频、提取音频、语音转文字

这是一个耗时较长的操作 (30-120秒)，包含:
1. 下载视频到临时目录
2. 使用 ffmpeg 提取音频
3. 使用 faster-whisper 进行语音识别

基于 LangChain 1.0 ToolRuntime 模式。
"""

import asyncio
import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agent.state import RemixContext
from agent.errors import (
    RemixToolException,
    RemixErrorCode,
    require_state,
    build_tool_user_message,
)
from i18n import t
from utils.logger import logger


@dataclass
class VideoProcessResult:
    """视频处理结果"""
    text: str  # 完整转录文本
    segments: list  # 带时间戳的分段列表 [{start, end, text}, ...]
    video_path: Optional[str] = None
    task_id: Optional[str] = None


async def _process_video_internal(
    video_url: str,
    step_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    persist_video: bool = False
) -> VideoProcessResult:
    """
    内部视频处理函数

    处理流程:
    1. 下载视频到临时目录
    2. 使用 ffmpeg 提取音频 (16kHz WAV)
    3. 使用 faster-whisper 进行语音识别
    4. 根据 persist_video 决定是否清理临时文件

    Args:
        video_url: 视频 URL
        step_callback: 子步骤回调函数
            - action: "start" | "end"
            - step_id: 子步骤唯一ID
            - label_or_message: 开始时是标签，结束时是完成消息
        persist_video: 是否保留视频文件（用于后续持久化）

    Returns:
        VideoProcessResult 包含转录文本和视频路径
    """
    import os
    import subprocess

    from services.video_downloader import VideoDownloader
    from services.audio_extractor import AudioExtractor

    downloader = VideoDownloader()
    extractor = AudioExtractor()

    task_id = str(uuid.uuid4())
    logger.info(f"Starting video processing, task_id={task_id}")

    try:
        # Step 1: 下载视频
        if step_callback:
            await step_callback("start", "download_video", t("progress.downloadVideo"))
        logger.info(f"[{task_id}] Downloading from: {video_url[:100]}...")
        video_path = await downloader.download(video_url, task_id)

        # 诊断：检查下载文件
        download_size = os.path.getsize(video_path)
        logger.info(f"[{task_id}] Downloaded: {video_path}, size: {download_size / 1024 / 1024:.2f} MB")

        if download_size < 100 * 1024:  # 小于 100KB
            logger.error(f"[{task_id}] Downloaded file too small: {download_size} bytes, may be incomplete")

        if step_callback:
            size_mb = f"{download_size / 1024 / 1024:.2f}"
            await step_callback("end", "download_video", t("progress.downloadComplete", size=size_mb))

        # Step 2: 提取音频 (同步操作，在线程池中运行)
        if step_callback:
            await step_callback("start", "extract_audio", t("progress.extractAudio"))
        logger.info(f"[{task_id}] Extracting audio...")
        audio_path = await asyncio.to_thread(extractor.extract, video_path)

        # 诊断：检查音频文件
        audio_size = os.path.getsize(audio_path)
        logger.info(f"[{task_id}] Extracted audio: {audio_path}, size: {audio_size / 1024 / 1024:.2f} MB")

        if step_callback:
            size_mb = f"{audio_size / 1024 / 1024:.2f}"
            await step_callback("end", "extract_audio", t("progress.extractComplete", size=size_mb))

        # 获取音频时长
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
        try:
            duration_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            audio_duration = float(duration_result.stdout.strip())
            logger.info(f"[{task_id}] Audio duration: {audio_duration:.2f} seconds")

            if audio_duration < 10:
                logger.warning(f"[{task_id}] Audio duration very short: {audio_duration:.2f}s, may indicate extraction issue")
        except Exception as e:
            logger.warning(f"[{task_id}] Could not get audio duration: {e}")

        # Step 3: ASR 转录 (同步操作，在线程池中运行)
        if step_callback:
            await step_callback("start", "transcribe", t("progress.transcribe"))
        logger.info(f"[{task_id}] Starting ASR transcription...")
        from services.asr_service import ASRService
        asr_service = ASRService()

        # 检查 faster-whisper 是否可用，不可用则直接报错
        if not asr_service.is_available():
            logger.error(f"[{task_id}] faster-whisper not available! Please install: uv add faster-whisper")
            raise RemixToolException(
                error_code=RemixErrorCode.ASR_FAILED,
                message=t("progress.asrNotAvailable"),
                details={"task_id": task_id}
            )
        logger.info(f"[{task_id}] Using ASRService (faster-whisper)")

        result = await asyncio.to_thread(asr_service.transcribe, audio_path)

        # 诊断：检查转录结果
        logger.info(f"[{task_id}] Transcription completed: {len(result.text)} chars, {len(result.segments)} segments")

        if len(result.text) < 200:
            logger.warning(f"[{task_id}] Transcript very short ({len(result.text)} chars)! Full content: {result.text}")
        else:
            logger.info(f"[{task_id}] Transcript preview: {result.text[:200]}...")

        if step_callback:
            await step_callback("end", "transcribe", t("progress.transcribeComplete", count=len(result.text)))

        # 将 Segment 对象转换为字典列表
        segments_list = [
            {"start": seg.start, "end": seg.end, "text": seg.text}
            for seg in result.segments
        ]

        return VideoProcessResult(
            text=result.text,
            segments=segments_list,
            video_path=video_path if persist_video else None,
            task_id=task_id if persist_video else None
        )

    except Exception as e:
        from services.video_downloader import VideoDownloadError
        from services.audio_extractor import AudioExtractError
        from services.asr_service import ASRError

        if isinstance(e, VideoDownloadError):
            raise RemixToolException(
                RemixErrorCode.DOWNLOAD_FAILED,
                t("errors.downloadFailed"),
                {"video_url": video_url, "stage": "downloading", "detail": str(e)},
            )
        elif isinstance(e, AudioExtractError):
            raise RemixToolException(
                RemixErrorCode.AUDIO_EXTRACT_FAILED,
                t("errors.audioExtractFailed"),
                {"video_url": video_url, "stage": "extracting", "detail": str(e)},
            )
        elif isinstance(e, ASRError):
            raise RemixToolException(
                RemixErrorCode.ASR_FAILED,
                t("errors.asrFailed"),
                {"video_url": video_url, "stage": "transcribing", "detail": str(e)},
            )
        else:
            raise RemixToolException(
                RemixErrorCode.INTERNAL_ERROR,
                t("progress.videoProcessFailed", error=str(e)),
                {"video_url": video_url, "stage": "unknown"},
            )

    finally:
        # 如果需要持久化视频，跳过清理（由调用方负责处理）
        if not persist_video:
            logger.info(f"[{task_id}] Cleaning up temporary files...")
            try:
                downloader.cleanup(task_id)
            except Exception as e:
                logger.warning(f"[{task_id}] Cleanup failed: {e}")
        else:
            logger.info(f"[{task_id}] Skipping cleanup (persist_video=True)")


@tool
async def process_video(runtime: ToolRuntime[RemixContext]) -> Command:
    """处理视频内容：下载视频、提取音频、转录语音。

    注意: 这是一个耗时操作，可能需要 30-120 秒。

    前置条件: 需要先调用 fetch_content 获取内容，确保 content_info 中有 video_url。

    处理流程:
    1. 下载视频到临时目录
    2. 使用 ffmpeg 提取音频 (16kHz WAV)
    3. 使用 faster-whisper 进行中文语音识别
    4. 返回转录文本

    Returns:
        Command 更新 transcript 状态
    """
    # 验证必需的状态
    content_info = runtime.state.get("content_info")
    if not content_info:
        return Command(update={
            "messages": [ToolMessage(
                content="content_info 尚未就绪，请先调用 fetch_content 获取内容信息后再调用 process_video。",
                tool_call_id=runtime.tool_call_id,
            )],
        })

    # 检查是否已有转录结果（缓存复用）
    existing_transcript = runtime.state.get("transcript")
    current_content_id = content_info.get("content_id")

    if existing_transcript and len(existing_transcript) > 0:
        cached_content_id = existing_transcript.get("content_id")
        # 只有 content_id 匹配时才使用缓存
        if cached_content_id == current_content_id:
            transcript_len = len(existing_transcript) if isinstance(existing_transcript, str) else len(existing_transcript.get("text", ""))
            logger.info(f"[process_video] Using cached transcript ({transcript_len} chars) for content_id={current_content_id}")
            runtime.stream_writer({
                "stage": "transcribing",
                "message": t("progress.usingCached", count=transcript_len),
            })
            return Command(update={
                "messages": [ToolMessage(
                    content=t("progress.usingCached", count=transcript_len),
                    tool_call_id=runtime.tool_call_id
                )],
                "current_stage": t("progress.usingCached", count=transcript_len),
            })
        else:
            logger.info(f"[process_video] Cache miss: content_id changed from {cached_content_id} to {current_content_id}")

    video_url = content_info.get("video_url")
    audio_url = content_info.get("audio_url")  # B站单独提供音频流

    if not video_url and not audio_url:
        # 非视频内容，跳过处理
        runtime.stream_writer({
            "stage": "transcribing",
            "message": t("progress.skipTranscript"),
        })
        # 发送 content_info 事件（供前端展示卡片）
        await adispatch_custom_event(
            "content_info",
            {"content_info": dict(content_info)},
        )
        return Command(update={
            "messages": [ToolMessage(content=t("progress.skipTranscript"), tool_call_id=runtime.tool_call_id)],
            "transcript": None,
            "current_stage": t("progress.skipTranscript"),
        })

    # ASR 优先使用 audio_url（B站音频流），否则使用 video_url
    asr_url = audio_url or video_url

    # 检查是否是可下载的视频/音频链接
    # DownloadServer API 返回的 video_download_url/audio_url 是可直接下载的
    check_url = asr_url
    is_downloadable = any([
        # 常见视频/音频格式后缀
        check_url.endswith(('.mp4', '.m3u8', '.flv', '.webm', '.m4s', '.wav', '.mp3', '.m4a')),
        # B站视频/音频流 (upos-sz-mirror 或 mcdn 开头的 CDN)
        'upos-sz-mirror' in check_url,
        'bilivideo' in check_url,
        'mcdn.bilivideo' in check_url,  # B站音频 CDN
        # 抖音视频
        'douyinvod' in check_url,
        'bytedance' in check_url,
        # 快手视频
        'kuaishou' in check_url,
        'kwaicdn' in check_url,
        # 小红书视频
        'xhscdn' in check_url,
        'xiaohongshu' in check_url and '/video/' in check_url,
        # 通用 CDN 标识
        '/video/' in check_url and 'http' in check_url,
        'cdn' in check_url.lower() and '/video' in check_url.lower(),
        '/resource/' in check_url,  # B站音频资源路径
    ])

    if not is_downloadable:
        # 检查是否是网页链接（而非 CDN 链接）
        is_webpage = any([
            'bilibili.com/video/' in check_url,
            'douyin.com/video/' in check_url,
            'xiaohongshu.com/explore/' in check_url,
            'kuaishou.com/short-video/' in check_url,
        ])

        if is_webpage:
            # 网页链接，无法直接下载，跳过视频处理
            runtime.stream_writer({
                "stage": "transcribing",
                "message": t("progress.webpageLink"),
            })
            # 发送 content_info 事件（供前端展示卡片，但没有 local_video_url）
            await adispatch_custom_event(
                "content_info",
                {"content_info": dict(content_info)},
            )
            return Command(update={
                "messages": [ToolMessage(
                    content=t("progress.webpageLink"),
                    tool_call_id=runtime.tool_call_id
                )],
                "transcript": None,
                "current_stage": t("progress.webpageLink"),
            })

    try:
        # 创建异步子步骤回调，使用 adispatch_custom_event 发送事件
        async def send_sub_step(action: str, step_id: str, label_or_message: str):
            """发送子步骤事件到 astream_events"""
            logger.info(f"[process_video] Sub-step {action}: {step_id} - {label_or_message}")
            if action == "start":
                await adispatch_custom_event(
                    "sub_step_start",
                    {
                        "step_id": step_id,
                        "label": label_or_message,
                        "parent_tool": "process_video",
                    },
                )
            else:
                await adispatch_custom_event(
                    "sub_step_end",
                    {
                        "step_id": step_id,
                        "message": label_or_message,
                    },
                )

        # 检查是否需要持久化视频
        from config import settings
        persist_video = settings.PERSIST_VIDEO

        # 判断是否需要单独下载视频（B站情况：audio_url 和 video_url 不同）
        need_separate_video_download = (
            persist_video
            and video_url
            and audio_url
            and video_url != audio_url
        )

        # 调用内部处理函数进行 ASR（使用 asr_url）
        # 如果需要单独下载视频，则不持久化 ASR 用的文件
        result = await _process_video_internal(
            asr_url,
            step_callback=send_sub_step,
            persist_video=persist_video and not need_separate_video_download
        )

        local_video_url = None
        update_dict = {
            "messages": [ToolMessage(
                content=f"视频转录完成，共 {len(result.text)} 字",
                tool_call_id=runtime.tool_call_id
            )],
            # 保存完整的 transcript 结构（包含 text、segments 和 content_id）
            "transcript": {
                "text": result.text,
                "segments": result.segments,
                "content_id": content_info.get("content_id"),  # 用于缓存验证
            },
            "current_stage": "视频转录完成",
        }

        # 持久化视频和生成元数据
        if persist_video and (result.video_path or need_separate_video_download):
            from services.asset_storage import AssetStorageService, AssetStorageError
            from services.video_downloader import VideoDownloader

            platform = content_info.get("platform", "unknown")
            # 处理枚举类型：Platform.BILIBILI -> bilibili
            if hasattr(platform, 'value'):
                platform = platform.value
            elif isinstance(platform, str) and "." in platform:
                # 处理字符串形式的枚举，如 "Platform.BILIBILI"
                platform = platform.split(".")[-1].lower()
            content_id = content_info.get("content_id", "unknown")

            asset_service = AssetStorageService()
            downloader = VideoDownloader()
            video_task_id = None

            try:
                # 持久化视频
                if need_separate_video_download:
                    # B站情况：需要下载视频流和音频流，然后合并
                    from services.video_merger import VideoMerger, VideoMergeError

                    logger.info(f"B站视频：下载并合并视频音频流...")
                    await send_sub_step("start", "merge_bilibili", t("progress.mergeBilibili"))

                    video_task_id = str(uuid.uuid4())
                    merger = VideoMerger()

                    try:
                        # 下载视频和音频流，然后合并
                        merged_video_path = await merger.download_and_merge_bilibili(
                            video_url=video_url,
                            audio_url=audio_url,
                            output_path=str(downloader.get_task_dir(video_task_id) / "merged.mp4"),
                            task_id=video_task_id,
                            timeout=300
                        )
                        logger.info(f"B站视频合并完成: {merged_video_path}")

                        await send_sub_step("end", "merge_bilibili", t("progress.mergeComplete"))

                        # 持久化合并后的视频
                        local_video_url = await asset_service.persist_video(
                            merged_video_path,
                            platform,
                            content_id
                        )
                    except VideoMergeError as e:
                        logger.warning(f"B站视频合并失败: {e}，尝试只保存视频流")
                        await send_sub_step("end", "merge_bilibili", t("progress.mergeFailed", error=str(e)))

                        # 回退：只下载视频流（无音频）
                        video_task_id = str(uuid.uuid4())
                        video_path = await downloader.download(video_url, video_task_id)
                        local_video_url = await asset_service.persist_video(
                            video_path,
                            platform,
                            content_id
                        )
                elif result.video_path:
                    # 其他平台：直接持久化 ASR 下载的文件（包含音视频）
                    local_video_url = await asset_service.persist_video(
                        result.video_path,
                        platform,
                        content_id
                    )

                if local_video_url:
                    logger.info(f"Video persisted to: {local_video_url}")

                # 处理 content_type 枚举
                content_type = content_info.get("content_type", "video")
                if hasattr(content_type, 'value'):
                    content_type = content_type.value
                elif isinstance(content_type, str) and "." in content_type:
                    content_type = content_type.split(".")[-1].lower()

                # 生成元数据文件（包含完整视频信息）
                asset_service.generate_metadata(
                    platform=platform,
                    content_id=content_id,
                    title=content_info.get("title", ""),
                    desc=content_info.get("desc", ""),
                    author_name=content_info.get("author_name", ""),
                    author_id=content_info.get("author_id", ""),
                    publish_time=content_info.get("publish_time"),
                    duration=content_info.get("duration"),
                    content_type=content_type,
                    tags=content_info.get("tags"),
                    transcript=result.text,
                    # 互动数据
                    like_count=content_info.get("like_count", 0),
                    comment_count=content_info.get("comment_count", 0),
                    share_count=content_info.get("share_count", 0),
                    collect_count=content_info.get("collect_count", 0),
                    view_count=content_info.get("view_count", 0),
                    danmaku_count=content_info.get("danmaku_count", 0),
                    # 原始媒体 URL
                    cover_url=content_info.get("cover_url", ""),
                    video_url=content_info.get("video_url", ""),
                    audio_url=content_info.get("audio_url", ""),
                    image_urls=content_info.get("image_urls"),
                    # 本地资源 URL
                    local_cover_url=content_info.get("local_cover_url", ""),
                    local_video_url=local_video_url,
                )

                # 更新 content_info 中的 local_video_url
                # 需要将 local_video_url 合并到 content_info 中，因为前端从 content_info 获取
                updated_content_info = dict(content_info)
                updated_content_info["local_video_url"] = local_video_url
                update_dict["content_info"] = updated_content_info

            except AssetStorageError as e:
                logger.warning(f"Failed to persist video: {e}")
            finally:
                # 清理临时文件（持久化后）
                if result.task_id:
                    try:
                        downloader.cleanup(result.task_id)
                    except Exception as e:
                        logger.warning(f"Cleanup ASR temp files failed: {e}")
                # 清理合并/下载的视频临时文件
                if video_task_id:
                    try:
                        downloader.cleanup(video_task_id)
                    except Exception as e:
                        logger.warning(f"Cleanup video temp files failed: {e}")

        # 发送 content_info 事件（供前端展示卡片，包含 local_video_url）
        # 使用更新后的 content_info（如果有），否则使用原始的
        final_content_info = update_dict.get("content_info", content_info)
        await adispatch_custom_event(
            "content_info",
            {"content_info": dict(final_content_info)},
        )

        # 发送 transcript 事件（供前端立即展示字幕，不必等到 done 事件）
        await adispatch_custom_event(
            "transcript",
            {
                "transcript": {
                    "text": result.text,
                    "segments": result.segments,
                    "content_id": content_info.get("content_id"),  # 用于缓存验证
                }
            },
        )

        return Command(update=update_dict)

    except RemixToolException as e:
        error_message = build_tool_user_message(e)
        return Command(update={
            "messages": [ToolMessage(content=error_message, tool_call_id=runtime.tool_call_id)],
            "current_stage": "视频处理失败",
        })
    except Exception as e:
        tool_error = RemixToolException(
            RemixErrorCode.INTERNAL_ERROR,
            t("progress.videoProcessFailed", error=str(e)),
            {"video_url": video_url},
        )
        error_message = build_tool_user_message(tool_error)
        return Command(update={
            "messages": [ToolMessage(content=error_message, tool_call_id=runtime.tool_call_id)],
            "current_stage": "视频处理失败",
        })
