# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/memory/manager.py
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
MemoryManager - Agent 记忆管理器

管理 Agent 的短期和长期记忆:
- 短期记忆 (Checkpointer): 会话级别的对话历史，使用 thread_id 隔离
- 长期记忆 (Store): 跨会话的持久化数据，使用 namespace + key 组织

支持的存储后端 (通过 MEMORY_BACKEND 配置):
- memory: 内存存储 (开发环境)
- mysql: MySQL 存储 (生产环境)
- postgres: PostgreSQL 存储 (兼容旧配置)
"""

from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from config import settings
from utils.logger import logger


class MemoryManager:
    """
    记忆管理器 - 管理 Agent 的短期和长期记忆 (异步版本)

    基于 langchain-use-skill 最佳实践:
    - Checkpointer: 短期记忆 (会话历史)
    - Store: 长期记忆 (跨会话持久化)

    支持的存储后端:
    - memory: 内存存储 (开发环境，重启后丢失)
    - mysql: MySQL 存储 (生产环境，使用 aiomysql)
    - postgres: PostgreSQL 存储 (兼容旧配置)

    生命周期:
    - 在 FastAPI 启动时调用 await initialize()
    - 在 FastAPI 关闭时调用 await cleanup()
    """

    def __init__(self):
        self._checkpointer: Optional[BaseCheckpointSaver] = None
        self._store: Optional[BaseStore] = None
        self._postgres_conn = None  # PostgreSQL 连接上下文
        self._mysql_checkpointer = None  # MySQL Checkpointer
        self._mysql_store = None  # MySQL Store
        self._shared_engine = None  # 共享的 AsyncEngine
        self._initialized = False

    @property
    def checkpointer(self) -> BaseCheckpointSaver:
        """获取短期记忆 (Checkpointer)"""
        if not self._initialized:
            # 同步回退: 使用内存存储
            logger.warning("MemoryManager not initialized, using MemorySaver fallback")
            return MemorySaver()
        return self._checkpointer

    @property
    def store(self) -> BaseStore:
        """获取长期记忆 (Store)"""
        if not self._initialized:
            # 同步回退: 使用内存存储
            logger.warning("MemoryManager not initialized, using InMemoryStore fallback")
            return InMemoryStore()
        return self._store

    async def initialize(self) -> None:
        """
        初始化记忆存储 (异步)

        必须在 FastAPI lifespan 中使用 await 调用。

        根据 MEMORY_BACKEND 配置选择:
        - mysql: MySQL 存储
        - postgres: PostgreSQL 存储
        - memory: 内存存储 (默认)
        """
        if self._initialized:
            return

        backend = getattr(settings, "MEMORY_BACKEND", "memory")

        if backend == "mysql":
            await self._init_mysql_async()
        elif backend == "postgres":
            await self._init_postgres_async()
        else:
            self._init_memory()

        self._initialized = True

    def _init_memory(self) -> None:
        """初始化内存存储"""
        logger.info("Using MemorySaver for short-term memory")
        self._checkpointer = MemorySaver()

        logger.info("Using InMemoryStore for long-term memory")
        self._store = InMemoryStore()

    async def _init_mysql_async(self) -> None:
        """初始化 MySQL 存储 (异步)"""
        try:
            from db.base import (
                get_shared_async_engine,
                ensure_tables_exist,
                verify_engine_connection,
                ensure_database_exists,
            )
            from db.mysql_checkpointer import MySQLCheckpointSaver
            from db.mysql_store import MySQLStore

            logger.info("Initializing MySQL memory backend...")

            # 确保数据库存在（如果不存在则自动创建）
            await ensure_database_exists()

            # 获取共享 Engine (单例)
            self._shared_engine = get_shared_async_engine()

            # 验证数据库连接
            await verify_engine_connection(self._shared_engine)

            # 自动创建表结构（如果不存在）
            created = await ensure_tables_exist(self._shared_engine)
            if created:
                logger.info("Agent memory tables auto-created on first startup")

            # 初始化短期记忆 (使用共享 Engine)
            self._mysql_checkpointer = MySQLCheckpointSaver.from_engine(self._shared_engine)
            self._checkpointer = self._mysql_checkpointer
            await self._mysql_checkpointer.setup()
            logger.info("MySQLCheckpointSaver initialized successfully")

            # 初始化长期记忆 (使用共享 Engine)
            self._mysql_store = MySQLStore.from_engine(self._shared_engine)
            self._store = self._mysql_store
            await self._mysql_store.setup()
            logger.info("MySQLStore initialized successfully")

        except ImportError as e:
            logger.warning(f"MySQL dependencies not installed: {e}")
            logger.warning("Falling back to memory storage")
            self._init_memory()

        except Exception as e:
            logger.error(f"Failed to initialize MySQL backend: {e}")
            logger.warning("Falling back to memory storage")
            self._init_memory()

    async def _init_postgres_async(self) -> None:
        """初始化 PostgreSQL 存储 (异步，兼容旧配置)"""
        postgres_uri = getattr(settings, "POSTGRES_URI", None)

        if not postgres_uri:
            logger.warning("POSTGRES_URI not set, falling back to memory storage")
            self._init_memory()
            return

        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            logger.info("Initializing PostgresSaver for short-term memory...")

            self._postgres_conn = PostgresSaver.from_conn_string(postgres_uri)
            self._checkpointer = self._postgres_conn.__enter__()
            self._checkpointer.setup()

            logger.info("PostgresSaver initialized successfully")

            # 长期记忆仍使用内存存储 (PostgresStore 需要额外配置)
            self._store = InMemoryStore()
            logger.info("Using InMemoryStore for long-term memory")

        except ImportError:
            logger.warning(
                "langgraph-checkpoint-postgres not installed, "
                "falling back to MemorySaver. "
                "Install with: uv add langgraph-checkpoint-postgres"
            )
            self._init_memory()

        except Exception as e:
            logger.error(f"Failed to initialize PostgresSaver: {e}")
            logger.warning("Falling back to memory storage")
            self._init_memory()

    async def cleanup(self) -> None:
        """
        清理记忆存储资源 (异步)

        在 FastAPI 关闭时调用，正确关闭数据库连接。
        """
        # 清理 PostgreSQL 连接
        if self._postgres_conn is not None:
            try:
                self._postgres_conn.__exit__(None, None, None)
                logger.info("PostgresSaver connection closed")
            except Exception as e:
                logger.error(f"Error closing PostgresSaver: {e}")
            finally:
                self._postgres_conn = None

        # 清理 MySQL 连接
        if self._mysql_checkpointer is not None:
            try:
                await self._mysql_checkpointer.close()
                logger.info("MySQLCheckpointSaver connection closed")
            except Exception as e:
                logger.error(f"Error closing MySQLCheckpointSaver: {e}")
            finally:
                self._mysql_checkpointer = None

        if self._mysql_store is not None:
            try:
                await self._mysql_store.close()
                logger.info("MySQLStore connection closed")
            except Exception as e:
                logger.error(f"Error closing MySQLStore: {e}")
            finally:
                self._mysql_store = None

        # 清理共享 Engine (由 db.base.close_async_engine() 统一管理)
        if self._shared_engine is not None:
            try:
                from db.base import close_async_engine
                await close_async_engine()
                logger.info("Shared async engine closed")
            except Exception as e:
                logger.error(f"Error closing shared engine: {e}")
            finally:
                self._shared_engine = None

        self._checkpointer = None
        self._store = None
        self._initialized = False


# 全局记忆管理器实例
memory_manager = MemoryManager()


def get_checkpointer() -> BaseCheckpointSaver:
    """获取短期记忆 (Checkpointer) - 会话历史"""
    return memory_manager.checkpointer


def get_store() -> BaseStore:
    """获取长期记忆 (Store) - 跨会话持久化"""
    return memory_manager.store
