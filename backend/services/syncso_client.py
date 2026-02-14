# -*- coding: utf-8 -*-
"""Sync.so API 客户端 - Lipsync 生成"""

from typing import Any, Dict

import httpx

from config import settings


class SyncsoClientError(Exception):
    """Sync.so API 调用异常"""


class SyncsoClient:
    """Sync.so API 客户端"""

    def __init__(self):
        self.base_url = settings.SYNCSO_BASE_URL.rstrip("/")
        self.api_key = settings.SYNCSO_API_KEY
        self.timeout = settings.SYNCSO_TIMEOUT

    def _check_config(self) -> None:
        if not self.api_key:
            raise SyncsoClientError("SYNCSO_API_KEY 未配置")
        if not self.base_url:
            raise SyncsoClientError("SYNCSO_BASE_URL 未配置")

    async def create_generation(
        self,
        video_bytes: bytes,
        video_filename: str,
        video_content_type: str,
        audio_bytes: bytes,
        audio_filename: str,
        audio_content_type: str,
        model: str = "lipsync-2",
    ) -> Dict[str, Any]:
        """创建 lipsync 任务"""
        self._check_config()
        url = f"{self.base_url}/generate"
        headers = {"x-api-key": self.api_key}
        files = {
            "video": (video_filename, video_bytes, video_content_type),
            "audio": (audio_filename, audio_bytes, audio_content_type),
        }
        form_data = {"model": model}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, files=files, data=form_data, headers=headers)
        except httpx.TimeoutException as e:
            raise SyncsoClientError(f"Sync.so 请求超时: {e}") from e
        except httpx.ConnectError as e:
            raise SyncsoClientError(f"无法连接 Sync.so 服务: {e}") from e
        except httpx.RequestError as e:
            raise SyncsoClientError(f"Sync.so 请求失败: {e}") from e

        try:
            payload = response.json()
        except Exception as e:
            raise SyncsoClientError(f"Sync.so 返回非 JSON 响应: HTTP {response.status_code}") from e

        if response.status_code not in (200, 201):
            raise SyncsoClientError(
                payload.get("error")
                or payload.get("message")
                or f"Sync.so HTTP 错误: {response.status_code}"
            )

        return {
            "generation_id": payload.get("id"),
            "status": payload.get("status", "PENDING"),
            "output_url": payload.get("outputUrl") or payload.get("outputMediaUrl") or "",
            "created_at": payload.get("createdAt"),
            "raw": payload,
        }

    async def get_generation(self, generation_id: str) -> Dict[str, Any]:
        """查询 lipsync 任务状态"""
        self._check_config()
        url = f"{self.base_url}/generate/{generation_id}"
        headers = {"x-api-key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
        except httpx.TimeoutException as e:
            raise SyncsoClientError(f"Sync.so 状态查询超时: {e}") from e
        except httpx.RequestError as e:
            raise SyncsoClientError(f"Sync.so 状态查询失败: {e}") from e

        try:
            payload = response.json()
        except Exception as e:
            raise SyncsoClientError(f"Sync.so 返回非 JSON 响应: HTTP {response.status_code}") from e

        if response.status_code != 200:
            raise SyncsoClientError(
                payload.get("error")
                or payload.get("message")
                or f"Sync.so HTTP 错误: {response.status_code}"
            )

        return payload
