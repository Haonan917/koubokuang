# -*- coding: utf-8 -*-
"""Media AI 源处理服务 - 上传保存、URL 下载、音频裁剪"""

import mimetypes
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

import httpx
from fastapi import UploadFile

from config import settings


class MediaSourceError(Exception):
    """媒体源处理异常"""


class MediaAISourceService:
    """媒体源处理服务"""

    def __init__(self):
        self.assets_dir = Path(settings.ASSETS_DIR)
        self.upload_dir = Path(settings.MEDIA_UPLOAD_DIR)
        self.url_prefix = settings.ASSETS_URL_PREFIX.rstrip("/")
        self.download_timeout = settings.VOICE_CLONE_DOWNLOAD_TIMEOUT
        self.max_audio_bytes = settings.VOICE_CLONE_MAX_AUDIO_BYTES

    def _ensure_upload_dir(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_content_type(self, content_type: str, default_value: str) -> str:
        normalized = (content_type or "").split(";")[0].strip()
        return normalized or default_value

    def _guess_ext(self, filename: str, content_type: str, fallback: str) -> str:
        suffix = Path(filename or "").suffix.lower()
        if suffix:
            return suffix
        ext = mimetypes.guess_extension(self._normalize_content_type(content_type, ""))
        return ext or fallback

    def _looks_like_html_or_json(self, content_type: str, payload: bytes) -> bool:
        ct = (content_type or "").lower()
        if ct.startswith("text/") or "application/json" in ct or "application/xml" in ct:
            return True
        head = payload[:512].lower()
        return (
            b"<!doctype html" in head
            or b"<html" in head
            or b"{\"error\"" in head
            or b"{\"message\"" in head
        )

    def _format_ffmpeg_error(self, stderr: str, stdout: str = "") -> str:
        # 返回更有价值的最后几行，避免只看到版本信息
        lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
        if not lines and stdout:
            lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if not lines:
            return "未知 ffmpeg 错误"
        tail = lines[-5:]
        return " | ".join(tail)

    def _build_atempo_filter(self, speed: float) -> str:
        """
        构建 ffmpeg atempo 过滤链。
        atempo 单段支持范围 [0.5, 2.0]，超出时通过多段串联实现。
        """
        if speed <= 0:
            raise MediaSourceError("语速参数必须大于 0")
        if abs(speed - 1.0) < 1e-6:
            return "atempo=1.0"

        remaining = speed
        filters = []
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0
        filters.append(f"atempo={remaining:.4f}")
        return ",".join(filters)

    def build_public_upload_url(self, local_path: Path) -> str:
        relative = local_path.relative_to(self.assets_dir).as_posix()
        return f"{self.url_prefix}/{relative}"

    def _write_bytes_to_uploads(
        self,
        payload: bytes,
        *,
        prefix: str,
        ext: str,
        content_type: str = "application/octet-stream",
    ) -> dict:
        if not payload:
            raise MediaSourceError("写入内容为空")
        self._ensure_upload_dir()
        normalized_ext = ext if ext.startswith(".") else f".{ext}"
        filename = f"{prefix}_{uuid.uuid4().hex}{normalized_ext}"
        target_path = self.upload_dir / filename
        with open(target_path, "wb") as f:
            f.write(payload)
        return {
            "filename": filename,
            "path": str(target_path),
            "size": len(payload),
            "content_type": self._normalize_content_type(content_type, "application/octet-stream"),
            "url": self.build_public_upload_url(target_path),
        }

    async def save_upload(self, upload_file: UploadFile, kind: str) -> dict:
        """
        保存上传文件到 ASSETS_DIR/uploads

        kind: audio / video
        """
        if not upload_file:
            raise MediaSourceError("上传文件不能为空")

        self._ensure_upload_dir()
        content_type = upload_file.content_type or ""
        ext = self._guess_ext(upload_file.filename or "", content_type, ".bin")
        filename = f"{kind}_{uuid.uuid4().hex}{ext}"
        target_path = self.upload_dir / filename

        content = await upload_file.read()
        if not content:
            raise MediaSourceError("上传文件内容为空")

        with open(target_path, "wb") as f:
            f.write(content)

        return {
            "filename": filename,
            "path": str(target_path),
            "size": len(content),
            "content_type": self._normalize_content_type(content_type, "application/octet-stream"),
            "url": self.build_public_upload_url(target_path),
        }

    def persist_bytes(
        self,
        payload: bytes,
        *,
        prefix: str,
        ext: str,
        content_type: str = "application/octet-stream",
    ) -> dict:
        """持久化字节数据到 uploads 目录并返回可访问 URL"""
        return self._write_bytes_to_uploads(
            payload,
            prefix=prefix,
            ext=ext,
            content_type=content_type,
        )

    async def download_bytes(
        self,
        source_url: str,
        *,
        max_bytes: int | None = None,
    ) -> Tuple[bytes, str, str]:
        if not source_url:
            raise MediaSourceError("source_url 不能为空")

        limit = max_bytes if max_bytes is not None else self.max_audio_bytes

        prefix = self.url_prefix
        if source_url.startswith(prefix + "/") or source_url.startswith("/media/"):
            relative = source_url.split(prefix + "/", 1)[-1] if source_url.startswith(prefix + "/") else source_url.split("/media/", 1)[-1]
            local_path = self.assets_dir / relative
            if not local_path.exists():
                raise MediaSourceError(f"本地文件不存在: {source_url}")
            content = local_path.read_bytes()
            if limit > 0 and len(content) > limit:
                raise MediaSourceError(f"本地文件过大，超过限制 {limit} bytes")
            guessed_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
            return content, local_path.name, guessed_type

        try:
            async with httpx.AsyncClient(timeout=self.download_timeout, follow_redirects=True) as client:
                async with client.stream("GET", source_url) as response:
                    response.raise_for_status()
                    content_type = self._normalize_content_type(
                        response.headers.get("content-type", ""),
                        "application/octet-stream",
                    )
                    parsed = urlparse(source_url)
                    guessed_name = Path(parsed.path).name or f"remote_{uuid.uuid4().hex}"

                    chunks = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        if not chunk:
                            continue
                        total += len(chunk)
                        if limit > 0 and total > limit:
                            raise MediaSourceError(f"下载文件过大，超过限制 {limit} bytes")
                        chunks.append(chunk)
        except httpx.TimeoutException as e:
            raise MediaSourceError(f"下载超时: {e}") from e
        except httpx.HTTPStatusError as e:
            raise MediaSourceError(f"下载失败，HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise MediaSourceError(f"下载请求失败: {e}") from e

        payload = b"".join(chunks)
        if self._looks_like_html_or_json(content_type, payload):
            preview = payload[:120].decode("utf-8", errors="ignore").replace("\n", " ").strip()
            raise MediaSourceError(
                f"下载到的内容不是媒体文件（content-type={content_type}），可能是页面/鉴权响应: {preview}"
            )

        return payload, guessed_name, content_type

    def trim_audio_clip(
        self,
        input_bytes: bytes,
        input_ext: str,
        *,
        start_seconds: int = 0,
        duration_seconds: int = 30,
    ) -> Tuple[bytes, str, str]:
        """使用 ffmpeg 裁剪音频片段，输出 wav"""
        if not input_bytes:
            raise MediaSourceError("输入音频为空")

        ext = input_ext if input_ext.startswith(".") else f".{input_ext}"
        with tempfile.TemporaryDirectory(prefix="media_ai_clip_") as temp_dir:
            temp_path = Path(temp_dir)
            in_path = temp_path / f"in{ext or '.bin'}"
            out_path = temp_path / "clip.wav"
            in_path.write_bytes(input_bytes)

            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel", "error",
                "-ss", str(max(0, start_seconds)),
                "-t", str(max(1, duration_seconds)),
                "-i", str(in_path),
                "-vn",
                "-ar", "16000",
                "-ac", "1",
                str(out_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0 or not out_path.exists():
                reason = self._format_ffmpeg_error(result.stderr, result.stdout)
                raise MediaSourceError(f"ffmpeg 裁剪失败: {reason}")

            return out_path.read_bytes(), "clip.wav", "audio/wav"

    def extract_audio_to_wav(
        self,
        input_bytes: bytes,
        input_ext: str,
    ) -> Tuple[bytes, str, str]:
        """从视频/音频源提取完整音轨，输出 16k 单声道 wav"""
        if not input_bytes:
            raise MediaSourceError("输入媒体为空")

        ext = input_ext if input_ext.startswith(".") else f".{input_ext}"
        with tempfile.TemporaryDirectory(prefix="media_ai_extract_") as temp_dir:
            temp_path = Path(temp_dir)
            in_path = temp_path / f"in{ext or '.bin'}"
            out_path = temp_path / "full.wav"
            in_path.write_bytes(input_bytes)

            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel", "error",
                "-i", str(in_path),
                "-vn",
                "-ar", "16000",
                "-ac", "1",
                str(out_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0 or not out_path.exists():
                reason = self._format_ffmpeg_error(result.stderr, result.stdout)
                raise MediaSourceError(f"ffmpeg 提取音轨失败: {reason}")

            return out_path.read_bytes(), "full.wav", "audio/wav"

    def change_audio_speed(
        self,
        input_bytes: bytes,
        input_ext: str,
        *,
        speed: float,
        output_ext: str,
    ) -> Tuple[bytes, str, str]:
        """调整音频语速并返回新音频字节。"""
        if not input_bytes:
            raise MediaSourceError("输入音频为空")
        if speed <= 0:
            raise MediaSourceError("speed 必须大于 0")

        normalized_in_ext = input_ext if input_ext.startswith(".") else f".{input_ext}"
        normalized_out_ext = output_ext if output_ext.startswith(".") else f".{output_ext}"

        if abs(speed - 1.0) < 1e-6:
            content_type = mimetypes.guess_type(f"out{normalized_out_ext}")[0] or "application/octet-stream"
            return input_bytes, f"speed1x{normalized_out_ext}", content_type

        with tempfile.TemporaryDirectory(prefix="media_ai_speed_") as temp_dir:
            temp_path = Path(temp_dir)
            in_path = temp_path / f"in{normalized_in_ext}"
            out_path = temp_path / f"speed{normalized_out_ext}"
            in_path.write_bytes(input_bytes)

            atempo_filter = self._build_atempo_filter(speed)
            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel", "error",
                "-i", str(in_path),
                "-filter:a", atempo_filter,
                str(out_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0 or not out_path.exists():
                reason = self._format_ffmpeg_error(result.stderr, result.stdout)
                raise MediaSourceError(f"ffmpeg 调整语速失败: {reason}")

            out_bytes = out_path.read_bytes()
            content_type = mimetypes.guess_type(out_path.name)[0] or "application/octet-stream"
            return out_bytes, out_path.name, content_type

    def trim_video_clip(
        self,
        input_bytes: bytes,
        input_ext: str,
        *,
        start_seconds: int = 0,
        duration_seconds: int = 30,
    ) -> Tuple[bytes, str, str]:
        """使用 ffmpeg 裁剪视频片段，输出 mp4"""
        if not input_bytes:
            raise MediaSourceError("输入视频为空")

        ext = input_ext if input_ext.startswith(".") else f".{input_ext}"
        with tempfile.TemporaryDirectory(prefix="media_ai_vclip_") as temp_dir:
            temp_path = Path(temp_dir)
            in_path = temp_path / f"in{ext or '.bin'}"
            out_path = temp_path / "clip.mp4"
            in_path.write_bytes(input_bytes)

            cmd = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel", "error",
                "-ss", str(max(0, start_seconds)),
                "-t", str(max(1, duration_seconds)),
                "-i", str(in_path),
                "-map", "0:v:0",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-c:a", "aac",
                "-movflags", "+faststart",
                "-pix_fmt", "yuv420p",
                str(out_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0 or not out_path.exists():
                reason = self._format_ffmpeg_error(result.stderr, result.stdout)
                raise MediaSourceError(f"ffmpeg 裁剪视频失败: {reason}")

            return out_path.read_bytes(), out_path.name, "video/mp4"
