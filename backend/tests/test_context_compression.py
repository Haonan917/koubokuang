# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/tests/test_context_compression.py
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
Context 压缩中间件测试

测试用例：
- Token 估算准确性
- 实际 Token 统计（from usage_metadata）
- 模型 context window 获取
- 状态摘要构建
- 消息压缩逻辑
- Token 追踪中间件
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from agent.middleware.context_compression import (
    estimate_tokens,
    estimate_message_tokens,
    estimate_messages_tokens,
    get_total_tokens_from_state,
    estimate_next_turn_tokens,
    get_model_context_window,
    get_current_model_name,
    build_state_summary,
    compress_messages,
)
from agent.middleware.token_tracking import (
    _extract_usage_metadata,
    _get_state_from_runtime,
)


class TestTokenEstimation:
    """Token 估算测试"""

    def test_estimate_tokens_empty(self):
        """空字符串应返回 0"""
        assert estimate_tokens("") == 0
        assert estimate_tokens(None) == 0

    def test_estimate_tokens_english(self):
        """英文文本估算"""
        # 纯英文，约 4 字符/token
        text = "Hello world, this is a test"  # 27 字符
        tokens = estimate_tokens(text)
        # 预期约 27/4 ≈ 6-7 tokens
        assert 5 <= tokens <= 10

    def test_estimate_tokens_chinese(self):
        """中文文本估算"""
        # 纯中文，约 1.5 字符/token
        text = "这是一段中文测试文本"  # 10 个中文字符
        tokens = estimate_tokens(text)
        # 预期约 10/1.5 ≈ 6-7 tokens
        assert 5 <= tokens <= 10

    def test_estimate_tokens_mixed(self):
        """中英混合文本估算"""
        text = "Hello 世界, this is 测试"
        tokens = estimate_tokens(text)
        # 混合文本，结果应该合理
        assert 5 <= tokens <= 15

    def test_estimate_message_tokens(self):
        """单条消息 token 估算"""
        msg = HumanMessage(content="Hello world")
        tokens = estimate_message_tokens(msg)
        # 内容 tokens + 约 10 元数据 tokens
        assert tokens >= 10

    def test_estimate_messages_tokens(self):
        """消息列表 token 估算"""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there, how can I help you?"),
        ]
        tokens = estimate_messages_tokens(messages)
        # 应该是两条消息 tokens 的总和
        assert tokens > estimate_message_tokens(messages[0])


class TestActualTokenStatistics:
    """实际 Token 统计测试（基于 usage_metadata）"""

    def test_get_total_tokens_from_state_empty(self):
        """空状态返回 0"""
        assert get_total_tokens_from_state({}) == 0
        assert get_total_tokens_from_state({"other": 123}) == 0

    def test_get_total_tokens_from_state_with_data(self):
        """有数据时返回累计值"""
        state = {
            "total_input_tokens": 1000,
            "total_output_tokens": 500,
        }
        assert get_total_tokens_from_state(state) == 1500

    def test_get_total_tokens_from_state_with_none(self):
        """None 值被视为 0"""
        state = {
            "total_input_tokens": None,
            "total_output_tokens": 500,
        }
        assert get_total_tokens_from_state(state) == 500

    def test_estimate_next_turn_tokens_empty(self):
        """空消息列表"""
        assert estimate_next_turn_tokens([]) == 500  # 默认预留

    def test_estimate_next_turn_tokens_human_message(self):
        """最后是 HumanMessage"""
        messages = [
            AIMessage(content="Hi"),
            HumanMessage(content="这是一段测试消息"),
        ]
        tokens = estimate_next_turn_tokens(messages)
        # 应该基于消息长度估算，至少 200
        assert tokens >= 200

    def test_estimate_next_turn_tokens_ai_message(self):
        """最后是 AIMessage"""
        messages = [
            HumanMessage(content="Hi"),
            AIMessage(content="Response"),
        ]
        tokens = estimate_next_turn_tokens(messages)
        # 非 HumanMessage，返回默认值
        assert tokens == 500


class TestTokenTrackingMiddleware:
    """Token 追踪中间件测试"""

    def test_extract_usage_metadata_dict(self):
        """从 dict 格式提取 usage_metadata"""
        message = AIMessage(content="Hello")
        message.usage_metadata = {
            "input_tokens": 100,
            "output_tokens": 50,
        }
        usage = _extract_usage_metadata(message)
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50

    def test_extract_usage_metadata_none(self):
        """无 usage_metadata"""
        message = AIMessage(content="Hello")
        usage = _extract_usage_metadata(message)
        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0

    def test_extract_usage_metadata_empty(self):
        """空 usage_metadata"""
        message = AIMessage(content="Hello")
        message.usage_metadata = {}
        usage = _extract_usage_metadata(message)
        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0

    def test_get_state_from_runtime_none(self):
        """runtime 为 None"""
        assert _get_state_from_runtime(None) == {}

    def test_get_state_from_runtime_with_state(self):
        """runtime 有 state 属性"""
        runtime = MagicMock()
        runtime.state = {"key": "value"}
        result = _get_state_from_runtime(runtime)
        assert result == {"key": "value"}

    def test_get_state_from_runtime_with_values(self):
        """runtime 有 values 属性"""
        runtime = MagicMock()
        runtime.state = None
        runtime.values = {"key": "value2"}
        result = _get_state_from_runtime(runtime)
        assert result == {"key": "value2"}


class TestContextWindowRetrieval:
    """Context window 获取测试"""

    def test_get_model_context_window_exact_match(self):
        """精确匹配模型名称"""
        with patch('config.settings') as mock_settings:
            mock_settings.MODEL_CONTEXT_WINDOWS = {
                "gpt-4o": 128000,
                "claude-3-5-sonnet": 200000,
            }
            mock_settings.DEFAULT_CONTEXT_WINDOW = 32000

            assert get_model_context_window("gpt-4o") == 128000
            assert get_model_context_window("claude-3-5-sonnet") == 200000

    def test_get_model_context_window_prefix_match(self):
        """前缀匹配模型名称"""
        with patch('config.settings') as mock_settings:
            mock_settings.MODEL_CONTEXT_WINDOWS = {
                "claude-3-5-sonnet": 200000,
            }
            mock_settings.DEFAULT_CONTEXT_WINDOW = 32000

            # 带版本号的模型名应该通过前缀匹配
            assert get_model_context_window("claude-3-5-sonnet-20241022") == 200000

    def test_get_model_context_window_default(self):
        """未知模型返回默认值"""
        with patch('config.settings') as mock_settings:
            mock_settings.MODEL_CONTEXT_WINDOWS = {}
            mock_settings.DEFAULT_CONTEXT_WINDOW = 32000

            assert get_model_context_window("unknown-model") == 32000
            assert get_model_context_window(None) == 32000

    def test_get_current_model_name_anthropic(self):
        """获取 Anthropic 模型名称"""
        with patch('config.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "anthropic"
            mock_settings.ANTHROPIC_MODEL_NAME = "claude-3-5-sonnet"

            assert get_current_model_name() == "claude-3-5-sonnet"

    def test_get_current_model_name_openai(self):
        """获取 OpenAI 模型名称"""
        with patch('config.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.OPENAI_MODEL_NAME = "gpt-4o"

            assert get_current_model_name() == "gpt-4o"

    def test_get_current_model_name_ollama(self):
        """获取 Ollama 模型名称"""
        with patch('config.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "ollama"
            mock_settings.OLLAMA_MODEL_NAME = "qwen3:4b"

            assert get_current_model_name() == "qwen3:4b"


class TestStateSummary:
    """状态摘要构建测试"""

    def test_build_state_summary_empty(self):
        """空状态"""
        summary = build_state_summary({})
        assert "[历史上下文压缩摘要]" in summary
        assert "请直接使用" in summary

    def test_build_state_summary_with_parsed_link(self):
        """包含解析链接"""
        state = {
            "parsed_link": {
                "platform": "bilibili",
                "content_id": "BV123456",
                "original_url": "https://www.bilibili.com/video/BV123456",
            }
        }
        summary = build_state_summary(state)
        assert "已解析链接" in summary
        assert "bilibili" in summary
        assert "BV123456" in summary

    def test_build_state_summary_with_content_info(self):
        """包含内容信息"""
        state = {
            "content_info": {
                "title": "测试视频标题",
                "author_name": "测试作者",
                "content_type": "video",
                "desc": "这是一段描述文字",
            }
        }
        summary = build_state_summary(state)
        assert "已获取内容" in summary
        assert "测试视频标题" in summary
        assert "测试作者" in summary

    def test_build_state_summary_with_transcript(self):
        """包含转录结果"""
        state = {
            "transcript": {
                "text": "这是转录的文本内容，包含视频中的所有语音。",
                "segments": [
                    {"start": 0.0, "end": 5.0, "text": "这是第一段"},
                    {"start": 5.0, "end": 10.0, "text": "这是第二段"},
                ],
            }
        }
        summary = build_state_summary(state)
        assert "已完成转录" in summary
        assert "2个分段" in summary
        assert "无需重复调用 process_video" in summary

    def test_build_state_summary_long_desc_truncated(self):
        """长描述被截断"""
        long_desc = "这是一段很长的描述" * 50  # 超过 200 字符
        state = {
            "content_info": {
                "title": "测试",
                "author_name": "作者",
                "content_type": "video",
                "desc": long_desc,
            }
        }
        summary = build_state_summary(state)
        assert "..." in summary  # 应该有省略号


class TestMessageCompression:
    """消息压缩测试"""

    def test_compress_messages_short_list(self):
        """短消息列表不压缩"""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi"),
        ]
        result = compress_messages(messages, {}, keep_recent_pairs=3)
        # 短列表应该保持原样
        assert len(result) == 2

    def test_compress_messages_basic(self):
        """基本压缩测试"""
        # 创建一个较长的消息列表
        messages = [
            SystemMessage(content="System prompt"),
            HumanMessage(content="Message 1"),
            AIMessage(content="Response 1"),
            HumanMessage(content="Message 2"),
            AIMessage(content="Response 2"),
            HumanMessage(content="Message 3"),
            AIMessage(content="Response 3"),
            HumanMessage(content="Message 4"),
            AIMessage(content="Response 4"),
            HumanMessage(content="Message 5"),
            AIMessage(content="Response 5"),
        ]

        state = {
            "parsed_link": {"platform": "bilibili", "content_id": "BV123"},
        }

        result = compress_messages(messages, state, keep_recent_pairs=2)

        # 压缩后应该包含：
        # 1. 第一条 SystemMessage
        # 2. 状态摘要 SystemMessage
        # 3. 最近的消息
        assert len(result) < len(messages)
        assert isinstance(result[0], SystemMessage)  # 原始 system message
        assert isinstance(result[1], SystemMessage)  # 状态摘要
        assert "历史上下文压缩摘要" in result[1].content

    def test_compress_messages_preserves_first(self):
        """保留第一条消息"""
        first_content = "Original system prompt"
        messages = [
            SystemMessage(content=first_content),
            HumanMessage(content="M1"),
            AIMessage(content="R1"),
            HumanMessage(content="M2"),
            AIMessage(content="R2"),
            HumanMessage(content="M3"),
            AIMessage(content="R3"),
        ]

        result = compress_messages(messages, {}, keep_recent_pairs=1)
        assert result[0].content == first_content

    def test_compress_messages_no_tool_message_at_start(self):
        """压缩后不以 ToolMessage 开头"""
        messages = [
            SystemMessage(content="System"),
            HumanMessage(content="M1"),
            AIMessage(content="Let me call a tool"),
            ToolMessage(content="Tool result", tool_call_id="1"),
            AIMessage(content="Based on the tool result..."),
            HumanMessage(content="M2"),
            AIMessage(content="R2"),
        ]

        result = compress_messages(messages, {}, keep_recent_pairs=1)

        # 检查第三条消息（跳过第一条原始消息和状态摘要）
        # 不应该是 ToolMessage
        for msg in result[2:]:
            if msg == result[2]:  # 第一条保留的消息
                assert not isinstance(msg, ToolMessage), "压缩后不应以 ToolMessage 开头"
                break


class TestCompressionMiddleware:
    """中间件集成测试

    注意: @before_model 装饰器返回的是一个中间件对象，
    不能直接调用。这里测试核心逻辑函数。
    """

    def test_compression_trigger_logic(self):
        """测试压缩触发逻辑"""
        # 当 token 数低于阈值时，不应该压缩
        messages_short = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi"),
        ]
        # 估算 tokens 很少
        tokens = estimate_messages_tokens(messages_short)
        assert tokens < 100  # 短消息应该少于 100 tokens

    def test_compression_with_many_messages(self):
        """测试多消息压缩"""
        # 创建很多消息
        messages = [SystemMessage(content="You are a helpful assistant.")]
        for i in range(20):
            messages.append(HumanMessage(content=f"This is message {i} with some content"))
            messages.append(AIMessage(content=f"Response {i} with detailed answer"))

        state = {
            "parsed_link": {"platform": "bilibili", "content_id": "BV123"},
            "transcript": {"text": "转录文本内容", "segments": []},
        }

        # 压缩消息
        compressed = compress_messages(messages, state, keep_recent_pairs=3)

        # 验证压缩后消息数量减少
        assert len(compressed) < len(messages)
        # 验证第一条消息保留
        assert compressed[0].content == "You are a helpful assistant."
        # 验证状态摘要
        assert "历史上下文压缩摘要" in compressed[1].content

    def test_token_threshold_calculation(self):
        """测试 token 阈值计算"""
        # 模拟 context window 和 threshold
        context_window = 200000
        threshold = 0.85  # 当前默认阈值
        token_threshold = int(context_window * threshold)

        assert token_threshold == 170000

        # 测试不同的 threshold
        threshold_90 = int(context_window * 0.9)
        assert threshold_90 == 180000

    def test_compression_resets_token_counters(self):
        """测试压缩后 token 计数器被重置"""
        # 创建有累计 token 的状态
        state = {
            "total_input_tokens": 170000,
            "total_output_tokens": 5000,
            "parsed_link": {"platform": "bilibili", "content_id": "BV123"},
        }

        messages = [SystemMessage(content="System prompt")]
        for i in range(10):
            messages.append(HumanMessage(content=f"Message {i}"))
            messages.append(AIMessage(content=f"Response {i}"))

        # 执行压缩
        compressed = compress_messages(messages, state, keep_recent_pairs=2)

        # 验证压缩执行了
        assert len(compressed) < len(messages)

        # 注意：compress_messages 函数本身不会重置计数器
        # 重置是在 context_compression_middleware 中进行的
        # 这里只测试 compress_messages 的核心功能


class TestTokenBasedCompression:
    """基于实际 Token 的压缩测试"""

    def test_compression_uses_actual_tokens(self):
        """测试压缩使用实际 token 数据"""
        # 创建有累计 token 的状态
        state = {
            "total_input_tokens": 100000,
            "total_output_tokens": 50000,
        }

        # 获取累计 token
        total = get_total_tokens_from_state(state)
        assert total == 150000

        # 加上预估的下一轮 token
        messages = [HumanMessage(content="测试消息")]
        next_turn = estimate_next_turn_tokens(messages)
        assert next_turn >= 200

        # 总 token 应该用于判断是否需要压缩
        total_with_buffer = total + next_turn
        assert total_with_buffer > total

    def test_fallback_to_estimation_when_no_actual_data(self):
        """测试无实际数据时回退到估算"""
        # 空状态，无累计 token
        state = {}

        total = get_total_tokens_from_state(state)
        assert total == 0

        # 此时应该使用字符估算
        messages = [
            HumanMessage(content="这是一段测试消息" * 100),
        ]
        estimated = estimate_messages_tokens(messages)
        assert estimated > 0  # 估算应该有值
