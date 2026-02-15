# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/remix_agent.py
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
RemixAgent 工厂 - 创建和配置对话式二创 Agent

基于 LangChain 1.0 create_agent() 模式创建 Agent，
配置 Tools、Memory、Context、System Prompt 等。

Memory 架构:
- 短期记忆 (Checkpointer): 会话级别的对话历史，使用 thread_id 隔离
- 长期记忆 (Store): 跨会话的持久化数据，使用 namespace + key 组织

支持的存储后端 (通过 MEMORY_BACKEND 配置):
- memory: 内存存储 (开发环境)
- mysql: MySQL 存储 (生产环境)
- postgres: PostgreSQL 存储 (兼容旧配置)
"""

from typing import Optional, Any, Dict

from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

from agent.state import RemixAgentState, RemixContext
from agent.prompts import remix_dynamic_prompt
from agent.middleware import (
    context_compression_middleware,
    token_tracking_middleware,
    multimodal_injection_middleware,
)
from agent.tools import (
    parse_link,
    fetch_content,
    process_video,
    voice_clone,
    text_to_speech,
    lipsync_generate,
)
# 从 memory 子模块导入
from agent.memory import get_checkpointer, get_store
from llm_provider import get_llm
from utils.logger import logger


__all__ = [
    # Agent 工厂
    "create_remix_agent",
    "get_session_config",
    "get_agent_state",
    "invoke_agent",
    "stream_agent",
    # 模型
    "get_model",
]


# ============================================================================
# LLM Model
# ============================================================================

def get_model(model_name: Optional[str] = None):
    """
    获取 LLM 模型实例

    使用 llm_provider.get_llm() 统一初始化模型，
    支持 thinking/reasoning 输出。

    Returns:
        ChatModel 实例
    """
    from config import settings
    return get_llm(
        temperature=0.3,
        model_name=model_name,
        enable_thinking=getattr(settings, 'ENABLE_THINKING', False),
    )


# ============================================================================
# Agent Factory
# ============================================================================

def create_remix_agent(model_name: Optional[str] = None):
    """
    创建 RemixAgent 实例

    使用 LangChain 1.0 的 create_agent() 模式。
    配置短期记忆 (checkpointer) 和长期记忆 (store)。

    Returns:
        Compiled LangGraph Agent
    """
    # 获取 LLM
    model = get_model(model_name=model_name)

    # 定义工具列表
    # 简化架构: 只保留数据获取工具
    # Agent 完成数据获取后，直接输出 Markdown 格式的分析和灵感
    tools = [
        parse_link,     # 解析链接
        fetch_content,  # 获取内容
        process_video,  # 处理视频
        voice_clone,    # 语音克隆
        text_to_speech, # 文本转语音
        lipsync_generate,  # 唇形同步
    ]

    # 获取短期记忆 (会话历史)
    checkpointer = get_checkpointer()

    # 获取长期记忆 (跨会话持久化)
    store = get_store()

    # 创建 Agent (基于 langchain-use-skill 最佳实践)
    # 使用 middleware 实现动态 System Prompt、Context 压缩、Token 追踪和多模态注入
    #
    # 中间件执行顺序:
    # 1. context_compression_middleware (@before_model): 检查 token 并压缩
    # 2. multimodal_injection_middleware (@before_model): 注入图片到消息中
    # 3. remix_dynamic_prompt (@dynamic_prompt): 动态 System Prompt
    # 4. token_tracking_middleware (@after_model): 追踪实际 token 使用量
    agent = create_agent(
        model=model,
        tools=tools,
        state_schema=RemixAgentState,
        context_schema=RemixContext,
        middleware=[
            context_compression_middleware,   # @before_model: 检查并压缩 context
            multimodal_injection_middleware,  # @before_model: 注入图片到消息中
            remix_dynamic_prompt,             # @dynamic_prompt: 动态 System Prompt
            token_tracking_middleware,        # @after_model: 追踪实际 token 使用量
        ],
        checkpointer=checkpointer,  # 短期记忆
        store=store,                 # 长期记忆
    )

    logger.info("RemixAgent created with checkpointer and store")
    return agent


# ============================================================================
# Session Configuration
# ============================================================================

def get_session_config(session_id: str) -> Dict[str, Any]:
    """
    获取会话配置

    Args:
        session_id: 会话 ID

    Returns:
        LangGraph 配置字典
    """
    from utils.llm_callbacks import get_debug_callback_handler

    return {
        "configurable": {
            "thread_id": session_id,
        },
        "callbacks": [get_debug_callback_handler()],  # 注入 LLM 调试回调
    }


# ============================================================================
# Agent Invocation
# ============================================================================

async def invoke_agent(
    agent,
    message: str,
    session_id: str,
    context: Optional[RemixContext] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    调用 Agent 处理用户消息

    Args:
        agent: Agent 实例
        message: 用户消息
        session_id: 会话 ID
        context: RemixContext 上下文
        **kwargs: 额外参数

    Returns:
        Agent 响应
    """
    config = get_session_config(session_id)

    invoke_kwargs = {
        "config": config,
        **kwargs
    }

    if context:
        invoke_kwargs["context"] = context

    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        **invoke_kwargs
    )

    return result


async def stream_agent(
    agent,
    message: str,
    session_id: str,
    context: Optional[RemixContext] = None,
    stream_mode: str = "updates",
    **kwargs
):
    """
    流式调用 Agent

    Args:
        agent: Agent 实例
        message: 用户消息
        session_id: 会话 ID
        context: RemixContext 上下文
        stream_mode: 流模式 ("updates", "custom", "messages")
        **kwargs: 额外参数

    Yields:
        流式响应块
    """
    config = get_session_config(session_id)

    stream_kwargs = {
        "config": config,
        "stream_mode": stream_mode,
        **kwargs
    }

    if context:
        stream_kwargs["context"] = context

    async for chunk in agent.astream(
        {"messages": [HumanMessage(content=message)]},
        **stream_kwargs
    ):
        yield chunk


async def get_agent_state(agent, session_id: str) -> Optional[Dict[str, Any]]:
    """
    获取 Agent 当前状态 (异步版本)

    Args:
        agent: Agent 实例
        session_id: 会话 ID

    Returns:
        当前状态，如果不存在则返回 None
    """
    config = get_session_config(session_id)

    try:
        state = await agent.aget_state(config)
        return state.values if state else None
    except Exception as e:
        logger.warning(f"Failed to get agent state: {e}")
        return None
