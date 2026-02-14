# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/tests/test_asr_service.py
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
ASR 服务测试

测试覆盖:
- MockASRService 基本功能
- ASRService 可用性检查和单例模式
- SegmentBuilder 句子切分逻辑
- Token 和 RawTranscriptResult 数据结构
"""

import pytest

from schemas import Segment, TranscriptResult
from services.asr_service import (
    ASRError,
    ASRService,
    MockASRService,
    RawTranscriptResult,
    SegmentBuilder,
    Token,
)


class TestMockASRService:
    """Mock ASR 服务测试"""

    def test_mock_transcribe_returns_valid_result(self):
        """测试 Mock 服务返回有效结果"""
        service = MockASRService()
        result = service.transcribe("/fake/audio.wav")

        assert result is not None
        assert isinstance(result, TranscriptResult)
        assert result.text != ""
        assert len(result.segments) > 0

    def test_mock_transcribe_segments_have_timestamps(self):
        """测试 Mock 服务返回的分段有时间戳"""
        service = MockASRService()
        result = service.transcribe("/fake/audio.wav")

        for segment in result.segments:
            assert isinstance(segment, Segment)
            assert segment.start >= 0
            assert segment.end > segment.start
            assert segment.text != ""

    def test_mock_is_available(self):
        """测试 Mock 服务总是可用"""
        service = MockASRService()
        assert service.is_available() is True

    def test_mock_preload_no_error(self):
        """测试 Mock 预加载不报错"""
        service = MockASRService()
        service.preload()  # 应该无操作，不抛异常


class TestASRService:
    """ASR 服务测试"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        service1 = ASRService()
        service2 = ASRService()
        assert service1 is service2

    def test_is_available_returns_bool(self):
        """测试可用性检查返回布尔值"""
        service = ASRService()
        result = service.is_available()
        assert isinstance(result, bool)


class TestASRError:
    """ASR 错误测试"""

    def test_error_message(self):
        """测试错误消息"""
        error = ASRError("转录失败")
        assert str(error) == "转录失败"

    def test_error_is_exception(self):
        """测试错误是异常类型"""
        with pytest.raises(ASRError):
            raise ASRError("测试异常")


class TestToken:
    """Token 数据结构测试"""

    def test_token_creation(self):
        """测试 Token 创建"""
        token = Token(text="你好", start_ms=0, end_ms=500)
        assert token.text == "你好"
        assert token.start_ms == 0
        assert token.end_ms == 500

    def test_token_duration(self):
        """测试 Token 时长计算"""
        token = Token(text="世界", start_ms=500, end_ms=1000)
        duration_ms = token.end_ms - token.start_ms
        assert duration_ms == 500


class TestRawTranscriptResult:
    """RawTranscriptResult 数据结构测试"""

    def test_raw_result_with_tokens(self):
        """测试带 tokens 的原始结果"""
        tokens = [
            Token(text="你好", start_ms=0, end_ms=500),
            Token(text="世界", start_ms=500, end_ms=1000),
        ]
        result = RawTranscriptResult(text="你好世界", tokens=tokens)

        assert result.text == "你好世界"
        assert len(result.tokens) == 2
        assert result.vad_segments == []

    def test_raw_result_empty_tokens(self):
        """测试空 tokens 的原始结果"""
        result = RawTranscriptResult(text="测试文本")
        assert result.text == "测试文本"
        assert result.tokens == []
        assert result.vad_segments == []


class TestSegmentBuilder:
    """SegmentBuilder 句子切分测试"""

    @pytest.fixture
    def builder(self):
        """创建默认配置的 SegmentBuilder"""
        return SegmentBuilder(
            max_chars=20,
            max_seconds=6.0,
            min_seconds=0.5,
            gap_split=0.6,
        )

    def test_build_segments_empty_text(self, builder):
        """测试空文本返回空列表"""
        result = RawTranscriptResult(text="")
        segments = builder.build_segments(result)
        assert segments == []

    def test_build_segments_from_tokens_punctuation_split(self, builder):
        """测试按标点切分"""
        tokens = [
            Token(text="你好", start_ms=0, end_ms=500),
            Token(text="世界", start_ms=500, end_ms=1000),
            Token(text="。", start_ms=1000, end_ms=1100),
            Token(text="再见", start_ms=1100, end_ms=1600),
        ]
        result = RawTranscriptResult(text="你好世界。再见", tokens=tokens)
        segments = builder.build_segments(result)

        assert len(segments) == 2
        assert segments[0].text == "你好世界。"
        assert segments[1].text == "再见"

    def test_build_segments_from_tokens_length_split(self, builder):
        """测试按长度切分"""
        # 创建一个超长句子（没有标点）
        tokens = [
            Token(text=f"字{i}", start_ms=i * 100, end_ms=(i + 1) * 100)
            for i in range(25)
        ]
        text = "".join(t.text for t in tokens)
        result = RawTranscriptResult(text=text, tokens=tokens)
        segments = builder.build_segments(result)

        # 应该被切分为多段
        assert len(segments) >= 2
        # 每段不应超过 max_chars
        for seg in segments:
            assert len(seg.text) <= builder.max_chars + 5  # 允许少量溢出

    def test_build_segments_from_tokens_gap_split(self, builder):
        """测试按间隙切分"""
        tokens = [
            Token(text="第一句", start_ms=0, end_ms=500),
            Token(text="第二句", start_ms=2000, end_ms=2500),  # 间隙 1500ms > 600ms
        ]
        result = RawTranscriptResult(text="第一句第二句", tokens=tokens)
        segments = builder.build_segments(result)

        assert len(segments) == 2

    def test_build_segments_timestamps_correct(self, builder):
        """测试时间戳正确转换"""
        tokens = [
            Token(text="测试", start_ms=1000, end_ms=1500),
            Token(text="。", start_ms=1500, end_ms=1600),
        ]
        result = RawTranscriptResult(text="测试。", tokens=tokens)
        segments = builder.build_segments(result)

        assert len(segments) == 1
        assert segments[0].start == 1.0  # 1000ms -> 1.0s
        assert segments[0].end == 1.6  # 1600ms -> 1.6s

    def test_build_segments_min_duration(self, builder):
        """测试最小时长保证"""
        tokens = [
            Token(text="短", start_ms=0, end_ms=100),  # 只有 0.1s
        ]
        result = RawTranscriptResult(text="短", tokens=tokens)
        segments = builder.build_segments(result)

        assert len(segments) == 1
        # 时长应该被扩展到 min_seconds
        duration = segments[0].end - segments[0].start
        assert duration >= builder.min_seconds

    def test_build_segments_text_only_fallback(self, builder):
        """测试无词级时间戳时的回退方案"""
        result = RawTranscriptResult(
            text="第一句话。第二句话。",
            tokens=[],  # 无 tokens
            vad_segments=[(0, 5000)],  # 总时长 5 秒
        )
        segments = builder.build_segments(result)

        assert len(segments) == 2
        assert segments[0].text == "第一句话。"
        assert segments[1].text == "第二句话。"
        # 时间戳按比例分配
        assert segments[0].start == 0.0
        assert segments[1].end == 5.0

    def test_split_by_punctuation_multiple_endings(self, builder):
        """测试多种句子结束标点"""
        result = RawTranscriptResult(
            text="问题吗？是的！结束。",
            tokens=[],
            vad_segments=[(0, 3000)],
        )
        segments = builder.build_segments(result)

        assert len(segments) == 3
        assert "？" in segments[0].text
        assert "！" in segments[1].text
        assert "。" in segments[2].text


class TestSegmentBuilderEdgeCases:
    """SegmentBuilder 边界情况测试"""

    def test_single_char_tokens(self):
        """测试单字符 tokens"""
        builder = SegmentBuilder(max_chars=10)
        tokens = [
            Token(text="我", start_ms=0, end_ms=200),
            Token(text="爱", start_ms=200, end_ms=400),
            Token(text="你", start_ms=400, end_ms=600),
            Token(text="。", start_ms=600, end_ms=700),
        ]
        result = RawTranscriptResult(text="我爱你。", tokens=tokens)
        segments = builder.build_segments(result)

        assert len(segments) == 1
        assert segments[0].text == "我爱你。"

    def test_only_punctuation(self):
        """测试只有标点的情况"""
        builder = SegmentBuilder()
        tokens = [
            Token(text="。", start_ms=0, end_ms=100),
        ]
        result = RawTranscriptResult(text="。", tokens=tokens)
        segments = builder.build_segments(result)

        # 空内容的段应该被过滤
        assert len(segments) <= 1

    def test_mixed_punctuation(self):
        """测试中英文混合标点"""
        builder = SegmentBuilder(max_chars=50)
        tokens = [
            Token(text="Hello", start_ms=0, end_ms=500),
            Token(text="!", start_ms=500, end_ms=600),
            Token(text="你好", start_ms=600, end_ms=1100),
            Token(text="！", start_ms=1100, end_ms=1200),
        ]
        result = RawTranscriptResult(text="Hello!你好！", tokens=tokens)
        segments = builder.build_segments(result)

        assert len(segments) == 2
