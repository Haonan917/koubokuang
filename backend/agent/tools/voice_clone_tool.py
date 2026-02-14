# -*- coding: utf-8 -*-
"""语音克隆工具 - 支持上传/录音/视频前30秒三种来源"""

from pathlib import Path
from typing import List, Literal, Optional
from urllib.parse import urlparse

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agent.errors import RemixErrorCode, RemixToolException, build_tool_user_message
from agent.state import RemixContext
from config import settings
from i18n import t
from services.download_server_client import (
    DownloadServerClient,
    DownloadServerError,
    ContentNotFoundError,
    CookiesNotFoundError,
)
from services.media_ai_source_service import MediaAISourceService, MediaSourceError
from services.tts_tag_service import TTSTagError, normalize_effect_tags, normalize_tone_tags
from services.voicv_client import VoicvClient, VoicvClientError
from services.voice_style_profile_store import VoiceStyleProfileStore


def _resolve_content_media_url(runtime: ToolRuntime[RemixContext]) -> str:
    content_info = runtime.state.get("content_info") or {}
    return (
        content_info.get("audio_url")
        or content_info.get("local_video_url")
        or content_info.get("video_url")
        or ""
    )


def _looks_like_direct_media_url(url: str) -> bool:
    if not url:
        return False
    url_lower = url.strip().lower()
    if url_lower.startswith("/media/"):
        return True
    parsed = urlparse(url_lower)
    path = parsed.path or url_lower
    if path.startswith("/media/"):
        return True
    media_ext = (
        ".mp4", ".mov", ".mkv", ".avi", ".wmv", ".m3u8", ".flv", ".webm", ".m4s",
        ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".opus",
    )
    if path.endswith(media_ext):
        return True
    return any(hint in url_lower for hint in ("xhscdn", "douyinvod", "bilivideo", "mcdn.bilivideo", "kwaicdn"))


async def _resolve_page_url_to_media(url: str) -> str:
    """将平台页面链接解析为可下载媒体链接（audio/video）"""
    if _looks_like_direct_media_url(url):
        return url

    client = DownloadServerClient()
    try:
        content = await client.fetch_content(url)
        if content.audio_url:
            return content.audio_url
        if content.video_url:
            return content.video_url
        raise MediaSourceError("页面链接解析成功，但未找到可下载音频/视频流")
    except CookiesNotFoundError as e:
        raise MediaSourceError(f"未配置平台 Cookies，无法解析页面链接: {e}")
    except ContentNotFoundError as e:
        raise MediaSourceError(f"内容不存在或已失效: {e}")
    except DownloadServerError as e:
        raise MediaSourceError(f"页面链接解析失败: {e}")


@tool
async def voice_clone(
    runtime: ToolRuntime[RemixContext],
    source_type: Literal["upload", "recording", "content_video"] = "content_video",
    source_url: Optional[str] = None,
    title: str = "Untitled",
    description: str = "",
    start_seconds: int = 0,
    duration_seconds: int = 30,
    auto_emotion: bool = True,
    auto_breaks: bool = True,
    tone_tags: Optional[List[str]] = None,
    effect_tags: Optional[List[str]] = None,
) -> Command:
    """
    语音克隆工具。

    Args:
        source_type: 声音来源类型
            - upload: 用户上传音频 URL
            - recording: 在线录音文件 URL
            - content_video: 从当前内容视频/音频截取片段
        source_url: 上传/录音来源 URL（upload/recording 必填）
        title: 声音标题
        description: 声音描述
        start_seconds: 截取起始秒（默认 0）
        duration_seconds: 截取时长秒（默认 30）
        auto_emotion: 是否启用逐句自动情绪识别（保存为 voice 表达习惯）
        auto_breaks: 是否启用长句句内表达增强（语气/音效/停顿，保存为 voice 表达习惯）
        tone_tags/effect_tags: 该 voice 的默认语气/音效标签模板
    """
    runtime.stream_writer({"stage": "voice_cloning", "message": t("progress.cloningVoice")})

    source_service = MediaAISourceService()

    try:
        effective_source_url = source_url
        if source_type == "content_video":
            effective_source_url = effective_source_url or _resolve_content_media_url(runtime)
        if not effective_source_url:
            raise RemixToolException(
                RemixErrorCode.VOICE_CLONE_FAILED,
                t("errors.voiceCloneSourceMissing"),
                {"source_type": source_type},
            )
        if source_type == "content_video":
            effective_source_url = await _resolve_page_url_to_media(effective_source_url)

        max_download = settings.VOICE_CLONE_MAX_AUDIO_BYTES
        if source_type == "content_video":
            max_download = max(max_download, settings.VOICE_CLONE_MAX_SOURCE_BYTES)

        raw_bytes, guessed_name, content_type = await source_service.download_bytes(
            effective_source_url,
            max_bytes=max_download,
        )

        filename = guessed_name
        voice_bytes = raw_bytes
        voice_content_type = content_type
        full_audio_asset = None
        clip_audio_asset = None

        if source_type == "content_video":
            clip_seconds = duration_seconds or settings.VOICE_SOURCE_DEFAULT_CLIP_SECONDS
            full_audio_bytes, _, full_content_type = source_service.extract_audio_to_wav(
                input_bytes=raw_bytes,
                input_ext=Path(guessed_name).suffix or ".bin",
            )
            full_audio_asset = source_service.persist_bytes(
                full_audio_bytes,
                prefix="voice_full",
                ext=".wav",
                content_type=full_content_type,
            )
            voice_bytes, filename, voice_content_type = source_service.trim_audio_clip(
                input_bytes=full_audio_bytes,
                input_ext=".wav",
                start_seconds=start_seconds,
                duration_seconds=clip_seconds,
            )
            clip_audio_asset = source_service.persist_bytes(
                voice_bytes,
                prefix="voice_clip",
                ext=".wav",
                content_type=voice_content_type,
            )
        else:
            ext = Path(filename).suffix or ".bin"
            full_audio_asset = source_service.persist_bytes(
                voice_bytes,
                prefix="voice_full",
                ext=ext,
                content_type=voice_content_type,
            )
            # Voicv 仅接受 MP3/WAV，录音常见 webm/ogg/mp4 需先转码
            normalized_ext = (Path(filename).suffix or "").lower()
            if normalized_ext not in {".mp3", ".wav"}:
                voice_bytes, _, voice_content_type = source_service.extract_audio_to_wav(
                    input_bytes=voice_bytes,
                    input_ext=normalized_ext or ".bin",
                )
                filename = "voice.wav"

        voicv_client = VoicvClient()
        clone_result = await voicv_client.clone_voice(
            audio_bytes=voice_bytes,
            filename=filename,
            content_type=voice_content_type,
        )

        cloned_voice = {
            "voice_id": clone_result["voice_id"],
            "title": title,
            "description": description,
            "source_type": source_type,
            "source_audio_url": effective_source_url,
            "sample_audio_url": clone_result.get("sample_audio_url", ""),
            "cost_credits": clone_result.get("cost_credits"),
            "clip_start_seconds": start_seconds if source_type == "content_video" else None,
            "clip_duration_seconds": duration_seconds if source_type == "content_video" else None,
            "full_audio_url": full_audio_asset["url"] if full_audio_asset else "",
            "clip_audio_url": clip_audio_asset["url"] if clip_audio_asset else "",
        }

        style_profile_store = VoiceStyleProfileStore()
        expression_profile = style_profile_store.upsert(
            clone_result["voice_id"],
            {
                "auto_emotion": auto_emotion,
                "auto_breaks": auto_breaks,
                "tone_tags": normalize_tone_tags(tone_tags or []),
                "effect_tags": normalize_effect_tags(effect_tags or []),
            },
        )
        cloned_voice["expression_profile"] = expression_profile

        runtime.stream_writer({
            "stage": "voice_cloning",
            "message": t("progress.cloneVoiceComplete", voice_id=clone_result["voice_id"]),
            "result": {
                "voice_id": clone_result["voice_id"],
                "source_type": source_type,
                "sample_audio_url": clone_result.get("sample_audio_url", ""),
            },
        })

        result_text = (
            "语音克隆成功\n\n"
            f"- voice_id: {clone_result['voice_id']}\n"
            f"- source_type: {source_type}\n"
            f"- expression_profile: {expression_profile}\n"
            f"- full_audio_url: {cloned_voice.get('full_audio_url') or '-'}\n"
            f"- clip_audio_url: {cloned_voice.get('clip_audio_url') or '-'}\n"
            f"- sample_audio_url: {clone_result.get('sample_audio_url') or '-'}"
        )

        return Command(update={
            "messages": [ToolMessage(content=result_text, tool_call_id=runtime.tool_call_id)],
            "cloned_voice": cloned_voice,
            "current_stage": "语音克隆完成",
        })
    except (VoicvClientError, MediaSourceError, TTSTagError) as e:
        error = RemixToolException(
            RemixErrorCode.VOICE_CLONE_FAILED,
            t("errors.voiceCloneFailed"),
            {"detail": str(e), "source_type": source_type},
        )
        return Command(update={
            "messages": [ToolMessage(content=build_tool_user_message(error), tool_call_id=runtime.tool_call_id)],
            "current_stage": "语音克隆失败",
        })
    except RemixToolException as e:
        return Command(update={
            "messages": [ToolMessage(content=build_tool_user_message(e), tool_call_id=runtime.tool_call_id)],
            "current_stage": "语音克隆失败",
        })
