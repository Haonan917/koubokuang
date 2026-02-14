# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/video_merger.py
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
视频合并服务 - 合并B站分离的视频和音频流

B站使用 DASH 格式，视频和音频是分离的 m4s 文件，
需要使用 FFmpeg 合并成完整的 mp4 文件。
"""
import asyncio
import os
import subprocess
from pathlib import Path
from typing import Optional

from utils.logger import logger


class VideoMergeError(Exception):
    """视频合并错误"""
    pass


class VideoMerger:
    """视频合并器"""

    def __init__(self):
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> None:
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                logger.warning("FFmpeg check failed, video merge may not work")
        except FileNotFoundError:
            logger.warning("FFmpeg not found, video merge will not work")
        except Exception as e:
            logger.warning(f"FFmpeg check error: {e}")

    async def merge_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        timeout: int = 300
    ) -> str:
        """
        合并视频和音频流

        Args:
            video_path: 视频文件路径（m4s）
            audio_path: 音频文件路径（m4s）
            output_path: 输出文件路径（mp4）
            timeout: 超时时间（秒）

        Returns:
            输出文件路径

        Raises:
            VideoMergeError: 合并失败
        """
        video_path = Path(video_path)
        audio_path = Path(audio_path)
        output_path = Path(output_path)

        if not video_path.exists():
            raise VideoMergeError(f"视频文件不存在: {video_path}")
        if not audio_path.exists():
            raise VideoMergeError(f"音频文件不存在: {audio_path}")

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # FFmpeg 命令: 直接复制流，不重新编码
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c", "copy",  # 直接复制，不重新编码
            "-y",  # 覆盖输出文件
            str(output_path)
        ]

        logger.info(f"Merging video and audio: {' '.join(cmd)}")

        try:
            # 在线程池中运行 FFmpeg
            process = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if process.returncode != 0:
                logger.error(f"FFmpeg merge failed: {process.stderr}")
                raise VideoMergeError(f"FFmpeg 合并失败: {process.stderr[:500]}")

            if not output_path.exists():
                raise VideoMergeError("合并后的文件不存在")

            output_size = output_path.stat().st_size
            logger.info(f"Video merge completed: {output_path} ({output_size / 1024 / 1024:.2f} MB)")

            return str(output_path)

        except subprocess.TimeoutExpired:
            raise VideoMergeError(f"FFmpeg 合并超时 ({timeout}秒)")
        except Exception as e:
            if isinstance(e, VideoMergeError):
                raise
            raise VideoMergeError(f"视频合并失败: {str(e)}")

    async def download_and_merge_bilibili(
        self,
        video_url: str,
        audio_url: str,
        output_path: str,
        task_id: str,
        timeout: int = 300
    ) -> str:
        """
        下载并合并B站视频音频

        Args:
            video_url: 视频流 URL
            audio_url: 音频流 URL
            output_path: 最终输出路径
            task_id: 任务 ID（用于临时文件）
            timeout: 合并超时时间

        Returns:
            合并后的视频路径

        Raises:
            VideoMergeError: 下载或合并失败
        """
        from services.video_downloader import VideoDownloader, VideoDownloadError

        downloader = VideoDownloader()
        task_dir = downloader.get_task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        video_temp_path = None
        audio_temp_path = None

        try:
            # 1. 下载视频流
            logger.info(f"[{task_id}] Downloading video stream...")
            video_temp_path = await downloader.download(video_url, f"{task_id}_video")
            logger.info(f"[{task_id}] Video stream downloaded: {video_temp_path}")

            # 2. 下载音频流
            logger.info(f"[{task_id}] Downloading audio stream...")
            audio_temp_path = await downloader.download(audio_url, f"{task_id}_audio")
            logger.info(f"[{task_id}] Audio stream downloaded: {audio_temp_path}")

            # 3. 合并视频和音频
            logger.info(f"[{task_id}] Merging video and audio...")
            merged_path = str(task_dir / "merged.mp4")
            await self.merge_video_audio(
                video_temp_path,
                audio_temp_path,
                merged_path,
                timeout
            )

            return merged_path

        except VideoDownloadError as e:
            raise VideoMergeError(f"下载失败: {str(e)}")
        finally:
            # 清理临时的视频和音频文件
            if video_temp_path:
                downloader.cleanup(f"{task_id}_video")
            if audio_temp_path:
                downloader.cleanup(f"{task_id}_audio")
