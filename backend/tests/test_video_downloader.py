# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/tests/test_video_downloader.py
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
视频下载器和音频提取器测试 - TDD
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from services.video_downloader import VideoDownloader, VideoDownloadError
from services.audio_extractor import AudioExtractor, AudioExtractError


class TestVideoDownloader:
    """视频下载器测试"""

    def test_downloader_uses_config(self):
        """测试下载器使用配置"""
        downloader = VideoDownloader()
        assert downloader.temp_dir is not None
        assert downloader.timeout > 0

    def test_get_task_dir(self):
        """测试获取任务目录"""
        downloader = VideoDownloader()
        task_dir = downloader.get_task_dir("test_task_123")
        assert "test_task_123" in str(task_dir)

    def test_cleanup_nonexistent_dir(self):
        """测试清理不存在的目录不报错"""
        downloader = VideoDownloader()
        # 不应该抛出异常
        downloader.cleanup("nonexistent_task_id_12345")

    def test_cleanup_existing_dir(self):
        """测试清理已存在的目录"""
        downloader = VideoDownloader()
        task_id = "test_cleanup_task"
        task_dir = downloader.get_task_dir(task_id)

        # 创建目录和文件
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "test_file.txt").touch()

        assert task_dir.exists()

        # 清理
        downloader.cleanup(task_id)

        assert not task_dir.exists()


class TestAudioExtractor:
    """音频提取器测试"""

    def test_extractor_uses_config(self):
        """测试提取器使用配置"""
        extractor = AudioExtractor()
        assert extractor.sample_rate == 16000

    def test_extract_nonexistent_file_raises_error(self):
        """测试提取不存在的文件抛出错误"""
        extractor = AudioExtractor()

        with pytest.raises(AudioExtractError) as exc_info:
            extractor.extract("/nonexistent/video.mp4")

        assert "不存在" in str(exc_info.value)

    def test_check_ffmpeg_available(self):
        """测试检查 ffmpeg 可用性"""
        extractor = AudioExtractor()
        # 这个测试取决于系统是否安装了 ffmpeg
        result = extractor.check_ffmpeg_available()
        assert isinstance(result, bool)


class TestVideoDownloadError:
    """视频下载错误测试"""

    def test_error_message(self):
        """测试错误消息"""
        error = VideoDownloadError("下载失败")
        assert str(error) == "下载失败"


class TestAudioExtractError:
    """音频提取错误测试"""

    def test_error_message(self):
        """测试错误消息"""
        error = AudioExtractError("提取失败")
        assert str(error) == "提取失败"
