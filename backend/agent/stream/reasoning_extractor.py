# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/stream/reasoning_extractor.py
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
ReasoningExtractor - 统一的推理内容提取器

支持多种 LLM Provider 的推理格式：
- Anthropic Claude: content_blocks (type="thinking")
- OpenAI GPT-5: content_blocks (type="reasoning", summary blocks)
- DeepSeek: additional_kwargs.reasoning_content
- GLM-4.7: additional_kwargs.reasoning_content 或 chunk.reasoning_content
- Kimi K2: additional_kwargs.reasoning_content
- MiniMax: <think> 标签 或 reasoning_details

提取优先级：
1. content_blocks (LangChain 1.0 标准化接口)
2. additional_kwargs.reasoning_content (DeepSeek/GLM/Kimi)
2.5 chunk.reasoning_content (某些 LangChain 版本的 GLM 适配)
3. additional_kwargs.reasoning_details (MiniMax API)
4. ThinkTagFSM 状态机解析 (MiniMax <think> 标签)
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional, Set

from langchain_core.messages import AIMessageChunk

from agent.stream.think_tag_fsm import ThinkTagFSM

logger = logging.getLogger(__name__)


# LangChain content_blocks 支持的推理类型
_REASONING_BLOCK_TYPES: Set[str] = frozenset({
    "reasoning",      # OpenAI GPT-5 / LangChain 标准 / 从 additional_kwargs.reasoning_content 转换
    "thinking",       # Anthropic Claude Extended Thinking
    "non_standard",   # LangChain 对未知类型的包装（内部可能包含 thinking/reasoning）
})

# LangChain content_blocks 支持的文本类型
_TEXT_BLOCK_TYPES: Set[str] = frozenset({
    "text",
    "text_delta",
})


@dataclass
class ReasoningResult:
    """推理提取结果

    Attributes:
        reasoning_content: 提取的推理/思考内容
        text_content: 提取的文本内容
        is_reasoning_start: 是否是推理块开始
        is_reasoning_end: 是否是推理块结束
    """
    reasoning_content: str = ""
    text_content: str = ""
    is_reasoning_start: bool = False
    is_reasoning_end: bool = False


class ReasoningExtractor:
    """统一的推理内容提取器

    自动检测 LLM Provider 的推理格式并提取内容。

    提取优先级：
    1. content_blocks (LangChain 1.0 标准化接口)
       - type="reasoning" -> reasoning_content (OpenAI GPT-5)
       - type="thinking" -> reasoning_content (Anthropic Claude)
    2. additional_kwargs.reasoning_content (DeepSeek/GLM/Kimi)
    3. ThinkTagFSM 状态机解析 (MiniMax <think> 标签)

    使用方式：
    ```python
    extractor = ReasoningExtractor()

    async for event in agent.astream_events(...):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            result = extractor.extract(chunk)

            if result.is_reasoning_start:
                yield reasoning_start_event()
            if result.reasoning_content:
                yield reasoning_delta_event(result.reasoning_content)
            if result.is_reasoning_end:
                yield reasoning_finish_event()
            if result.text_content:
                yield text_delta_event(result.text_content)

    # 流结束时刷新
    final = extractor.flush()
    ```
    """

    def __init__(self):
        self._fsm = ThinkTagFSM()
        self._detected_source: Optional[str] = None

    def reset(self) -> None:
        """重置提取器状态"""
        self._fsm.reset()
        self._detected_source = None

    @property
    def detected_source(self) -> Optional[str]:
        """检测到的推理来源（用于调试）"""
        return self._detected_source

    @property
    def is_in_reasoning(self) -> bool:
        """是否在推理块内"""
        return self._fsm.is_in_thinking

    def extract(self, chunk: AIMessageChunk) -> ReasoningResult:
        """从 AIMessageChunk 提取推理和文本内容

        Args:
            chunk: LangChain AIMessageChunk

        Returns:
            ReasoningResult: 包含提取的 reasoning/text 内容和状态标志
        """
        if chunk is None:
            return ReasoningResult()

        # 1. 优先检查 content_blocks (LangChain 1.0 标准)
        if hasattr(chunk, 'content_blocks') and chunk.content_blocks:
            result = self._extract_from_content_blocks(chunk.content_blocks)
            # 注意：即使没有内容输出，也要检查状态标志和 FSM 状态
            # FSM 可能已识别 <think> 开始但内容在缓冲区中
            # 或者 FSM 正在处理跨 chunk 的标签（has_pending_state）
            if (result.reasoning_content or result.text_content or
                result.is_reasoning_start or result.is_reasoning_end or
                self._fsm.has_pending_state):
                return result
            # 如果 content_blocks 解析完全为空且 FSM 无待处理状态，继续尝试其他方式

        # 2. 检查 additional_kwargs.reasoning_content (DeepSeek/GLM/Kimi)
        additional_kwargs = getattr(chunk, "additional_kwargs", {}) or {}
        if "reasoning_content" in additional_kwargs:
            return self._extract_from_reasoning_content(chunk, additional_kwargs)

        # 2.5 检查 chunk 直接属性 reasoning_content (某些 LangChain 版本的 GLM 适配)
        # GLM 流式输出可能将 reasoning_content 作为 chunk 的直接属性
        if hasattr(chunk, "reasoning_content") and chunk.reasoning_content:
            if not self._detected_source:
                self._detected_source = "chunk:reasoning_content"
                logger.debug(f"Detected reasoning source: {self._detected_source}")
            return ReasoningResult(
                reasoning_content=chunk.reasoning_content,
                text_content=getattr(chunk, "content", "") if isinstance(getattr(chunk, "content", ""), str) else "",
                is_reasoning_start=True,
            )

        # 3. 检查 additional_kwargs.reasoning_details (MiniMax API)
        if "reasoning_details" in additional_kwargs:
            return self._extract_from_reasoning_details(chunk, additional_kwargs)

        # 4. 使用 ThinkTagFSM 解析 <think> 标签 (MiniMax 默认输出)
        content = getattr(chunk, "content", "")
        if isinstance(content, str) and content:
            return self._extract_from_think_tags(content)

        # 5. 处理 Anthropic 的特殊 content 格式 (list of blocks)
        content = getattr(chunk, "content", None)
        if isinstance(content, list):
            return self._extract_from_anthropic_blocks(content)

        return ReasoningResult()

    def _extract_from_content_blocks(self, content_blocks: list) -> ReasoningResult:
        """从 LangChain content_blocks 提取

        content_blocks 是 LangChain 1.0 标准化的接口，
        所有 Provider 的推理内容都会被转换为统一格式。
        """
        result = ReasoningResult()

        for block in content_blocks:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type", "")

            if block_type in _REASONING_BLOCK_TYPES:
                # reasoning, thinking, 或 non_standard
                content = self._extract_reasoning_text(block)
                if content:
                    # 对于 non_standard 类型，尝试识别内部的真实类型
                    actual_type = block_type
                    if block_type == "non_standard":
                        value = block.get("value", {})
                        if isinstance(value, dict):
                            actual_type = f"non_standard:{value.get('type', 'unknown')}"
                    if not self._detected_source:
                        self._detected_source = f"content_blocks:{actual_type}"
                        logger.debug(f"Detected reasoning source: {self._detected_source}")
                    result.reasoning_content += content
                    result.is_reasoning_start = True

            elif block_type in _TEXT_BLOCK_TYPES:
                text = block.get("text", "")
                if text:
                    # 检查是否需要使用 FSM 解析 <think> 标签
                    # 注意：使用 "<" 而不是 "<think"，以处理跨 chunk 分割的标签
                    # 例如：chunk1 = "<thi", chunk2 = "nk>..."
                    # has_pending_state 检查 FSM 是否处于 IN_TAG/IN_THINK 状态
                    if "<" in text or self._fsm.has_pending_state:
                        # 使用 FSM 解析
                        fsm_result = self._fsm.process(text)
                        # 当 FSM 识别到 <think> 开始或正在思考时设置 detected_source
                        if not self._detected_source and (fsm_result.is_reasoning_start or self._fsm.is_in_thinking):
                            self._detected_source = "think_tags"
                            logger.debug(f"Detected reasoning source: {self._detected_source}")
                        result.reasoning_content += fsm_result.reasoning_content
                        result.text_content += fsm_result.text_content
                        result.is_reasoning_start = result.is_reasoning_start or fsm_result.is_reasoning_start
                        result.is_reasoning_end = fsm_result.is_reasoning_end
                    else:
                        result.text_content += text

        return result

    @staticmethod
    def _extract_reasoning_text(block: dict) -> str:
        """从 reasoning/thinking/non_standard block 中提取推理文本

        兼容多种格式：
        1. OpenAI GPT-5 Responses API summary 格式：
           {"type": "reasoning", "summary": [{"type": "summary_text", "text": "..."}]}
        2. Claude thinking 格式：
           {"type": "thinking", "thinking": "..."}
        3. LangChain non_standard 包装格式：
           {"type": "non_standard", "value": {"type": "thinking", "thinking": "..."}}
        4. LangChain 从 additional_kwargs.reasoning_content 转换的格式：
           {"type": "reasoning", "reasoning": "..."}
        """
        # 处理 non_standard 包装类型
        if block.get("type") == "non_standard":
            value = block.get("value", {})
            if isinstance(value, dict):
                # 递归提取内部的 reasoning/thinking
                inner_type = value.get("type", "")
                if inner_type in ("thinking", "reasoning"):
                    return value.get("thinking", "") or value.get("reasoning", "")
            return ""

        # 直接提取 reasoning 或 thinking 字段
        content = block.get("reasoning", "") or block.get("thinking", "")
        if content:
            return content

        # 处理 OpenAI Responses API 的 summary 格式
        summary = block.get("summary")
        if isinstance(summary, list):
            parts = []
            for item in summary:
                if isinstance(item, dict):
                    text = item.get("text", "")
                    if text:
                        parts.append(text)
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)

        return ""

    def _extract_from_reasoning_content(
        self,
        chunk: AIMessageChunk,
        additional_kwargs: dict
    ) -> ReasoningResult:
        """从 additional_kwargs.reasoning_content 提取 (DeepSeek/GLM/Kimi)"""
        result = ReasoningResult()

        reasoning = additional_kwargs.get("reasoning_content", "")
        if reasoning:
            if not self._detected_source:
                self._detected_source = "additional_kwargs:reasoning_content"
                logger.debug(f"Detected reasoning source: {self._detected_source}")
            result.reasoning_content = reasoning
            result.is_reasoning_start = True

        # 同时提取文本内容
        content = getattr(chunk, "content", "")
        if isinstance(content, str) and content:
            result.text_content = content

        return result

    def _extract_from_reasoning_details(
        self,
        chunk: AIMessageChunk,
        additional_kwargs: dict
    ) -> ReasoningResult:
        """从 additional_kwargs.reasoning_details 提取 (MiniMax API)"""
        result = ReasoningResult()

        reasoning_details = additional_kwargs.get("reasoning_details", [])
        if reasoning_details:
            if not self._detected_source:
                self._detected_source = "additional_kwargs:reasoning_details"
                logger.debug(f"Detected reasoning source: {self._detected_source}")

            for detail in reasoning_details:
                if isinstance(detail, dict):
                    result.reasoning_content += detail.get("text", "")
                elif isinstance(detail, str):
                    result.reasoning_content += detail

            if result.reasoning_content:
                result.is_reasoning_start = True

        # 同时提取文本内容
        content = getattr(chunk, "content", "")
        if isinstance(content, str) and content:
            result.text_content = content

        return result

    def _extract_from_think_tags(self, content: str) -> ReasoningResult:
        """使用 ThinkTagFSM 解析 <think> 标签"""
        fsm_result = self._fsm.process(content)

        # 当 FSM 识别到 <think> 开始或正在思考时设置 detected_source
        # 注意：需要在 process 之后检查，因为标签可能跨 chunk 完成
        if not self._detected_source and (fsm_result.is_reasoning_start or self._fsm.is_in_thinking):
            self._detected_source = "think_tags"
            logger.debug(f"Detected reasoning source: {self._detected_source}")

        return ReasoningResult(
            reasoning_content=fsm_result.reasoning_content,
            text_content=fsm_result.text_content,
            is_reasoning_start=fsm_result.is_reasoning_start,
            is_reasoning_end=fsm_result.is_reasoning_end,
        )

    def _extract_from_anthropic_blocks(self, content: list) -> ReasoningResult:
        """从 Anthropic 特殊的 content 列表格式提取

        Anthropic 的 content 可能是：
        - {"type": "thinking", "thinking": "..."}
        - {"type": "text", "text": "..."}
        - {"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "..."}}
        """
        result = ReasoningResult()

        for block in content:
            if not isinstance(block, dict):
                if isinstance(block, str):
                    result.text_content += block
                continue

            block_type = block.get("type", "")

            # 处理直接格式
            if block_type == "thinking" or block_type == "thinking_delta":
                if not self._detected_source:
                    self._detected_source = "anthropic:thinking"
                    logger.debug(f"Detected reasoning source: {self._detected_source}")
                result.reasoning_content += block.get("thinking", "")
                result.is_reasoning_start = True

            elif block_type == "text" or block_type == "text_delta":
                result.text_content += block.get("text", "")

            # 处理嵌套的 delta 结构
            elif block_type == "content_block_delta":
                delta = block.get("delta", {})
                if isinstance(delta, dict):
                    delta_type = delta.get("type", "")
                    if delta_type == "thinking_delta":
                        if not self._detected_source:
                            self._detected_source = "anthropic:thinking_delta"
                            logger.debug(f"Detected reasoning source: {self._detected_source}")
                        result.reasoning_content += delta.get("thinking", "")
                        result.is_reasoning_start = True
                    elif delta_type == "text_delta":
                        result.text_content += delta.get("text", "")

        return result

    def flush(self) -> ReasoningResult:
        """刷新缓冲区（流结束时调用）

        Returns:
            ReasoningResult: 包含剩余的 reasoning/text 内容
        """
        fsm_result = self._fsm.flush()

        return ReasoningResult(
            reasoning_content=fsm_result.reasoning_content,
            text_content=fsm_result.text_content,
            is_reasoning_start=False,
            is_reasoning_end=fsm_result.is_reasoning_end,
        )
