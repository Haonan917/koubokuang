# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/__init__.py
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
Agent 模块 - 基于 LangChain 1.0 的对话式二创 Agent

核心组件:
- RemixAgent: 主 Agent，使用 create_agent 创建
- Tools: parse_link, fetch_content, process_video
- State: RemixAgentState (会话状态)
- Context: RemixContext (运行时上下文)
- Memory: 短期记忆 (Checkpointer) + 长期记忆 (Store)

导入指南:
- Agent 相关: from agent import create_remix_agent, get_session_config, ...
- 状态相关: from agent import RemixAgentState, RemixContext
- 记忆相关: from agent.memory import memory_manager, get_store, get_session_manager
- 流式处理: from agent.stream import StreamEventProcessor
"""

from agent.remix_agent import (
    create_remix_agent,
    get_session_config,
    get_agent_state,
)
from agent.state import RemixAgentState, RemixContext
from agent.memory import memory_manager, get_store

__all__ = [
    # Agent 工厂
    "create_remix_agent",
    "get_session_config",
    "get_agent_state",
    # 状态和上下文
    "RemixAgentState",
    "RemixContext",
    # 记忆管理
    "memory_manager",
    "get_store",
]
