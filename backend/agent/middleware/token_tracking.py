# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/middleware/token_tracking.py
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
Token 追踪中间件

在每次 LLM 调用后，从 AIMessage.usage_metadata 提取真实的 token 使用量，
累加到 Agent 状态中，供 Context 压缩中间件使用。

基于 LangChain 1.0 的 @after_model 中间件模式实现。

签名说明：
- @after_model 接收 (state, runtime) 参数
- 返回 dict[str, Any] 状态更新，Command，或 None
"""

from typing import Dict, Any, Optional

from langchain.agents.middleware import after_model
from langchain_core.messages import AIMessage

from utils.logger import logger


def _extract_usage_metadata(message: AIMessage) -> Dict[str, int]:
    """
    从 AIMessage 提取 usage_metadata

    Args:
        message: AIMessage 对象

    Returns:
        包含 input_tokens 和 output_tokens 的字典
    """
    usage = {"input_tokens": 0, "output_tokens": 0}

    if not hasattr(message, 'usage_metadata') or not message.usage_metadata:
        return usage

    metadata = message.usage_metadata

    # LangChain UsageMetadata 可能是 dict 或 TypedDict
    if isinstance(metadata, dict):
        usage["input_tokens"] = metadata.get("input_tokens", 0)
        usage["output_tokens"] = metadata.get("output_tokens", 0)
    else:
        # 尝试作为对象访问
        usage["input_tokens"] = getattr(metadata, "input_tokens", 0) or 0
        usage["output_tokens"] = getattr(metadata, "output_tokens", 0) or 0

    return usage


def _get_state_from_runtime(runtime: Any) -> Dict[str, Any]:
    """
    从 runtime 获取 Agent 状态

    Args:
        runtime: Runtime 对象

    Returns:
        Agent 状态字典
    """
    if runtime is None:
        return {}

    # 尝试不同的属性名获取状态
    if hasattr(runtime, 'state') and runtime.state is not None:
        return runtime.state
    if hasattr(runtime, 'values') and runtime.values is not None:
        return runtime.values

    return {}


@after_model
def token_tracking_middleware(state: Dict[str, Any], runtime: Any) -> Optional[Dict[str, Any]]:
    """
    Token 追踪中间件

    在每次模型调用后追踪 token 使用量。
    从 state["messages"] 中最新的 AIMessage 提取 usage_metadata，
    累加到 Agent 状态中。

    实现 LangChain 1.0 的 @after_model 中间件模式。

    Args:
        state: Agent 状态字典，包含 messages 等字段
        runtime: Runtime 对象

    Returns:
        状态更新字典（包含累加后的 token 计数），或 None 表示无需更新
    """
    # 获取消息列表
    messages = state.get("messages", [])
    if not messages:
        return None

    # 获取最新的消息
    last_message = messages[-1]

    # 只处理 AIMessage
    if not isinstance(last_message, AIMessage):
        return None

    # 提取 usage_metadata
    usage = _extract_usage_metadata(last_message)

    input_tokens = usage["input_tokens"]
    output_tokens = usage["output_tokens"]

    # 如果没有 usage 数据，直接返回
    if input_tokens == 0 and output_tokens == 0:
        logger.debug("[TokenTracking] No usage_metadata in AIMessage")
        return None

    # 累加 token 数量
    prev_input = state.get('total_input_tokens', 0) or 0
    prev_output = state.get('total_output_tokens', 0) or 0

    new_input = prev_input + input_tokens
    new_output = prev_output + output_tokens

    total_tokens = input_tokens + output_tokens
    cumulative_total = new_input + new_output

    logger.debug(
        f"[TokenTracking] +{total_tokens} tokens "
        f"(input: {input_tokens}, output: {output_tokens}), "
        f"cumulative: {cumulative_total}"
    )

    # 返回状态更新
    return {
        "total_input_tokens": new_input,
        "total_output_tokens": new_output,
    }


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "token_tracking_middleware",
    # 工具函数（用于测试）
    "_extract_usage_metadata",
    "_get_state_from_runtime",
]
