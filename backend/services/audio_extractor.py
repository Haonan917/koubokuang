# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/audio_extractor.py
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
音频提取器 - 从视频中提取音频用于 ASR

使用 ffmpeg 将视频转换为 16kHz 单声道 WAV 格式
"""
import subprocess
from pathlib import Path

from config import settings
from utils.logger import logger


class AudioExtractError(Exception):
    """音频提取错误"""
    pass


class AudioExtractor:
    """音频提取器"""

    def __init__(self):
        self.sample_rate = settings.AUDIO_SAMPLE_RATE  # 16000

    def extract(self, video_path: str) -> str:
        """
        从视频中提取音频

        Args:
            video_path: 视频文件路径

        Returns:
            音频文件路径（WAV 格式）

        Raises:
            AudioExtractError: 提取失败
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise AudioExtractError(f"视频文件不存在: {video_path}")

        audio_path = video_path.parent / "audio.wav"

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ar", str(self.sample_rate),  # 采样率 16000
            "-ac", "1",                     # 单声道
            "-f", "wav",                    # WAV 格式
            "-y",                           # 覆盖已存在
            str(audio_path)
        ]

        logger.info(f"开始提取音频: {video_path}")

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=300,  # 5分钟超时
            )
            logger.info(f"音频提取成功: {audio_path}")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else ''
            logger.error(f"ffmpeg 错误: {stderr[:500]}")
            raise AudioExtractError(f"ffmpeg 执行失败: {stderr[:200]}")
        except subprocess.TimeoutExpired:
            logger.error("音频提取超时")
            raise AudioExtractError("音频提取超时")
        except BrokenPipeError as e:
            logger.error(f"管道错误: {e}")
            raise AudioExtractError(f"音频提取中断: {e}")
        except FileNotFoundError:
            raise AudioExtractError("ffmpeg 未安装或不在 PATH 中")

        if not audio_path.exists():
            raise AudioExtractError("音频文件生成失败")

        # 诊断：检查输出文件大小和时长
        output_size = audio_path.stat().st_size
        logger.info(f"音频提取完成: {audio_path}, 大小: {output_size / 1024:.2f} KB")

        # 检查音频时长
        try:
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            duration = float(probe_result.stdout.strip())
            logger.info(f"提取的音频时长: {duration:.2f} 秒")

            if duration < 10:  # 小于 10 秒可能有问题
                logger.warning(f"音频时长过短: {duration:.2f} 秒，原文件可能有问题或提取不完整")
        except Exception as e:
            logger.warning(f"无法获取音频时长: {e}")

        return str(audio_path)

    def check_ffmpeg_available(self) -> bool:
        """检查 ffmpeg 是否可用"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                check=True,
                capture_output=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
