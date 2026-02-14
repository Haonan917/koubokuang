# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/utils/chat_openai_with_reasoning.py
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
ChatOpenAI with reasoning_content support.

LangChain 的 ChatOpenAI 默认不处理 Kimi/GLM 等模型返回的 reasoning_content 字段。
这个子类通过重写流式处理方法，将 reasoning_content 添加到 additional_kwargs 中，
使得 ReasoningExtractor 能够正确提取 thinking 内容。

支持的模型:
- Kimi K2 (kimi-k2-thinking)
- GLM-4.7 (glm-4.7, glm-4.7-thinking)
- 其他返回 delta.reasoning_content 的 OpenAI 兼容模型

用法:
    from utils.chat_openai_with_reasoning import ChatOpenAIWithReasoning

    llm = ChatOpenAIWithReasoning(
        api_key="...",
        base_url="https://api.moonshot.cn/v1",
        model="kimi-k2-thinking",
        extra_body={"reasoning": True},
    )
"""

from typing import Any, AsyncIterator

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models.chat_models import generate_from_stream
from langchain_core.messages import BaseMessage, AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI


class ChatOpenAIWithReasoning(ChatOpenAI):
    """ChatOpenAI 子类，支持 reasoning_content 字段。

    重写流式处理方法，将 Kimi/GLM 等模型返回的 delta.reasoning_content
    添加到 AIMessageChunk.additional_kwargs["reasoning_content"] 中。
    """

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        """重写以支持 reasoning_content 字段。"""
        # 调用父类方法获取基本的 generation chunk
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )

        if generation_chunk is None:
            return None

        # 检查 chunk 中是否有 reasoning_content
        choices = chunk.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            if delta and "reasoning_content" in delta:
                reasoning_content = delta["reasoning_content"]
                if reasoning_content:
                    # 将 reasoning_content 添加到 additional_kwargs
                    if isinstance(generation_chunk.message, AIMessageChunk):
                        generation_chunk.message.additional_kwargs["reasoning_content"] = reasoning_content

        return generation_chunk

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        *,
        stream_usage: bool | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """重写 _astream 以使用自定义的 chunk 转换。

        这个方法大部分逻辑与父类相同，只是使用了重写的 _convert_chunk_to_generation_chunk。
        """
        # 复用父类的流式处理逻辑
        async for chunk in super()._astream(
            messages,
            stop=stop,
            run_manager=run_manager,
            stream_usage=stream_usage,
            **kwargs,
        ):
            yield chunk

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """重写 _agenerate 以使用流式处理并正确聚合 reasoning_content。"""
        # 使用流式处理来获取完整响应
        # 这样可以确保 reasoning_content 被正确处理
        if kwargs.get("stream", False) or self.streaming:
            stream_iter = self._astream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
            return await generate_from_stream(stream_iter)

        # 对于非流式调用，使用父类方法
        return await super()._agenerate(
            messages, stop=stop, run_manager=run_manager, **kwargs
        )
