# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/video_downloader.py
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
视频下载器 - 下载视频文件到本地临时目录

功能:
- 流式下载视频
- 进度回调支持
- 临时文件管理和清理
- 下载重试和断点续传
"""
import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional, Callable

import httpx

from config import settings
from utils.logger import logger


class VideoDownloadError(Exception):
    """视频下载错误"""
    pass


class VideoDownloader:
    """视频下载器"""

    # 默认重试配置
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 2  # 秒
    DEFAULT_CHUNK_SIZE = 65536  # 64KB，更大的 chunk 减少 IO 次数

    def __init__(self):
        self.temp_dir = settings.VIDEO_TEMP_DIR
        self.timeout = settings.VIDEO_DOWNLOAD_TIMEOUT
        self.max_retries = getattr(settings, 'VIDEO_DOWNLOAD_MAX_RETRIES', self.DEFAULT_MAX_RETRIES)
        self.retry_delay = getattr(settings, 'VIDEO_DOWNLOAD_RETRY_DELAY', self.DEFAULT_RETRY_DELAY)

    def _get_headers(self, video_url: str) -> dict:
        """
        根据 URL 获取请求头

        不同平台的 CDN 可能需要特定的请求头
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        # B站视频需要 Referer
        if "bilivideo" in video_url or "bilibili" in video_url:
            headers["Referer"] = "https://www.bilibili.com/"

        # 抖音视频
        if "douyinvod" in video_url or "bytedance" in video_url:
            headers["Referer"] = "https://www.douyin.com/"

        return headers

    def _get_file_extension(self, video_url: str, content_type: str = "") -> str:
        """
        根据 URL 和 Content-Type 确定文件扩展名
        """
        # 从 URL 路径提取扩展名
        url_path = video_url.split("?")[0]
        if url_path.endswith(".m4s"):
            return ".m4s"
        elif url_path.endswith(".mp4"):
            return ".mp4"
        elif url_path.endswith(".m3u8"):
            return ".m3u8"
        elif url_path.endswith(".flv"):
            return ".flv"
        elif url_path.endswith(".wav"):
            return ".wav"
        elif url_path.endswith(".mp3"):
            return ".mp3"

        # 从 Content-Type 推断
        if "audio" in content_type:
            if "wav" in content_type:
                return ".wav"
            elif "mp3" in content_type or "mpeg" in content_type:
                return ".mp3"
            return ".m4a"
        elif "video" in content_type:
            if "mp4" in content_type:
                return ".mp4"
            elif "flv" in content_type:
                return ".flv"

        # 默认 mp4
        return ".mp4"

    async def _check_range_support(self, client: httpx.AsyncClient, url: str, headers: dict) -> tuple[bool, int]:
        """
        检查服务器是否支持 Range 请求

        Returns:
            (支持断点续传, 文件总大小)
        """
        try:
            response = await client.head(url, headers=headers)
            accept_ranges = response.headers.get("accept-ranges", "").lower()
            content_length = int(response.headers.get("content-length", 0))
            return accept_ranges == "bytes", content_length
        except Exception:
            return False, 0

    async def _download_with_resume(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict,
        video_path: Path,
        total: int,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> None:
        """
        支持断点续传的下载

        Args:
            client: HTTP 客户端
            url: 下载 URL
            headers: 请求头
            video_path: 保存路径
            total: 文件总大小
            progress_callback: 进度回调
        """
        # 检查已下载的大小
        downloaded = 0
        if video_path.exists():
            downloaded = video_path.stat().st_size
            if downloaded >= total:
                logger.info(f"File already fully downloaded: {video_path}")
                return

        # 添加 Range 头实现断点续传
        req_headers = headers.copy()
        if downloaded > 0:
            req_headers["Range"] = f"bytes={downloaded}-"
            logger.info(f"Resuming download from byte {downloaded}/{total}")

        async with client.stream("GET", url, headers=req_headers) as response:
            # 206 Partial Content 表示断点续传成功
            # 200 OK 表示服务器不支持或返回完整文件
            if response.status_code == 200 and downloaded > 0:
                # 服务器返回完整文件，需要重新下载
                downloaded = 0

            response.raise_for_status()

            # 追加模式或写入模式
            mode = "ab" if downloaded > 0 and response.status_code == 206 else "wb"
            if mode == "wb":
                downloaded = 0

            with open(video_path, mode) as f:
                async for chunk in response.aiter_bytes(chunk_size=self.DEFAULT_CHUNK_SIZE):
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback:
                        progress_callback(downloaded, total)

        # 验证下载完整性
        actual_size = video_path.stat().st_size
        if total > 0 and actual_size < total:
            raise VideoDownloadError(
                f"下载不完整: 收到 {actual_size} 字节，预期 {total} 字节"
            )

    async def download(
        self,
        video_url: str,
        task_id: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> str:
        """
        下载视频（支持重试和断点续传）

        Args:
            video_url: 视频 URL
            task_id: 任务 ID（用于创建临时目录）
            progress_callback: 进度回调 (downloaded_bytes, total_bytes)

        Returns:
            本地文件路径

        Raises:
            VideoDownloadError: 下载失败
        """
        # 创建任务目录
        task_dir = Path(self.temp_dir) / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # 获取请求头
        headers = self._get_headers(video_url)

        last_error = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    # 首次尝试时检查 Range 支持并获取文件大小
                    if attempt == 0:
                        supports_range, total = await self._check_range_support(client, video_url, headers)
                        # 确定文件扩展名
                        async with client.stream("GET", video_url, headers=headers) as resp:
                            content_type = resp.headers.get("content-type", "")
                            ext = self._get_file_extension(video_url, content_type)
                            if total == 0:
                                total = int(resp.headers.get("content-length", 0))
                            # 立即关闭，不读取内容
                            await resp.aclose()

                        video_path = task_dir / f"video{ext}"
                        self._video_path = video_path  # 保存供后续重试使用
                        self._total = total
                        self._supports_range = supports_range
                    else:
                        video_path = self._video_path
                        total = self._total
                        supports_range = self._supports_range

                    # 如果支持断点续传，使用续传方式
                    if supports_range and total > 0:
                        await self._download_with_resume(
                            client, video_url, headers, video_path, total, progress_callback
                        )
                    else:
                        # 不支持断点续传，普通下载
                        await self._simple_download(
                            client, video_url, headers, video_path, progress_callback
                        )

                logger.info(f"Download completed: {video_path}")
                return str(video_path)

            except httpx.TimeoutException as e:
                last_error = VideoDownloadError("视频下载超时")
                logger.warning(f"Download timeout (attempt {attempt + 1}/{self.max_retries}): {e}")
            except httpx.HTTPStatusError as e:
                last_error = VideoDownloadError(f"视频下载失败: HTTP {e.response.status_code}")
                logger.warning(f"HTTP error (attempt {attempt + 1}/{self.max_retries}): {e}")
                # HTTP 错误通常不需要重试（如 404, 403）
                if e.response.status_code in (404, 403, 401):
                    raise last_error
            except VideoDownloadError as e:
                last_error = e
                logger.warning(f"Download error (attempt {attempt + 1}/{self.max_retries}): {e}")
            except Exception as e:
                last_error = VideoDownloadError(f"视频下载失败: {str(e)}")
                logger.warning(f"Unexpected error (attempt {attempt + 1}/{self.max_retries}): {e}")

            # 重试前等待（指数退避）
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)

        # 所有重试都失败
        raise last_error or VideoDownloadError("视频下载失败: 未知错误")

    async def _simple_download(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict,
        video_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> None:
        """
        简单下载（不支持断点续传时使用）
        """
        async with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()

            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(video_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=self.DEFAULT_CHUNK_SIZE):
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback:
                        progress_callback(downloaded, total)

    def cleanup(self, task_id: str) -> None:
        """清理任务临时文件"""
        task_dir = Path(self.temp_dir) / task_id
        if task_dir.exists():
            shutil.rmtree(task_dir)

    def get_task_dir(self, task_id: str) -> Path:
        """获取任务目录路径"""
        return Path(self.temp_dir) / task_id
