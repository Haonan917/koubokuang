# -*- coding: utf-8 -*-
"""文本转语音工具 - 使用指定音色或克隆音色"""

from pathlib import Path
from typing import List, Optional

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agent.errors import RemixErrorCode, RemixToolException, build_tool_user_message
from agent.state import RemixContext
from config import settings
from i18n import t
from services.media_ai_source_service import MediaAISourceService, MediaSourceError
from services.tts_expression_service import build_expressive_tts_text_async
from services.tts_tag_service import TTSTagError
from services.voicv_client import VoicvClient, VoicvClientError
from services.voice_style_profile_store import VoiceStyleProfileStore
from services.media_ai_store import MediaAIStore


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
async def text_to_speech(
    runtime: ToolRuntime[RemixContext],
    text: str,
    voice_id: Optional[str] = None,
    audio_format: str = "mp3",
    emotion: Optional[str] = None,
    tone_tags: Optional[List[str]] = None,
    effect_tags: Optional[List[str]] = None,
    auto_emotion: Optional[bool] = None,
    auto_breaks: Optional[bool] = None,
    use_voice_profile: bool = True,
) -> Command:
    """将文本转换为语音。未传 voice_id 时自动使用最近一次克隆音色。

    支持基于 voice 表达习惯模板做逐句情绪识别与长句句内语气/音效增强。
    """
    runtime.stream_writer({"stage": "tts_generating", "message": t("progress.generatingTts")})

    try:
        selected_voice_id = _resolve_voice_id(runtime, voice_id)
        if not selected_voice_id:
            raise RemixToolException(
                RemixErrorCode.TTS_FAILED,
                t("errors.ttsVoiceMissing"),
                {"hint": "请先调用 voice_clone 或显式传入 voice_id"},
            )

        if not text or not text.strip():
            raise RemixToolException(
                RemixErrorCode.TTS_FAILED,
                t("errors.ttsTextMissing"),
            )

        voice_profile = _resolve_voice_profile(runtime, selected_voice_id, use_voice_profile)
        normalized = await build_expressive_tts_text_async(
            text.strip(),
            emotion=emotion,
            tone_tags=tone_tags,
            effect_tags=effect_tags,
            auto_emotion=auto_emotion,
            auto_breaks=auto_breaks,
            voice_profile=voice_profile,
            tag_strategy="llm",
            speech_style="speech",
        )

        client = VoicvClient()
        result = await client.text_to_speech(
            voice_id=selected_voice_id,
            text=normalized["text"],
            audio_format=audio_format,
        )
        final_audio_url = result["audio_url"]
        speed = float(settings.TTS_AUDIO_SPEED)

        if abs(speed - 1.0) > 1e-6:
            source_svc = MediaAISourceService()
            downloaded_bytes, guessed_name, _ = await source_svc.download_bytes(
                final_audio_url,
                max_bytes=max(settings.VOICE_CLONE_MAX_AUDIO_BYTES, 50 * 1024 * 1024),
            )
            input_ext = Path(guessed_name).suffix or f".{audio_format}"
            output_ext = f".{audio_format}"
            speed_bytes, speed_name, speed_content_type = source_svc.change_audio_speed(
                downloaded_bytes,
                input_ext=input_ext,
                speed=speed,
                output_ext=output_ext,
            )
            speed_asset = source_svc.persist_bytes(
                speed_bytes,
                prefix="tts_speed",
                ext=Path(speed_name).suffix or output_ext,
                content_type=speed_content_type,
            )
            result["original_audio_url"] = final_audio_url
            final_audio_url = speed_asset["url"]

        tts_result = {
            "voice_id": selected_voice_id,
            "text": normalized["text"],
            "format": audio_format,
            "audio_url": final_audio_url,
            "speed": speed,
            "original_audio_url": result.get("original_audio_url"),
            "emotion": normalized["emotion"],
            "tone_tags": normalized["tone_tags"],
            "effect_tags": normalized["effect_tags"],
            "sentence_emotions": normalized["sentence_emotions"],
            "tagged_text": normalized["tagged_text"],
            "auto_emotion": normalized["auto_emotion"],
            "auto_breaks": normalized["auto_breaks"],
            "voice_profile": voice_profile,
        }

        runtime.stream_writer({
            "stage": "tts_generating",
            "message": t("progress.ttsComplete"),
            "result": {
                "voice_id": selected_voice_id,
                "audio_url": final_audio_url,
                "speed": speed,
            },
        })

        user_id = getattr(runtime.context, "user_id", None)
        if user_id:
            store = MediaAIStore()
            await store.insert_tts_result(user_id, tts_result)

        result_text = (
            "TTS 生成成功\n\n"
            f"- voice_id: {selected_voice_id}\n"
            f"- format: {audio_format}\n"
            f"- speed: {speed}\n"
            f"- emotion: {normalized['emotion'] or '-'}\n"
            f"- auto_emotion: {normalized['auto_emotion']}\n"
            f"- auto_breaks: {normalized['auto_breaks']}\n"
            f"- tone_tags: {', '.join(normalized['tone_tags']) if normalized['tone_tags'] else '-'}\n"
            f"- effect_tags: {', '.join(normalized['effect_tags']) if normalized['effect_tags'] else '-'}\n"
            f"- tagged_text_preview: {normalized['tagged_text'][:120]}{'...' if len(normalized['tagged_text']) > 120 else ''}\n"
            f"- audio_url: {final_audio_url}"
        )

        return Command(update={
            "messages": [ToolMessage(content=result_text, tool_call_id=runtime.tool_call_id)],
            "tts_result": tts_result,
            "current_stage": "TTS 生成完成",
        })
    except (VoicvClientError, MediaSourceError, TTSTagError) as e:
        error = RemixToolException(RemixErrorCode.TTS_FAILED, t("errors.ttsFailed"), {"detail": str(e)})
        return Command(update={
            "messages": [ToolMessage(content=build_tool_user_message(error), tool_call_id=runtime.tool_call_id)],
            "current_stage": "TTS 生成失败",
        })
    except RemixToolException as e:
        return Command(update={
            "messages": [ToolMessage(content=build_tool_user_message(e), tool_call_id=runtime.tool_call_id)],
            "current_stage": "TTS 生成失败",
        })
