# -*- coding: utf-8 -*-
"""Voicv API 客户端 - 语音克隆 / TTS"""

from typing import Any, Dict, Optional

import httpx

from config import settings


class VoicvClientError(Exception):
    """Voicv API 调用异常"""


class VoicvClient:
    """Voicv API 客户端"""

    def __init__(self):
        self.base_url = settings.VOICV_BASE_URL.rstrip("/")
        self.api_key = settings.VOICV_API_KEY
        self.timeout = settings.VOICV_TIMEOUT

    def _check_config(self) -> None:
        if not self.api_key:
            raise VoicvClientError("VOICV_API_KEY 未配置")
        if not self.base_url:
            raise VoicvClientError("VOICV_BASE_URL 未配置")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        files: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ) -> Dict[str, Any]:
        self._check_config()

        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"x-api-key": self.api_key}
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    files=files,
                    json=json_body,
                    headers=headers,
                )
        except httpx.TimeoutException as e:
            raise VoicvClientError(f"Voicv 请求超时: {e}") from e
        except httpx.ConnectError as e:
            raise VoicvClientError(f"无法连接 Voicv 服务: {e}") from e
        except httpx.RequestError as e:
            raise VoicvClientError(f"Voicv 请求失败: {e}") from e

        try:
            payload = response.json()
        except Exception as e:
            raise VoicvClientError(f"Voicv 返回非 JSON 响应: HTTP {response.status_code}") from e

        if response.status_code >= 400:
            message = payload.get("message") if isinstance(payload, dict) else None
            raise VoicvClientError(message or f"Voicv HTTP 错误: {response.status_code}")

        if payload.get("code") != 200:
            raise VoicvClientError(payload.get("message") or "Voicv 请求失败")

        return payload.get("data") or {}

    async def clone_voice(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        """
        调用 Voicv voice-clone API

        Returns:
            {
                "voice_id": str,
                "sample_audio_url": str,
                "cost_credits": int | None,
                "raw": dict,
            }
        """
        data = await self._request(
            "POST",
            "/voice-clone",
            files={"voice": (filename, audio_bytes, content_type)},
        )
        voice_id = data.get("voiceId")
        if not voice_id:
            raise VoicvClientError("Voicv 返回缺少 voiceId")

        return {
            "voice_id": voice_id,
            "sample_audio_url": data.get("sampleAudioUrl", ""),
            "cost_credits": data.get("costCredits"),
            "raw": data,
        }

    async def text_to_speech(
        self,
        voice_id: str,
        text: str,
        audio_format: str = "mp3",
    ) -> Dict[str, Any]:
        """调用 Voicv TTS API"""
        if not voice_id:
            raise VoicvClientError("voice_id 不能为空")
        if not text:
            raise VoicvClientError("text 不能为空")

        data = await self._request(
            "POST",
            "/tts",
            json_body={
                "voiceId": voice_id,
                "text": text,
                "format": audio_format,
            },
        )

        audio_url = data.get("audioUrl") or data.get("url") or ""
        if not audio_url:
            raise VoicvClientError("Voicv TTS 返回缺少 audioUrl")

        return {
            "audio_url": audio_url,
            "voice_id": voice_id,
            "format": audio_format,
            "raw": data,
        }
