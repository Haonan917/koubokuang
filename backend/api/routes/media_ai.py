# -*- coding: utf-8 -*-
"""Media AI API - 上传媒体 + VoiceClone/TTS/Lipsync"""

import json
import uuid
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends, Query
from pydantic import BaseModel, Field

from config import settings
from services.download_server_client import (
    DownloadServerClient,
    DownloadServerError,
    ContentNotFoundError,
    CookiesNotFoundError,
)
from services.media_ai_source_service import MediaAISourceService, MediaSourceError
from services.media_ai_store import MediaAIStore
from services.syncso_client import SyncsoClient, SyncsoClientError
from services.tts_expression_service import build_expressive_tts_text_async
from services.tts_tag_service import TTSTagError, normalize_effect_tags, normalize_tone_tags
from services.voicv_client import VoicvClient, VoicvClientError
from services.voice_style_profile_store import VoiceStyleProfileStore
from services.auth_service import User
from api.dependencies import get_current_user_optional
from utils.logger import logger


router = APIRouter()


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
    cdn_hints = (
        "xhscdn",
        "douyinvod",
        "bilivideo",
        "mcdn.bilivideo",
        "kwaicdn",
    )
    return any(hint in url_lower for hint in cdn_hints)


async def _resolve_content_media_url(page_or_media_url: str) -> str:
    """
    输入页面链接或媒体链接，返回可下载媒体 URL。
    页面链接会通过 DownloadServer 自动解析到 audio_url/video_url。
    """
    normalized_url = (page_or_media_url or "").strip()
    if _looks_like_direct_media_url(normalized_url):
        return normalized_url

    parsed = urlparse(normalized_url)
    if normalized_url and not parsed.scheme and not normalized_url.startswith("/"):
        normalized_url = f"https://{normalized_url}"

    if _looks_like_direct_media_url(normalized_url):
        return normalized_url

    client = DownloadServerClient()
    try:
        content = await client.fetch_content(normalized_url)
        if content.audio_url:
            logger.info(f"[media-ai] Resolved page URL to audio stream: {content.audio_url[:120]}")
            return content.audio_url
        if content.video_url:
            logger.info(f"[media-ai] Resolved page URL to video stream: {content.video_url[:120]}")
            return content.video_url
        logger.warning(f"[media-ai] No downloadable media found for url={normalized_url}")
        raise HTTPException(status_code=400, detail="页面链接解析成功，但未找到可下载音频/视频流")
    except CookiesNotFoundError as e:
        logger.warning(f"[media-ai] Cookies missing for url={normalized_url}: {e}")
        raise HTTPException(status_code=400, detail=f"未配置平台 Cookies，无法解析页面链接: {e}")
    except ContentNotFoundError as e:
        logger.warning(f"[media-ai] Content not found for url={normalized_url}: {e}")
        raise HTTPException(status_code=400, detail=f"内容不存在或已失效: {e}")
    except DownloadServerError as e:
        logger.warning(f"[media-ai] DownloadServer resolve failed for url={normalized_url}: {e}")
        raise HTTPException(status_code=400, detail=f"页面链接解析失败: {e}")


async def _resolve_content_video_url(page_or_media_url: str) -> str:
    """
    输入页面链接或媒体链接，返回可下载视频 URL。
    页面链接会通过 DownloadServer 自动解析到 video_url。
    """
    normalized_url = (page_or_media_url or "").strip()
    if _looks_like_direct_media_url(normalized_url):
        return normalized_url

    parsed = urlparse(normalized_url)
    if normalized_url and not parsed.scheme and not normalized_url.startswith("/"):
        normalized_url = f"https://{normalized_url}"

    if _looks_like_direct_media_url(normalized_url):
        return normalized_url

    client = DownloadServerClient()
    try:
        content = await client.fetch_content(normalized_url)
        if content.video_url:
            logger.info(f"[media-ai] Resolved page URL to video stream: {content.video_url[:120]}")
            return content.video_url
        logger.warning(f"[media-ai] No downloadable video found for url={normalized_url}")
        raise HTTPException(status_code=400, detail="页面链接解析成功，但未找到可下载视频流")
    except CookiesNotFoundError as e:
        logger.warning(f"[media-ai] Cookies missing for url={normalized_url}: {e}")
        raise HTTPException(status_code=400, detail=f"未配置平台 Cookies，无法解析页面链接: {e}")
    except ContentNotFoundError as e:
        logger.warning(f"[media-ai] Content not found for url={normalized_url}: {e}")
        raise HTTPException(status_code=400, detail=f"内容不存在或已失效: {e}")
    except DownloadServerError as e:
        logger.warning(f"[media-ai] DownloadServer resolve failed for url={normalized_url}: {e}")
        raise HTTPException(status_code=400, detail=f"页面链接解析失败: {e}")


class TTSRequest(BaseModel):
    voice_id: str = Field(..., description="Voicv voiceId")
    text: str = Field(..., min_length=1)
    audio_format: str = Field(default="mp3")
    speed: Optional[float] = Field(default=None, gt=0, le=4, description="语速倍率，默认使用系统配置")
    emotion: Optional[str] = Field(default=None, description="情绪标签，例如 (happy)")
    tone_tags: List[str] = Field(default_factory=list, description="语气标签列表")
    effect_tags: List[str] = Field(default_factory=list, description="音效标签列表")
    auto_emotion: Optional[bool] = Field(default=None, description="是否按句自动识别情绪")
    auto_breaks: Optional[bool] = Field(default=None, description="是否自动在长句句内添加语气/音效/停顿标签")
    tag_strategy: Optional[str] = Field(default="llm", description="标签生成策略: llm/heuristic/none")
    speech_style: Optional[str] = Field(default="speech", description="语体风格: speech/neutral")
    use_voice_profile: bool = Field(default=True, description="是否叠加 voice 的表达习惯模板")


class TTSPreviewRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice_id: Optional[str] = Field(default=None)
    emotion: Optional[str] = Field(default=None, description="情绪标签，例如 (happy)")
    tone_tags: List[str] = Field(default_factory=list, description="语气标签列表")
    effect_tags: List[str] = Field(default_factory=list, description="音效标签列表")
    auto_emotion: Optional[bool] = Field(default=None, description="是否按句自动识别情绪")
    auto_breaks: Optional[bool] = Field(default=None, description="是否自动在长句句内添加语气/音效/停顿标签")
    tag_strategy: Optional[str] = Field(default="llm", description="标签生成策略: llm/heuristic/none")
    speech_style: Optional[str] = Field(default="speech", description="语体风格: speech/neutral")
    use_voice_profile: bool = Field(default=True, description="是否叠加 voice 的表达习惯模板")


class LipsyncRequest(BaseModel):
    video_url: str
    audio_url: str
    model: str = "lipsync-2"


def _parse_tags_form(raw: Optional[str]) -> List[str]:
    value = (raw or "").strip()
    if not value:
        return []
    if value.startswith("["):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"标签列表 JSON 解析失败: {e}")
        if not isinstance(parsed, list):
            raise HTTPException(status_code=400, detail="标签列表必须是数组")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


@router.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """上传音频文件（包含在线录音 blob）并返回可访问 URL"""
    try:
        svc = MediaAISourceService()
        result = await svc.save_upload(file, kind="audio")
        return {"success": True, "data": result}
    except MediaSourceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """上传视频文件并返回可访问 URL"""
    try:
        svc = MediaAISourceService()
        result = await svc.save_upload(file, kind="video")
        return {"success": True, "data": result}
    except MediaSourceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/voice-clone")
async def voice_clone(
    source_type: str = Form(default="upload"),  # upload / recording / content_video
    source_url: Optional[str] = Form(default=None),
    title: str = Form(default="Untitled"),
    description: str = Form(default=""),
    start_seconds: int = Form(default=0),
    duration_seconds: int = Form(default=30),
    auto_emotion: bool = Form(default=True),
    auto_breaks: bool = Form(default=True),
    tone_tags: str = Form(default=""),
    effect_tags: str = Form(default=""),
    file: Optional[UploadFile] = File(default=None),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    语音克隆 API：
    - source_type=upload/recording: 可以直接传 file，或传 source_url
    - source_type=content_video: 必须传 source_url（通常是视频 URL），将截取前30秒
    """
    try:
        svc = MediaAISourceService()
        voicv = VoicvClient()

        effective_source_url = source_url
        if file is not None:
            save_result = await svc.save_upload(file, kind="audio")
            effective_source_url = save_result["url"]

        if not effective_source_url:
            raise HTTPException(status_code=400, detail="source_url 或 file 至少提供一个")

        if source_type == "content_video":
            effective_source_url = await _resolve_content_media_url(effective_source_url)

        max_download = settings.VOICE_CLONE_MAX_AUDIO_BYTES
        if source_type == "content_video":
            max_download = max(max_download, settings.VOICE_CLONE_MAX_SOURCE_BYTES)

        raw_bytes, guessed_name, content_type = await svc.download_bytes(
            effective_source_url,
            max_bytes=max_download,
        )
        voice_bytes = raw_bytes
        voice_name = guessed_name
        voice_content_type = content_type
        full_audio_asset = None
        clip_audio_asset = None

        if source_type == "content_video":
            clip_seconds = duration_seconds or settings.VOICE_SOURCE_DEFAULT_CLIP_SECONDS
            # 先提取完整音轨并持久化，再裁剪片段并持久化
            full_audio_bytes, _, full_audio_content_type = svc.extract_audio_to_wav(
                input_bytes=raw_bytes,
                input_ext=Path(guessed_name).suffix or ".bin",
            )
            full_audio_asset = svc.persist_bytes(
                full_audio_bytes,
                prefix="voice_full",
                ext=".wav",
                content_type=full_audio_content_type,
            )

            voice_bytes, voice_name, voice_content_type = svc.trim_audio_clip(
                input_bytes=full_audio_bytes,
                input_ext=".wav",
                start_seconds=start_seconds,
                duration_seconds=clip_seconds,
            )
            clip_audio_asset = svc.persist_bytes(
                voice_bytes,
                prefix="voice_clip",
                ext=".wav",
                content_type=voice_content_type,
            )
        else:
            # 上传/录音来源同样持久化一份完整音频，便于复查和复用
            ext = Path(voice_name).suffix or ".bin"
            full_audio_asset = svc.persist_bytes(
                voice_bytes,
                prefix="voice_full",
                ext=ext,
                content_type=voice_content_type,
            )
            # Voicv 仅接受 MP3/WAV，录音常见 webm/ogg/mp4 需先转码
            normalized_ext = (Path(voice_name).suffix or "").lower()
            if normalized_ext not in {".mp3", ".wav"}:
                voice_bytes, _, voice_content_type = svc.extract_audio_to_wav(
                    input_bytes=voice_bytes,
                    input_ext=normalized_ext or ".bin",
                )
                voice_name = "voice.wav"

        result = await voicv.clone_voice(
            audio_bytes=voice_bytes,
            filename=voice_name,
            content_type=voice_content_type,
        )

        style_profile_store = VoiceStyleProfileStore()
        style_profile = style_profile_store.upsert(
            result["voice_id"],
            {
                "auto_emotion": auto_emotion,
                "auto_breaks": auto_breaks,
                "tone_tags": normalize_tone_tags(_parse_tags_form(tone_tags)),
                "effect_tags": normalize_effect_tags(_parse_tags_form(effect_tags)),
            },
        )

        response_payload = {
            "success": True,
            "data": {
                "voiceId": result["voice_id"],
                "sampleAudioUrl": result.get("sample_audio_url", ""),
                "costCredits": result.get("cost_credits"),
                "sourceType": source_type,
                "sourceUrl": effective_source_url,
                "title": title,
                "description": description,
                "fullAudioUrl": full_audio_asset["url"] if full_audio_asset else "",
                "fullAudioPath": full_audio_asset["path"] if full_audio_asset else "",
                "clipAudioUrl": clip_audio_asset["url"] if clip_audio_asset else "",
                "clipAudioPath": clip_audio_asset["path"] if clip_audio_asset else "",
                "expressionProfile": style_profile,
            },
        }
        user_id = current_user.user_id if current_user else None
        if user_id:
            store = MediaAIStore()
            await store.upsert_voice_clone(
                user_id,
                {
                    "voice_id": result["voice_id"],
                    "title": title,
                    "description": description,
                    "source_type": source_type,
                    "source_url": effective_source_url,
                    "sample_audio_url": result.get("sample_audio_url"),
                    "full_audio_url": full_audio_asset["url"] if full_audio_asset else "",
                    "full_audio_path": full_audio_asset["path"] if full_audio_asset else "",
                    "clip_audio_url": clip_audio_asset["url"] if clip_audio_asset else "",
                    "clip_audio_path": clip_audio_asset["path"] if clip_audio_asset else "",
                    "expression_profile": style_profile,
                },
            )
        return response_payload
    except HTTPException as e:
        logger.warning(f"[media-ai] /voice-clone HTTPException: detail={e.detail}")
        raise
    except VoicvClientError as e:
        logger.warning(f"voice-clone failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except TTSTagError as e:
        logger.warning(f"[media-ai] /voice-clone invalid style tags: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except MediaSourceError as e:
        logger.warning(f"[media-ai] /voice-clone MediaSourceError: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/avatar-clone")
async def avatar_clone(
    source_type: str = Form(default="upload"),  # upload / recording / content_video
    source_url: Optional[str] = Form(default=None),
    title: str = Form(default="Untitled"),
    description: str = Form(default=""),
    start_seconds: int = Form(default=0),
    duration_seconds: int = Form(default=30),
    file: Optional[UploadFile] = File(default=None),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    形象克隆 API：
    - source_type=upload/recording: 可以直接传 file，或传 source_url
    - source_type=content_video: 必须传 source_url（通常是视频 URL），将截取前30秒
    """
    try:
        svc = MediaAISourceService()

        effective_source_url = source_url
        if file is not None:
            save_result = await svc.save_upload(file, kind="video")
            effective_source_url = save_result["url"]

        if not effective_source_url:
            raise HTTPException(status_code=400, detail="source_url 或 file 至少提供一个")

        if source_type == "content_video":
            effective_source_url = await _resolve_content_video_url(effective_source_url)

        video_bytes, guessed_name, content_type = await svc.download_bytes(
            effective_source_url,
            max_bytes=settings.VOICE_CLONE_MAX_SOURCE_BYTES,
        )

        ext = Path(guessed_name).suffix or ".mp4"
        full_video_asset = svc.persist_bytes(
            video_bytes,
            prefix="avatar_full",
            ext=ext,
            content_type=content_type,
        )

        clip_video_asset = None
        if duration_seconds and duration_seconds > 0:
            clip_bytes, clip_name, clip_content_type = svc.trim_video_clip(
                input_bytes=video_bytes,
                input_ext=ext,
                start_seconds=start_seconds,
                duration_seconds=duration_seconds,
            )
            clip_video_asset = svc.persist_bytes(
                clip_bytes,
                prefix="avatar_clip",
                ext=Path(clip_name).suffix or ".mp4",
                content_type=clip_content_type,
            )

        avatar_id = uuid.uuid4().hex
        response_payload = {
            "success": True,
            "data": {
                "avatarId": avatar_id,
                "sourceType": source_type,
                "sourceUrl": effective_source_url,
                "title": title,
                "description": description,
                "fullVideoUrl": full_video_asset["url"] if full_video_asset else "",
                "fullVideoPath": full_video_asset["path"] if full_video_asset else "",
                "clipVideoUrl": clip_video_asset["url"] if clip_video_asset else "",
                "clipVideoPath": clip_video_asset["path"] if clip_video_asset else "",
            },
        }
        user_id = current_user.user_id if current_user else None
        if user_id:
            store = MediaAIStore()
            await store.upsert_avatar(
                user_id,
                {
                    "avatar_id": avatar_id,
                    "title": title,
                    "description": description,
                    "source_type": source_type,
                    "source_url": effective_source_url,
                    "full_video_url": full_video_asset["url"] if full_video_asset else "",
                    "full_video_path": full_video_asset["path"] if full_video_asset else "",
                    "clip_video_url": clip_video_asset["url"] if clip_video_asset else "",
                    "clip_video_path": clip_video_asset["path"] if clip_video_asset else "",
                },
            )
        return response_payload
    except HTTPException as e:
        logger.warning(f"[media-ai] /avatar-clone HTTPException: detail={e.detail}")
        raise
    except MediaSourceError as e:
        logger.warning(f"[media-ai] /avatar-clone MediaSourceError: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    try:
        client = VoicvClient()
        source_svc = MediaAISourceService()
        profile_store = VoiceStyleProfileStore()
        voice_profile = profile_store.get(request.voice_id) if request.use_voice_profile else None

        normalized = await build_expressive_tts_text_async(
            request.text,
            emotion=request.emotion,
            tone_tags=request.tone_tags,
            effect_tags=request.effect_tags,
            auto_emotion=request.auto_emotion,
            auto_breaks=request.auto_breaks,
            voice_profile=voice_profile,
            tag_strategy=request.tag_strategy or "llm",
            speech_style=request.speech_style or "speech",
        )
        result = await client.text_to_speech(
            voice_id=request.voice_id,
            text=normalized["text"],
            audio_format=request.audio_format,
        )

        final_audio_url = result["audio_url"]
        speed = float(request.speed if request.speed is not None else settings.TTS_AUDIO_SPEED)
        if abs(speed - 1.0) > 1e-6:
            downloaded_bytes, guessed_name, _ = await source_svc.download_bytes(
                final_audio_url,
                max_bytes=max(settings.VOICE_CLONE_MAX_AUDIO_BYTES, 50 * 1024 * 1024),
            )
            input_ext = Path(guessed_name).suffix or f".{request.audio_format}"
            output_ext = f".{request.audio_format}"
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
            result["audio_url"] = speed_asset["url"]
            result["audio_local_path"] = speed_asset["path"]
        result["speed"] = speed
        result["text"] = normalized["text"]
        result["tagged_text"] = normalized["tagged_text"]
        result["sentence_emotions"] = normalized["sentence_emotions"]
        result["emotion"] = normalized["emotion"]
        result["tone_tags"] = normalized["tone_tags"]
        result["effect_tags"] = normalized["effect_tags"]
        result["auto_emotion"] = normalized["auto_emotion"]
        result["auto_breaks"] = normalized["auto_breaks"]
        result["voice_profile"] = voice_profile

        return {"success": True, "data": result}
    except VoicvClientError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TTSTagError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MediaSourceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tts/preview-tags")
async def preview_tts_tags(request: TTSPreviewRequest):
    try:
        profile_store = VoiceStyleProfileStore()
        voice_profile = (
            profile_store.get(request.voice_id)
            if request.use_voice_profile and request.voice_id
            else None
        )
        normalized = await build_expressive_tts_text_async(
            request.text,
            emotion=request.emotion,
            tone_tags=request.tone_tags,
            effect_tags=request.effect_tags,
            auto_emotion=request.auto_emotion,
            auto_breaks=request.auto_breaks,
            voice_profile=voice_profile,
            tag_strategy=request.tag_strategy or "llm",
            speech_style=request.speech_style or "speech",
        )
        response_payload = {
            "success": True,
            "data": {
                "text": normalized["text"],
                "tagged_text": normalized["tagged_text"],
                "sentence_emotions": normalized["sentence_emotions"],
                "emotion": normalized["emotion"],
                "tone_tags": normalized["tone_tags"],
                "effect_tags": normalized["effect_tags"],
                "auto_emotion": normalized["auto_emotion"],
                "auto_breaks": normalized["auto_breaks"],
                "voice_profile": voice_profile,
            },
        }
        user_id = current_user.user_id if current_user else None
        if user_id:
            store = MediaAIStore()
            await store.insert_tts_result(
                user_id,
                {
                    "voice_id": request.voice_id,
                    "text": normalized["text"],
                    "tagged_text": normalized["tagged_text"],
                    "audio_url": final_audio_url,
                    "original_audio_url": result.get("original_audio_url"),
                    "format": request.audio_format,
                    "speed": speed,
                    "emotion": normalized["emotion"],
                    "tone_tags": normalized["tone_tags"],
                    "effect_tags": normalized["effect_tags"],
                    "sentence_emotions": normalized["sentence_emotions"],
                    "auto_emotion": normalized["auto_emotion"],
                    "auto_breaks": normalized["auto_breaks"],
                    "voice_profile": voice_profile,
                },
            )
        return response_payload
    except TTSTagError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/lipsync")
async def create_lipsync(
    request: LipsyncRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    try:
        source_svc = MediaAISourceService()
        sync_client = SyncsoClient()
        resolved_video_url = await _resolve_content_media_url(request.video_url)

        video_bytes, video_name, video_content_type = await source_svc.download_bytes(
            resolved_video_url,
            max_bytes=300 * 1024 * 1024,
        )
        audio_bytes, audio_name, audio_content_type = await source_svc.download_bytes(
            request.audio_url,
            max_bytes=50 * 1024 * 1024,
        )

        result = await sync_client.create_generation(
            video_bytes=video_bytes,
            video_filename=video_name,
            video_content_type=video_content_type,
            audio_bytes=audio_bytes,
            audio_filename=audio_name,
            audio_content_type=audio_content_type,
            model=request.model,
        )
        user_id = current_user.user_id if current_user else None
        if user_id:
            store = MediaAIStore()
            await store.upsert_lipsync_result(
                user_id,
                {
                    "generation_id": result.get("generation_id"),
                    "model": request.model,
                    "status": result.get("status"),
                    "output_url": result.get("output_url"),
                    "video_url": resolved_video_url,
                    "audio_url": request.audio_url,
                    "video_source_type": "url",
                    "audio_source_type": "upload",
                },
            )
        return {"success": True, "data": result}
    except HTTPException as e:
        logger.warning(f"[media-ai] /lipsync HTTPException: detail={e.detail}")
        raise
    except (MediaSourceError, SyncsoClientError) as e:
        logger.warning(f"[media-ai] /lipsync failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/lipsync/{generation_id}")
async def get_lipsync_status(generation_id: str):
    try:
        client = SyncsoClient()
        data = await client.get_generation(generation_id)
        return {"success": True, "data": data}
    except SyncsoClientError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/voices")
async def list_voice_clones(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(default=None),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    user_id = current_user.user_id if current_user else None
    store = MediaAIStore()
    items = await store.list_voices(user_id, limit=limit, offset=offset, query_text=q or "")
    total = await store.count_voices(user_id, query_text=q or "")
    return {"success": True, "data": items, "total": total}


@router.get("/avatars")
async def list_avatars(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(default=None),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    user_id = current_user.user_id if current_user else None
    store = MediaAIStore()
    items = await store.list_avatars(user_id, limit=limit, offset=offset, query_text=q or "")
    total = await store.count_avatars(user_id, query_text=q or "")
    return {"success": True, "data": items, "total": total}


@router.get("/tts-results")
async def list_tts_results(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(default=None),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    user_id = current_user.user_id if current_user else None
    store = MediaAIStore()
    items = await store.list_tts_results(user_id, limit=limit, offset=offset, query_text=q or "")
    total = await store.count_tts_results(user_id, query_text=q or "")
    return {"success": True, "data": items, "total": total}


@router.get("/lipsync-results")
async def list_lipsync_results(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(default=None),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    user_id = current_user.user_id if current_user else None
    store = MediaAIStore()
    items = await store.list_lipsync_results(user_id, limit=limit, offset=offset, query_text=q or "")
    total = await store.count_lipsync_results(user_id, query_text=q or "")
    return {"success": True, "data": items, "total": total}
