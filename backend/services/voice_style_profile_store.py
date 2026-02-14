# -*- coding: utf-8 -*-
"""语音表达习惯配置存储（按 voice_id 持久化）"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from config import settings
from services.tts_tag_service import normalize_effect_tags, normalize_tone_tags


class VoiceStyleProfileStore:
    """voice_id -> style profile 简易 JSON 存储"""

    def __init__(self):
        self._store_path = Path(settings.ASSETS_DIR) / "voice_style_profiles.json"

    def _ensure_parent(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_all(self) -> Dict[str, Dict[str, Any]]:
        if not self._store_path.exists():
            return {}
        try:
            payload = json.loads(self._store_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _write_all(self, payload: Dict[str, Dict[str, Any]]) -> None:
        self._ensure_parent()
        self._store_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def normalize_profile(self, profile: Optional[dict]) -> Dict[str, Any]:
        profile = profile or {}
        auto_emotion = bool(profile.get("auto_emotion", True))
        auto_breaks = bool(profile.get("auto_breaks", True))
        tone_tags = normalize_tone_tags(profile.get("tone_tags") or [])
        effect_tags = normalize_effect_tags(profile.get("effect_tags") or [])
        return {
            "auto_emotion": auto_emotion,
            "auto_breaks": auto_breaks,
            "tone_tags": tone_tags,
            "effect_tags": effect_tags,
        }

    def get(self, voice_id: str) -> Optional[Dict[str, Any]]:
        if not voice_id:
            return None
        all_data = self._read_all()
        raw_profile = all_data.get(voice_id)
        if not isinstance(raw_profile, dict):
            return None
        return self.normalize_profile(raw_profile)

    def upsert(self, voice_id: str, profile: Optional[dict]) -> Dict[str, Any]:
        if not voice_id:
            raise ValueError("voice_id 不能为空")
        normalized = self.normalize_profile(profile or {})
        all_data = self._read_all()
        all_data[voice_id] = normalized
        self._write_all(all_data)
        return normalized

