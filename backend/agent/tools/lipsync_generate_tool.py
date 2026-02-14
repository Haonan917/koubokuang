# -*- coding: utf-8 -*-
"""唇形同步工具 - 支持上传音频/TTS/录音来源"""

from pathlib import Path
from typing import List, Literal, Optional

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agent.errors import RemixErrorCode, RemixToolException, build_tool_user_message
from agent.state import RemixContext
from config import settings
from i18n import t
from services.media_ai_source_service import MediaAISourceService, MediaSourceError
from services.syncso_client import SyncsoClient, SyncsoClientError
from services.tts_expression_service import build_expressive_tts_text_async
from services.tts_tag_service import TTSTagError
from services.voicv_client import VoicvClient, VoicvClientError
from services.voice_style_profile_store import VoiceStyleProfileStore
from services.media_ai_store import MediaAIStore


def _resolve_video_url(runtime: ToolRuntime[RemixContext], explicit_url: Optional[str]) -> str:
    if explicit_url:
        return explicit_url
    preferred_avatar_url = getattr(runtime.context, "preferred_avatar_url", None)
    if preferred_avatar_url:
        return preferred_avatar_url
    content_info = runtime.state.get("content_info") or {}
    return content_info.get("local_video_url") or content_info.get("video_url") or ""


def _resolve_tts_audio_url(runtime: ToolRuntime[RemixContext]) -> str:
    tts_result = runtime.state.get("tts_result") or {}
    return tts_result.get("audio_url") or ""


def _resolve_voice_id(runtime: ToolRuntime[RemixContext], voice_id: Optional[str]) -> Optional[str]:
    if voice_id:
        return voice_id
    preferred = getattr(runtime.context, "preferred_voice_id", None)
    if preferred:
        return preferred
    cloned_voice = runtime.state.get("cloned_voice") or {}
    return cloned_voice.get("voice_id")


def _resolve_voice_profile(
    runtime: ToolRuntime[RemixContext],
    selected_voice_id: str,
    use_voice_profile: bool,
) -> Optional[dict]:
    if not use_voice_profile:
        return None

    cloned_voice = runtime.state.get("cloned_voice") or {}
    if cloned_voice.get("voice_id") == selected_voice_id and isinstance(cloned_voice.get("expression_profile"), dict):
        return cloned_voice.get("expression_profile")

    store = VoiceStyleProfileStore()
    return store.get(selected_voice_id)


@tool
async def lipsync_generate(
    runtime: ToolRuntime[RemixContext],
    video_source_type: Literal["content_video", "upload"] = "content_video",
    video_url: Optional[str] = None,
    audio_source_type: Literal["tts", "upload", "recording"] = "tts",
    audio_url: Optional[str] = None,
    script_text: Optional[str] = None,
    voice_id: Optional[str] = None,
    emotion: Optional[str] = None,
    tone_tags: Optional[List[str]] = None,
    effect_tags: Optional[List[str]] = None,
    auto_emotion: Optional[bool] = None,
    auto_breaks: Optional[bool] = None,
    use_voice_profile: bool = True,
    model: str = "lipsync-2",
) -> Command:
    """
    创建 lipsync 生成任务。

    支持：
    - 视频来源：当前内容视频 / 上传视频 URL
    - 音频来源：TTS / 上传音频 URL / 录音 URL
    - script_text + voice_id（或最近 cloned_voice）自动先做 TTS 再做 lipsync
    - script 模式可选 emotion / tone_tags / effect_tags 增强自然度
    - 可选 auto_emotion / auto_breaks / use_voice_profile 控制表达习惯（auto_breaks 为长句句内语气/音效/停顿增强）
    """
    runtime.stream_writer({"stage": "lipsync_generating", "message": t("progress.generatingLipsync")})

    source_service = MediaAISourceService()

    try:
        # 1) 解析视频来源
        effective_video_url = _resolve_video_url(runtime, video_url)
        if video_source_type == "upload" and not effective_video_url:
            raise RemixToolException(RemixErrorCode.LIPSYNC_FAILED, t("errors.lipsyncVideoMissing"))
        if video_source_type == "content_video" and not effective_video_url:
            raise RemixToolException(RemixErrorCode.LIPSYNC_FAILED, t("errors.lipsyncVideoMissing"))

        # 2) 解析音频来源（可选先做 TTS）
        effective_audio_url = audio_url
        effective_audio_source_type = audio_source_type

        if script_text and script_text.strip():
            selected_voice_id = _resolve_voice_id(runtime, voice_id)
            if not selected_voice_id:
                raise RemixToolException(RemixErrorCode.TTS_FAILED, t("errors.ttsVoiceMissing"))
            voice_profile = _resolve_voice_profile(runtime, selected_voice_id, use_voice_profile)
            normalized = await build_expressive_tts_text_async(
                script_text.strip(),
                emotion=emotion,
                tone_tags=tone_tags,
                effect_tags=effect_tags,
                auto_emotion=auto_emotion,
                auto_breaks=auto_breaks,
                voice_profile=voice_profile,
                tag_strategy="llm",
                speech_style="speech",
            )
            tts_client = VoicvClient()
            tts_result = await tts_client.text_to_speech(
                voice_id=selected_voice_id,
                text=normalized["text"],
                audio_format="mp3",
            )
            tts_audio_url = tts_result["audio_url"]
            speed = float(settings.TTS_AUDIO_SPEED)
            if abs(speed - 1.0) > 1e-6:
                downloaded_bytes, guessed_name, _ = await source_service.download_bytes(
                    tts_audio_url,
                    max_bytes=max(settings.VOICE_CLONE_MAX_AUDIO_BYTES, 50 * 1024 * 1024),
                )
                input_ext = Path(guessed_name).suffix or ".mp3"
                speed_bytes, speed_name, speed_content_type = source_service.change_audio_speed(
                    downloaded_bytes,
                    input_ext=input_ext,
                    speed=speed,
                    output_ext=".mp3",
                )
                speed_asset = source_service.persist_bytes(
                    speed_bytes,
                    prefix="tts_speed",
                    ext=Path(speed_name).suffix or ".mp3",
                    content_type=speed_content_type,
                )
                effective_audio_url = speed_asset["url"]
            else:
                effective_audio_url = tts_audio_url
            effective_audio_source_type = "tts"

        if effective_audio_source_type == "tts" and not effective_audio_url:
            effective_audio_url = _resolve_tts_audio_url(runtime)
        if not effective_audio_url:
            raise RemixToolException(RemixErrorCode.LIPSYNC_FAILED, t("errors.lipsyncAudioMissing"))

        # 3) 下载素材，调用 Sync.so
        video_bytes, video_name, video_content_type = await source_service.download_bytes(
            effective_video_url,
            max_bytes=300 * 1024 * 1024,
        )
        audio_bytes, audio_name, audio_content_type = await source_service.download_bytes(
            effective_audio_url,
            max_bytes=50 * 1024 * 1024,
        )

        if Path(video_name).suffix == "":
            video_name = "input_video.mp4"
        if Path(audio_name).suffix == "":
            audio_name = "input_audio.mp3"

        sync_client = SyncsoClient()
        generation = await sync_client.create_generation(
            video_bytes=video_bytes,
            video_filename=video_name,
            video_content_type=video_content_type,
            audio_bytes=audio_bytes,
            audio_filename=audio_name,
            audio_content_type=audio_content_type,
            model=model,
        )

        lipsync_result = {
            "generation_id": generation.get("generation_id"),
            "model": model,
            "status": generation.get("status", "PENDING"),
            "output_url": generation.get("output_url", ""),
            "video_source_type": video_source_type,
            "audio_source_type": effective_audio_source_type,
            "video_url": effective_video_url,
            "audio_url": effective_audio_url,
        }

        runtime.stream_writer({
            "stage": "lipsync_generating",
            "message": t("progress.lipsyncComplete"),
            "result": lipsync_result,
        })

        result_text = (
            "Lipsync 任务已创建\n\n"
            f"- generation_id: {lipsync_result.get('generation_id')}\n"
            f"- status: {lipsync_result.get('status')}\n"
            f"- output_url: {lipsync_result.get('output_url') or '-'}"
        )

        user_id = getattr(runtime.context, "user_id", None)
        if user_id:
            store = MediaAIStore()
            await store.upsert_lipsync_result(user_id, lipsync_result)

        return Command(update={
            "messages": [ToolMessage(content=result_text, tool_call_id=runtime.tool_call_id)],
            "lipsync_result": lipsync_result,
            "current_stage": "Lipsync 任务创建完成",
        })
    except (MediaSourceError, SyncsoClientError, VoicvClientError, TTSTagError) as e:
        error = RemixToolException(RemixErrorCode.LIPSYNC_FAILED, t("errors.lipsyncFailed"), {"detail": str(e)})
        return Command(update={
            "messages": [ToolMessage(content=build_tool_user_message(error), tool_call_id=runtime.tool_call_id)],
            "current_stage": "Lipsync 生成失败",
        })
    except RemixToolException as e:
        return Command(update={
            "messages": [ToolMessage(content=build_tool_user_message(e), tool_call_id=runtime.tool_call_id)],
            "current_stage": "Lipsync 生成失败",
        })
