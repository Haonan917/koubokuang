# -*- coding: utf-8 -*-
"""Media AI 资产持久化存储（MySQL）"""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from db.base import get_async_session
from utils.logger import logger


def _json_dump(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return None


def _json_load(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


class MediaAIStore:
    async def upsert_voice_clone(self, user_id: Optional[str], data: Dict[str, Any]) -> None:
        if not user_id:
            return
        voice_id = (data.get("voice_id") or "").strip()
        if not voice_id:
            return
        payload = {
            "user_id": user_id,
            "voice_id": voice_id,
            "title": data.get("title"),
            "description": data.get("description"),
            "source_type": data.get("source_type"),
            "source_url": data.get("source_url"),
            "sample_audio_url": data.get("sample_audio_url"),
            "full_audio_url": data.get("full_audio_url"),
            "full_audio_path": data.get("full_audio_path"),
            "clip_audio_url": data.get("clip_audio_url"),
            "clip_audio_path": data.get("clip_audio_path"),
            "expression_profile": _json_dump(data.get("expression_profile")),
        }
        query = text(
            """
            INSERT INTO media_ai_voice_clones (
                user_id, voice_id, title, description, source_type, source_url,
                sample_audio_url, full_audio_url, full_audio_path, clip_audio_url, clip_audio_path,
                expression_profile
            ) VALUES (
                :user_id, :voice_id, :title, :description, :source_type, :source_url,
                :sample_audio_url, :full_audio_url, :full_audio_path, :clip_audio_url, :clip_audio_path,
                :expression_profile
            )
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                description = VALUES(description),
                source_type = VALUES(source_type),
                source_url = VALUES(source_url),
                sample_audio_url = VALUES(sample_audio_url),
                full_audio_url = VALUES(full_audio_url),
                full_audio_path = VALUES(full_audio_path),
                clip_audio_url = VALUES(clip_audio_url),
                clip_audio_path = VALUES(clip_audio_path),
                expression_profile = VALUES(expression_profile),
                updated_at = CURRENT_TIMESTAMP(6)
            """
        )
        try:
            async with get_async_session() as session:
                await session.execute(query, payload)
        except Exception as exc:
            logger.warning(f"Failed to persist voice clone: {exc}")

    async def upsert_avatar(self, user_id: Optional[str], data: Dict[str, Any]) -> None:
        if not user_id:
            return
        avatar_id = (data.get("avatar_id") or data.get("avatarId") or "").strip()
        if not avatar_id:
            return
        payload = {
            "user_id": user_id,
            "avatar_id": avatar_id,
            "title": data.get("title"),
            "description": data.get("description"),
            "source_type": data.get("source_type"),
            "source_url": data.get("source_url"),
            "full_video_url": data.get("full_video_url"),
            "full_video_path": data.get("full_video_path"),
            "clip_video_url": data.get("clip_video_url"),
            "clip_video_path": data.get("clip_video_path"),
        }
        query = text(
            """
            INSERT INTO media_ai_avatars (
                user_id, avatar_id, title, description, source_type, source_url,
                full_video_url, full_video_path, clip_video_url, clip_video_path
            ) VALUES (
                :user_id, :avatar_id, :title, :description, :source_type, :source_url,
                :full_video_url, :full_video_path, :clip_video_url, :clip_video_path
            )
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                description = VALUES(description),
                source_type = VALUES(source_type),
                source_url = VALUES(source_url),
                full_video_url = VALUES(full_video_url),
                full_video_path = VALUES(full_video_path),
                clip_video_url = VALUES(clip_video_url),
                clip_video_path = VALUES(clip_video_path),
                updated_at = CURRENT_TIMESTAMP(6)
            """
        )
        try:
            async with get_async_session() as session:
                await session.execute(query, payload)
        except Exception as exc:
            logger.warning(f"Failed to persist avatar: {exc}")

    async def insert_tts_result(self, user_id: Optional[str], data: Dict[str, Any]) -> None:
        if not user_id:
            return
        payload = {
            "user_id": user_id,
            "voice_id": data.get("voice_id"),
            "text": data.get("text"),
            "tagged_text": data.get("tagged_text"),
            "audio_url": data.get("audio_url"),
            "original_audio_url": data.get("original_audio_url"),
            "format": data.get("format"),
            "speed": data.get("speed"),
            "emotion": data.get("emotion"),
            "tone_tags": _json_dump(data.get("tone_tags")),
            "effect_tags": _json_dump(data.get("effect_tags")),
            "sentence_emotions": _json_dump(data.get("sentence_emotions")),
            "auto_emotion": data.get("auto_emotion"),
            "auto_breaks": data.get("auto_breaks"),
            "voice_profile": _json_dump(data.get("voice_profile")),
        }
        query = text(
            """
            INSERT INTO media_ai_tts_results (
                user_id, voice_id, text, tagged_text, audio_url, original_audio_url, format, speed,
                emotion, tone_tags, effect_tags, sentence_emotions, auto_emotion, auto_breaks, voice_profile
            ) VALUES (
                :user_id, :voice_id, :text, :tagged_text, :audio_url, :original_audio_url, :format, :speed,
                :emotion, :tone_tags, :effect_tags, :sentence_emotions, :auto_emotion, :auto_breaks, :voice_profile
            )
            """
        )
        try:
            async with get_async_session() as session:
                await session.execute(query, payload)
        except Exception as exc:
            logger.warning(f"Failed to persist TTS result: {exc}")

    async def upsert_lipsync_result(self, user_id: Optional[str], data: Dict[str, Any]) -> None:
        if not user_id:
            return
        generation_id = (data.get("generation_id") or "").strip()
        if not generation_id:
            return
        payload = {
            "user_id": user_id,
            "generation_id": generation_id,
            "model": data.get("model"),
            "status": data.get("status"),
            "output_url": data.get("output_url"),
            "video_url": data.get("video_url"),
            "audio_url": data.get("audio_url"),
            "video_source_type": data.get("video_source_type"),
            "audio_source_type": data.get("audio_source_type"),
        }
        query = text(
            """
            INSERT INTO media_ai_lipsync_results (
                user_id, generation_id, model, status, output_url,
                video_url, audio_url, video_source_type, audio_source_type
            ) VALUES (
                :user_id, :generation_id, :model, :status, :output_url,
                :video_url, :audio_url, :video_source_type, :audio_source_type
            )
            ON DUPLICATE KEY UPDATE
                model = VALUES(model),
                status = VALUES(status),
                output_url = VALUES(output_url),
                video_url = VALUES(video_url),
                audio_url = VALUES(audio_url),
                video_source_type = VALUES(video_source_type),
                audio_source_type = VALUES(audio_source_type),
                updated_at = CURRENT_TIMESTAMP(6)
            """
        )
        try:
            async with get_async_session() as session:
                await session.execute(query, payload)
        except Exception as exc:
            logger.warning(f"Failed to persist lipsync result: {exc}")

    async def list_voices(self, user_id: Optional[str], limit: int = 50, offset: int = 0, query_text: str = "") -> List[Dict[str, Any]]:
        if not user_id:
            return []
        q = f"%{query_text.strip()}%" if query_text else None
        sql = """
            SELECT voice_id, title, description, source_type, source_url,
                   sample_audio_url, full_audio_url, full_audio_path,
                   clip_audio_url, clip_audio_path, expression_profile, created_at
            FROM media_ai_voice_clones
            WHERE user_id = :user_id
        """
        if q:
            sql += " AND (voice_id LIKE :q OR title LIKE :q OR description LIKE :q)"
        sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        async with get_async_session() as session:
            rows = (await session.execute(text(sql), {"user_id": user_id, "limit": limit, "offset": offset, "q": q})).mappings().all()
        return [
            {
                "voiceId": row["voice_id"],
                "title": row["title"],
                "description": row["description"],
                "sourceType": row["source_type"],
                "sourceUrl": row["source_url"],
                "sampleAudioUrl": row["sample_audio_url"],
                "fullAudioUrl": row["full_audio_url"],
                "fullAudioPath": row["full_audio_path"],
                "clipAudioUrl": row["clip_audio_url"],
                "clipAudioPath": row["clip_audio_path"],
                "expressionProfile": _json_load(row["expression_profile"]),
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    async def list_avatars(self, user_id: Optional[str], limit: int = 50, offset: int = 0, query_text: str = "") -> List[Dict[str, Any]]:
        if not user_id:
            return []
        q = f"%{query_text.strip()}%" if query_text else None
        sql = """
            SELECT avatar_id, title, description, source_type, source_url,
                   full_video_url, full_video_path, clip_video_url, clip_video_path, created_at
            FROM media_ai_avatars
            WHERE user_id = :user_id
        """
        if q:
            sql += " AND (avatar_id LIKE :q OR title LIKE :q OR description LIKE :q)"
        sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        async with get_async_session() as session:
            rows = (await session.execute(text(sql), {"user_id": user_id, "limit": limit, "offset": offset, "q": q})).mappings().all()
        return [
            {
                "avatarId": row["avatar_id"],
                "title": row["title"],
                "description": row["description"],
                "sourceType": row["source_type"],
                "sourceUrl": row["source_url"],
                "fullVideoUrl": row["full_video_url"],
                "fullVideoPath": row["full_video_path"],
                "clipVideoUrl": row["clip_video_url"],
                "clipVideoPath": row["clip_video_path"],
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    async def list_tts_results(self, user_id: Optional[str], limit: int = 50, offset: int = 0, query_text: str = "") -> List[Dict[str, Any]]:
        if not user_id:
            return []
        q = f"%{query_text.strip()}%" if query_text else None
        sql = """
            SELECT voice_id, text, tagged_text, audio_url, original_audio_url, format, speed, emotion,
                   tone_tags, effect_tags, sentence_emotions, auto_emotion, auto_breaks, voice_profile, created_at
            FROM media_ai_tts_results
            WHERE user_id = :user_id
        """
        if q:
            sql += " AND (voice_id LIKE :q OR text LIKE :q OR tagged_text LIKE :q)"
        sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        async with get_async_session() as session:
            rows = (await session.execute(text(sql), {"user_id": user_id, "limit": limit, "offset": offset, "q": q})).mappings().all()
        return [
            {
                "voiceId": row["voice_id"],
                "text": row["text"],
                "taggedText": row["tagged_text"],
                "audioUrl": row["audio_url"],
                "originalAudioUrl": row["original_audio_url"],
                "format": row["format"],
                "speed": float(row["speed"]) if row["speed"] is not None else None,
                "emotion": row["emotion"],
                "toneTags": _json_load(row["tone_tags"]) or [],
                "effectTags": _json_load(row["effect_tags"]) or [],
                "sentenceEmotions": _json_load(row["sentence_emotions"]) or [],
                "autoEmotion": bool(row["auto_emotion"]) if row["auto_emotion"] is not None else None,
                "autoBreaks": bool(row["auto_breaks"]) if row["auto_breaks"] is not None else None,
                "voiceProfile": _json_load(row["voice_profile"]),
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    async def list_lipsync_results(self, user_id: Optional[str], limit: int = 50, offset: int = 0, query_text: str = "") -> List[Dict[str, Any]]:
        if not user_id:
            return []
        q = f"%{query_text.strip()}%" if query_text else None
        sql = """
            SELECT generation_id, model, status, output_url, video_url, audio_url,
                   video_source_type, audio_source_type, created_at
            FROM media_ai_lipsync_results
            WHERE user_id = :user_id
        """
        if q:
            sql += " AND (generation_id LIKE :q OR model LIKE :q)"
        sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        async with get_async_session() as session:
            rows = (await session.execute(text(sql), {"user_id": user_id, "limit": limit, "offset": offset, "q": q})).mappings().all()
        return [
            {
                "generationId": row["generation_id"],
                "model": row["model"],
                "status": row["status"],
                "outputUrl": row["output_url"],
                "videoUrl": row["video_url"],
                "audioUrl": row["audio_url"],
                "videoSourceType": row["video_source_type"],
                "audioSourceType": row["audio_source_type"],
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    async def get_latest_voice(self, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        voices = await self.list_voices(user_id, limit=1)
        return voices[0] if voices else None

    async def get_latest_avatar(self, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
        avatars = await self.list_avatars(user_id, limit=1)
        return avatars[0] if avatars else None

    async def count_voices(self, user_id: Optional[str], query_text: str = "") -> int:
        if not user_id:
            return 0
        q = f"%{query_text.strip()}%" if query_text else None
        sql = "SELECT COUNT(*) AS total FROM media_ai_voice_clones WHERE user_id = :user_id"
        if q:
            sql += " AND (voice_id LIKE :q OR title LIKE :q OR description LIKE :q)"
        async with get_async_session() as session:
            row = (await session.execute(text(sql), {"user_id": user_id, "q": q})).mappings().first()
        return int(row["total"]) if row else 0

    async def count_avatars(self, user_id: Optional[str], query_text: str = "") -> int:
        if not user_id:
            return 0
        q = f"%{query_text.strip()}%" if query_text else None
        sql = "SELECT COUNT(*) AS total FROM media_ai_avatars WHERE user_id = :user_id"
        if q:
            sql += " AND (avatar_id LIKE :q OR title LIKE :q OR description LIKE :q)"
        async with get_async_session() as session:
            row = (await session.execute(text(sql), {"user_id": user_id, "q": q})).mappings().first()
        return int(row["total"]) if row else 0

    async def count_tts_results(self, user_id: Optional[str], query_text: str = "") -> int:
        if not user_id:
            return 0
        q = f"%{query_text.strip()}%" if query_text else None
        sql = "SELECT COUNT(*) AS total FROM media_ai_tts_results WHERE user_id = :user_id"
        if q:
            sql += " AND (voice_id LIKE :q OR text LIKE :q OR tagged_text LIKE :q)"
        async with get_async_session() as session:
            row = (await session.execute(text(sql), {"user_id": user_id, "q": q})).mappings().first()
        return int(row["total"]) if row else 0

    async def count_lipsync_results(self, user_id: Optional[str], query_text: str = "") -> int:
        if not user_id:
            return 0
        q = f"%{query_text.strip()}%" if query_text else None
        sql = "SELECT COUNT(*) AS total FROM media_ai_lipsync_results WHERE user_id = :user_id"
        if q:
            sql += " AND (generation_id LIKE :q OR model LIKE :q)"
        async with get_async_session() as session:
            row = (await session.execute(text(sql), {"user_id": user_id, "q": q})).mappings().first()
        return int(row["total"]) if row else 0
