# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/middleware/context_compression.py
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
Context 压缩中间件

当 LLM 的 token 数量接近上限时自动压缩历史消息，保留关键状态信息。

基于 LangChain 1.0 的 @before_model 中间件模式实现。

策略：
1. 保留第一条消息（通常是 SystemMessage 或初始 HumanMessage）
2. 插入状态摘要（结构化信息，避免重复调用工具）
3. 保留最近 N 对消息（保持对话连贯性）

签名说明：
- @before_model 接收 (state, runtime) 参数
- 返回 dict[str, Any] 状态更新，Command，或 None
"""

from typing import List, Optional, Dict, Any

from langchain.agents.middleware import before_model
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from utils.logger import logger


# ============================================================================
# Token 估算（用于回退和预估）
# ============================================================================

def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量

    使用简化的估算方法，仅在无法获取实际 token 数据时使用。
    实际 token 数据应优先从 AIMessage.usage_metadata 获取。

    Args:
        text: 要估算的文本

    Returns:
        估算的 token 数量
    """
    if not text:
        return 0

    # 统计中文字符数
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    # 非中文字符数
    other_chars = len(text) - chinese_chars

    # 中文：约 1.5 字符/token
    # 其他：约 4 字符/token (英文词平均 4 字符，1词约1token)
    chinese_tokens = chinese_chars / 1.5
    other_tokens = other_chars / 4

    return int(chinese_tokens + other_tokens)


def estimate_message_tokens(message: BaseMessage) -> int:
    """
    估算单条消息的 token 数量

    Args:
        message: LangChain 消息对象

    Returns:
        估算的 token 数量
    """
    content = message.content if isinstance(message.content, str) else str(message.content)
    # 消息元数据约 10 tokens
    return estimate_tokens(content) + 10


def estimate_messages_tokens(messages: List[BaseMessage]) -> int:
    """
    估算消息列表的总 token 数量

    Args:
        messages: 消息列表

    Returns:
        总 token 数量
    """
    return sum(estimate_message_tokens(msg) for msg in messages)


# ============================================================================
# 实际 Token 统计（优先使用）
# ============================================================================

def get_total_tokens_from_state(state: Dict[str, Any]) -> int:
    """
    从 Agent 状态中获取累计的实际 token 数

    这些数据由 token_tracking_middleware 从 AIMessage.usage_metadata 累加。

    Args:
        state: Agent 状态字典

    Returns:
        累计的 token 数量（input + output）
    """
    input_tokens = state.get('total_input_tokens', 0) or 0
    output_tokens = state.get('total_output_tokens', 0) or 0
    return input_tokens + output_tokens


def estimate_next_turn_tokens(messages: List[BaseMessage]) -> int:
    """
    估算下一轮对话的 token 数

    对于新的 HumanMessage（还没有 usage_metadata），
    使用简化估算作为缓冲。

    Args:
        messages: 当前消息列表

    Returns:
        预估的下一轮 token 数
    """
    if not messages:
        return 500  # 默认预留

    last_msg = messages[-1]
    if isinstance(last_msg, HumanMessage):
        content = last_msg.content if isinstance(last_msg.content, str) else str(last_msg.content)
        # 简化估算：中英混合约 2.5 字符/token
        estimated = len(content) // 2 + 100  # 加 100 作为 buffer
        return max(estimated, 200)  # 至少 200 tokens

    return 500  # 默认预留


# ============================================================================
# 模型 Context Window 获取
# ============================================================================

def get_model_context_window(model_name: Optional[str] = None) -> int:
    """
    获取模型的 context window 大小

    优先从配置文件的 MODEL_CONTEXT_WINDOWS 查找，
    找不到则使用 DEFAULT_CONTEXT_WINDOW。

    Args:
        model_name: 模型名称（可选）

    Returns:
        context window 大小（token 数）
    """
    from config import settings

    if not model_name:
        return settings.DEFAULT_CONTEXT_WINDOW

    # 尝试精确匹配
    context_windows = settings.MODEL_CONTEXT_WINDOWS
    if model_name in context_windows:
        return context_windows[model_name]

    # 尝试前缀匹配（如 "claude-3-5-sonnet-20241022" 匹配 "claude-3-5-sonnet"）
    for key, value in context_windows.items():
        if model_name.startswith(key):
            return value

    return settings.DEFAULT_CONTEXT_WINDOW


def get_current_model_name() -> Optional[str]:
    """
    获取当前配置的模型名称

    优先从数据库获取激活的配置，否则回退到 settings。
    这与 llm_provider.py 的行为保持一致，确保 context window 计算正确。

    Returns:
        模型名称或 None
    """
    from config import settings

    # 尝试从数据库获取激活配置（与 llm_provider.py 保持一致）
    try:
        import pymysql
        conn = pymysql.connect(
            host=settings.AGENT_DB_HOST or "localhost",
            port=settings.AGENT_DB_PORT or 3306,
            user=settings.AGENT_DB_USER or "root",
            password=settings.AGENT_DB_PASSWORD or "",
            database=settings.AGENT_DB_NAME,
            charset="utf8mb4",
            connect_timeout=5,
        )
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT model_name FROM llm_configs WHERE is_active = 1 LIMIT 1
                """)
                result = cursor.fetchone()
                if result:
                    logger.debug(f"[ContextCompression] Got model from DB: {result['model_name']}")
                    return result['model_name']
        finally:
            conn.close()
    except Exception as e:
        logger.debug(f"[ContextCompression] Failed to get model from DB: {e}, falling back to settings")

    # 回退到 settings 配置
    provider = settings.LLM_PROVIDER.lower()
    if provider == "anthropic":
        return settings.ANTHROPIC_MODEL_NAME
    elif provider == "openai":
        return settings.OPENAI_MODEL_NAME
    elif provider == "deepseek":
        return settings.DEEPSEEK_MODEL_NAME
    elif provider == "ollama":
        return settings.OLLAMA_MODEL_NAME
    return None


# ============================================================================
# 状态摘要构建
# ============================================================================

def build_state_summary(state: Dict[str, Any]) -> str:
    """
    构建关键状态摘要

    从 Agent 状态中提取关键信息，生成摘要文本。
    摘要中明确提示 Agent 复用已有数据，避免重复工具调用。

    Args:
        state: Agent 状态字典

    Returns:
        状态摘要文本
    """
    summary_parts = ["[历史上下文压缩摘要]"]
    summary_parts.append("以下是之前对话中获取的关键数据，请直接使用，无需重复调用工具：")
    summary_parts.append("")

    # 1. 解析的链接信息
    parsed_link = state.get("parsed_link")
    if parsed_link:
        platform = parsed_link.get("platform", "未知")
        content_id = parsed_link.get("content_id", "未知")
        original_url = parsed_link.get("original_url", "")
        summary_parts.append(f"- **已解析链接**: 平台={platform}, 内容ID={content_id}")
        if original_url:
            summary_parts.append(f"  原始URL: {original_url}")

    # 2. 内容信息
    content_info = state.get("content_info")
    if content_info:
        title = content_info.get("title", "未知")
        author = content_info.get("author_name", "未知")
        content_type = content_info.get("content_type", "未知")
        desc = content_info.get("desc", "")

        summary_parts.append(f"- **已获取内容**: 《{title}》")
        summary_parts.append(f"  作者: {author}, 类型: {content_type}")
        if desc:
            # 描述可能很长，只保留前 200 字符
            desc_preview = desc[:200] + "..." if len(desc) > 200 else desc
            summary_parts.append(f"  描述: {desc_preview}")

    # 3. 转录结果
    transcript = state.get("transcript")
    if transcript:
        text = transcript.get("text", "")
        segments = transcript.get("segments", [])
        char_count = len(text)
        segment_count = len(segments)

        summary_parts.append(f"- **已完成转录**: {char_count}字, {segment_count}个分段")
        summary_parts.append("  ⚠️ 转录数据已存在，无需重复调用 process_video")

        # 添加转录内容摘要（前 500 字符）
        if text:
            text_preview = text[:500] + "..." if len(text) > 500 else text
            summary_parts.append(f"  转录内容预览: {text_preview}")

    # 4. 当前阶段
    current_stage = state.get("current_stage")
    if current_stage:
        summary_parts.append(f"- **当前阶段**: {current_stage}")

    summary_parts.append("")
    summary_parts.append("---")
    summary_parts.append("")

    return "\n".join(summary_parts)


# ============================================================================
# 消息压缩
# ============================================================================

def compress_messages(
    messages: List[BaseMessage],
    state: Dict[str, Any],
    keep_recent_pairs: int = 3,
) -> List[BaseMessage]:
    """
    压缩消息列表

    策略：
    1. 保留第一条消息（SystemMessage 或初始 HumanMessage）
    2. 插入状态摘要（结构化信息）
    3. 保留最近 N 对消息

    Args:
        messages: 原始消息列表
        state: Agent 状态字典
        keep_recent_pairs: 保留的最近消息对数

    Returns:
        压缩后的消息列表
    """
    if len(messages) <= 2:
        return messages

    compressed = []

    # 1. 保留第一条消息
    first_msg = messages[0]
    compressed.append(first_msg)

    # 2. 构建并插入状态摘要
    # 使用 HumanMessage 而非 SystemMessage，避免 Anthropic API 的
    # "Received multiple non-consecutive system messages" 错误
    summary_text = build_state_summary(state)
    summary_msg = HumanMessage(content=summary_text)
    compressed.append(summary_msg)

    # 3. 收集最近的消息
    # 计算需要保留的消息数量（对数 * 2，因为一对包含 Human + AI）
    # 但实际上消息可能包含 ToolMessage，所以我们从后往前收集
    keep_count = keep_recent_pairs * 2

    # 从后往前收集消息，但要保证完整性（不要截断 tool 调用）
    recent_messages = []
    remaining = messages[1:]  # 跳过第一条

    # 简单策略：保留最后 N*2+2 条消息（额外 2 条作为 buffer）
    if len(remaining) > keep_count + 2:
        recent_messages = remaining[-(keep_count + 2):]
    else:
        recent_messages = remaining

    # 确保不以 ToolMessage 开头（这会导致上下文不完整）
    while recent_messages and isinstance(recent_messages[0], ToolMessage):
        recent_messages = recent_messages[1:]

    compressed.extend(recent_messages)

    return compressed


# ============================================================================
# 中间件主体
# ============================================================================

@before_model
def context_compression_middleware(state: Dict[str, Any], runtime: Any) -> Optional[Dict[str, Any]]:
    """
    Context 压缩中间件

    在每次模型调用前检查 token 数量，必要时压缩历史消息。

    **改进后的 Token 计算逻辑**:
    1. 优先使用累计的实际 token 数（来自 AIMessage.usage_metadata）
    2. 如果无实际数据，回退到字符估算
    3. 加上下一轮对话的预估 token 作为缓冲

    实现 LangChain 1.0 的 @before_model 中间件模式。

    Args:
        state: Agent 状态字典，包含 messages 等字段
        runtime: Runtime 对象，包含 context 等信息

    Returns:
        状态更新字典（包含压缩后的 messages），或 None 表示无需更新
    """
    from config import settings

    # 检查是否启用
    if not settings.CONTEXT_COMPRESSION_ENABLED:
        return None

    messages = state.get("messages", [])
    if not messages:
        return None

    # 获取模型 context window 和阈值
    model_name = get_current_model_name()
    context_window = get_model_context_window(model_name)
    threshold = settings.CONTEXT_COMPRESSION_THRESHOLD
    keep_pairs = settings.CONTEXT_KEEP_RECENT_PAIRS

    # 计算阈值
    token_threshold = int(context_window * threshold)

    # 计算 token 数量
    # 优先使用累计的实际 token 数（来自 token_tracking_middleware）
    actual_tokens = get_total_tokens_from_state(state)

    # 检测是否为新对话开始（消息数量很少时使用估算而非累计值）
    # 当使用相同 session_id 恢复会话时，checkpointer 会从数据库加载旧状态，
    # 包括前一个会话的累计 token 数，这会导致刚开始就触发压缩
    if len(messages) <= 3 and actual_tokens > 0:
        logger.debug(
            f"[ContextCompression] New conversation detected ({len(messages)} messages), "
            f"ignoring stale token count ({actual_tokens})"
        )
        actual_tokens = 0

    if actual_tokens > 0:
        # 有实际数据：使用累计值 + 下一轮预估
        estimated_next = estimate_next_turn_tokens(messages)
        total_tokens = actual_tokens + estimated_next
        token_source = "actual"
    else:
        # 无实际数据（第一次调用或状态未初始化）：回退到字符估算
        total_tokens = estimate_messages_tokens(messages)
        estimated_next = 0
        token_source = "estimated"

    # 判断是否需要压缩
    if total_tokens < token_threshold:
        return None

    # 需要压缩
    if token_source == "actual":
        logger.info(
            f"[ContextCompression] Triggering compression: "
            f"actual {actual_tokens} + next ~{estimated_next} = {total_tokens} tokens "
            f">= {token_threshold} threshold ({threshold*100:.0f}% of {context_window})"
        )
    else:
        logger.info(
            f"[ContextCompression] Triggering compression (fallback estimate): "
            f"{total_tokens} tokens >= {token_threshold} threshold "
            f"({threshold*100:.0f}% of {context_window})"
        )

    # 执行压缩
    compressed_messages = compress_messages(messages, state, keep_pairs)

    # 计算压缩后的 token 数（用于日志）
    compressed_tokens = estimate_messages_tokens(compressed_messages)

    logger.info(
        f"[ContextCompression] Compressed: "
        f"{len(messages)} -> {len(compressed_messages)} messages, "
        f"~{total_tokens} -> ~{compressed_tokens} tokens"
    )

    # 返回状态更新：压缩后的 messages + 重置 token 计数
    # 下一次 LLM 调用会通过 token_tracking_middleware 获取新的 usage_metadata
    logger.debug("[ContextCompression] Reset token counters after compression")

    return {
        "messages": compressed_messages,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
    }


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 中间件
    "context_compression_middleware",
    # Token 统计函数（用于测试）
    "estimate_tokens",
    "estimate_message_tokens",
    "estimate_messages_tokens",
    "get_total_tokens_from_state",
    "estimate_next_turn_tokens",
    # 其他工具函数（用于测试）
    "get_model_context_window",
    "get_current_model_name",
    "build_state_summary",
    "compress_messages",
]
