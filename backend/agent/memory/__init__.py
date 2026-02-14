# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/memory/__init__.py
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
Memory 子模块 - Agent 记忆管理

提供:
- 短期记忆 (Checkpointer) 和长期记忆 (Store) 的统一管理
- 会话元数据管理 (SessionManager)
"""

from agent.memory.manager import (
    MemoryManager,
    memory_manager,
    get_checkpointer,
    get_store,
)
from agent.memory.session import (
    ChatMessageEntry,
    SessionMetadata,
    SessionManagerProtocol,
    InMemorySessionManager,
    MySQLSessionManager,
    create_session_manager,
    get_session_manager,
    reset_session_manager,
)

__all__ = [
    # Agent 记忆管理
    "MemoryManager",
    "memory_manager",
    "get_checkpointer",
    "get_store",
    # 会话管理
    "ChatMessageEntry",
    "SessionMetadata",
    "SessionManagerProtocol",
    "InMemorySessionManager",
    "MySQLSessionManager",
    "create_session_manager",
    "get_session_manager",
    "reset_session_manager",
]
