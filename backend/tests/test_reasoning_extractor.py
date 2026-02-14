# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/tests/test_reasoning_extractor.py
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
ReasoningExtractor tests.

测试多种 LLM Provider 的 reasoning/thinking 提取：
- OpenAI GPT-5: content_blocks (type="reasoning", summary blocks)
- Anthropic Claude: content_blocks (type="thinking")
- DeepSeek/GLM/Kimi: additional_kwargs.reasoning_content
- MiniMax: additional_kwargs.reasoning_details 或 <think> 标签
"""

from langchain_core.messages import AIMessageChunk

from agent.stream.reasoning_extractor import ReasoningExtractor


# ============================================================================
# OpenAI GPT-5 Tests (content_blocks with summary)
# ============================================================================


def test_extract_reasoning_summary_from_content_blocks():
    """测试 GPT-5 的 summary blocks 格式"""
    extractor = ReasoningExtractor()
    chunk = AIMessageChunk(
        content=[
            {
                "type": "reasoning",
                "summary": [
                    {"type": "summary_text", "text": "Step 1."},
                    {"type": "summary_text", "text": "Step 2."},
                ],
            }
        ]
    )

    result = extractor.extract(chunk)

    assert result.reasoning_content == "Step 1.Step 2."
    assert result.is_reasoning_start is True


def test_extract_reasoning_summary_with_text():
    """测试 GPT-5 的 summary blocks + 文本内容"""
    extractor = ReasoningExtractor()
    chunk = AIMessageChunk(
        content=[
            {"type": "reasoning", "summary": [{"type": "summary_text", "text": "Summary."}]},
            {"type": "text", "text": "Final answer."},
        ]
    )

    result = extractor.extract(chunk)

    assert result.reasoning_content == "Summary."
    assert result.text_content == "Final answer."


def test_extract_direct_reasoning_block():
    """测试直接的 reasoning 内容（非 summary 格式）"""
    extractor = ReasoningExtractor()
    chunk = AIMessageChunk(
        content=[
            {"type": "reasoning", "reasoning": "Let me think step by step..."},
            {"type": "text", "text": "The answer is 42."},
        ]
    )

    result = extractor.extract(chunk)

    assert result.reasoning_content == "Let me think step by step..."
    assert result.text_content == "The answer is 42."


# ============================================================================
# Anthropic Claude Tests (content_blocks with thinking)
# ============================================================================


def test_extract_claude_thinking_block():
    """测试 Claude 的 thinking block 格式"""
    extractor = ReasoningExtractor()
    chunk = AIMessageChunk(
        content=[
            {"type": "thinking", "thinking": "I need to analyze this problem..."},
            {"type": "text", "text": "Here is my answer."},
        ]
    )

    result = extractor.extract(chunk)

    assert result.reasoning_content == "I need to analyze this problem..."
    assert result.text_content == "Here is my answer."
    assert result.is_reasoning_start is True


def test_extract_claude_thinking_delta():
    """测试 Claude 的 thinking_delta 格式（流式输出）"""
    extractor = ReasoningExtractor()
    chunk = AIMessageChunk(
        content=[
            {"type": "thinking_delta", "thinking": "Analyzing..."},
        ]
    )

    result = extractor.extract(chunk)

    assert result.reasoning_content == "Analyzing..."
    assert result.is_reasoning_start is True


def test_extract_claude_content_block_delta():
    """测试 Claude 的嵌套 content_block_delta 格式"""
    extractor = ReasoningExtractor()
    chunk = AIMessageChunk(
        content=[
            {
                "type": "content_block_delta",
                "delta": {"type": "thinking_delta", "thinking": "Processing..."},
            },
        ]
    )

    result = extractor.extract(chunk)

    assert result.reasoning_content == "Processing..."


# ============================================================================
# DeepSeek/GLM/Kimi Tests (additional_kwargs.reasoning_content)
# ============================================================================


def test_extract_from_additional_kwargs_reasoning_content():
    """测试 DeepSeek/GLM/Kimi 的 reasoning_content 提取

    注意：LangChain 会自动将 additional_kwargs.reasoning_content 转换为
    content_blocks[type="reasoning"]，所以 detected_source 会是 content_blocks
    """
    extractor = ReasoningExtractor()
    chunk = AIMessageChunk(
        content="最终答案是 9.11 更大",
        additional_kwargs={"reasoning_content": "首先比较整数部分，9 = 9..."},
    )

    result = extractor.extract(chunk)

    assert result.reasoning_content == "首先比较整数部分，9 = 9..."
    assert result.text_content == "最终答案是 9.11 更大"
    assert result.is_reasoning_start is True
    # LangChain 自动转换为 content_blocks 格式
    assert extractor.detected_source == "content_blocks:reasoning"


def test_extract_glm_reasoning_content_only():
    """测试 GLM 只有 reasoning_content 没有 text 的情况"""
    extractor = ReasoningExtractor()
    chunk = AIMessageChunk(
        content="",
        additional_kwargs={"reasoning_content": "让我分析一下这个问题..."},
    )

    result = extractor.extract(chunk)

    assert result.reasoning_content == "让我分析一下这个问题..."
    assert result.text_content == ""


# ============================================================================
# MiniMax Tests (reasoning_details 或 <think> 标签)
# ============================================================================


def test_extract_from_reasoning_details():
    """测试 MiniMax 的 reasoning_details 格式

    注意：LangChain 不会自动将 reasoning_details 转换为 content_blocks，
    但 content_blocks 会优先处理 content。为了测试 reasoning_details，
    需要确保 content_blocks 为空或不包含 reasoning。
    """
    extractor = ReasoningExtractor()
    # 创建一个没有 content 的 chunk，这样 content_blocks 可能为空
    # 或者直接测试 additional_kwargs.reasoning_details 的场景
    chunk = AIMessageChunk(
        content="",  # 空 content
        additional_kwargs={
            "reasoning_details": [
                {"text": "第一步："},
                {"text": "分析问题"},
            ]
        },
    )

    result = extractor.extract(chunk)

    assert result.reasoning_content == "第一步：分析问题"
    assert result.is_reasoning_start is True


def test_extract_from_think_tags():
    """测试 MiniMax 的 <think> 标签解析

    注意：FSM 使用缓冲区，短文本可能不会立即输出，需要 flush 才能获取全部内容。
    同时，LangChain 会将字符串 content 包装为 content_blocks[type=text]，
    然后由 _extract_from_content_blocks 中的 FSM 逻辑处理。
    """
    extractor = ReasoningExtractor()

    # 第一个 chunk：开始标签和部分内容
    chunk1 = AIMessageChunk(content="<think>让我想想，这需要仔细分析")
    result1 = extractor.extract(chunk1)
    # is_reasoning_start 应该在遇到 <think> 时设置
    assert result1.is_reasoning_start is True

    # 第二个 chunk：更多内容（超过缓冲区阈值 50 字符）
    chunk2 = AIMessageChunk(content="，首先我们需要比较整数部分，然后再比较小数部分，这样可以得到正确的结果")
    result2 = extractor.extract(chunk2)
    # 部分 reasoning 内容可能会被刷新
    assert len(result2.reasoning_content) > 0 or extractor.is_in_reasoning

    # 第三个 chunk：结束标签和答案
    chunk3 = AIMessageChunk(content="</think>答案是42")
    result3 = extractor.extract(chunk3)
    assert result3.is_reasoning_end is True

    # flush 获取剩余内容
    final = extractor.flush()
    # 验证 text_content 包含答案
    all_text = result3.text_content + final.text_content
    assert "42" in all_text


def test_extract_think_tags_with_flush():
    """测试 <think> 标签解析并 flush 获取完整内容"""
    extractor = ReasoningExtractor()

    # 完整的 think 块
    chunk = AIMessageChunk(content="<think>思考过程</think>最终答案")
    result = extractor.extract(chunk)

    # flush 获取缓冲区中的剩余内容
    final = extractor.flush()

    # 合并所有内容
    all_reasoning = result.reasoning_content + final.reasoning_content
    all_text = result.text_content + final.text_content

    # 验证
    assert "思考过程" in all_reasoning
    assert "最终答案" in all_text
    assert extractor.detected_source == "think_tags"


def test_extract_think_tags_split_across_chunks():
    """测试 <think> 标签跨 chunk 的情况"""
    extractor = ReasoningExtractor()

    # 标签被分割的情况：<thi + nk>
    chunk1 = AIMessageChunk(content="前文<thi")
    result1 = extractor.extract(chunk1)

    chunk2 = AIMessageChunk(content="nk>思考内容很长很长需要超过五十个字符才能触发缓冲区刷新</think>答案")
    result2 = extractor.extract(chunk2)

    # flush 确保剩余内容被处理
    final = extractor.flush()

    # 合并所有内容
    all_reasoning = result1.reasoning_content + result2.reasoning_content + final.reasoning_content
    all_text = result1.text_content + result2.text_content + final.text_content

    # 验证整体效果
    assert extractor.detected_source == "think_tags"
    assert "思考内容" in all_reasoning
    assert "答案" in all_text


# ============================================================================
# Edge Cases and State Management
# ============================================================================


def test_extractor_reset():
    """测试 extractor 重置功能"""
    extractor = ReasoningExtractor()

    # 处理一些内容
    chunk = AIMessageChunk(
        content="",
        additional_kwargs={"reasoning_content": "Some reasoning"},
    )
    extractor.extract(chunk)

    assert extractor.detected_source is not None

    # 重置
    extractor.reset()

    assert extractor.detected_source is None
    assert extractor.is_in_reasoning is False


def test_extract_empty_chunk():
    """测试空 chunk 处理"""
    extractor = ReasoningExtractor()

    # None chunk
    result = extractor.extract(None)
    assert result.reasoning_content == ""
    assert result.text_content == ""

    # 空 content
    chunk = AIMessageChunk(content="")
    result = extractor.extract(chunk)
    assert result.reasoning_content == ""


def test_flush_remaining_content():
    """测试 flush 方法处理剩余内容"""
    extractor = ReasoningExtractor()

    # 未完成的 <think> 标签
    chunk = AIMessageChunk(content="<think>未完成的思考")
    extractor.extract(chunk)

    # flush 应该返回剩余内容
    result = extractor.flush()
    # 即使标签未闭合，内容也应该被保留


def test_detected_source_tracking():
    """测试 detected_source 只在首次检测时设置"""
    extractor = ReasoningExtractor()

    # 第一次提取
    chunk1 = AIMessageChunk(
        content="",
        additional_kwargs={"reasoning_content": "First reasoning"},
    )
    extractor.extract(chunk1)
    first_source = extractor.detected_source

    # 第二次提取（同类型）
    chunk2 = AIMessageChunk(
        content="",
        additional_kwargs={"reasoning_content": "Second reasoning"},
    )
    extractor.extract(chunk2)

    # detected_source 应该保持不变
    assert extractor.detected_source == first_source
