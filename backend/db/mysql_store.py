# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/db/mysql_store.py
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
MySQL Store - LangGraph 长期记忆持久化

实现 BaseStore 接口，提供基于 MySQL 的键值存储。
支持命名空间、批量操作。
"""

import json
from typing import Any, Iterable, Optional

from langgraph.store.base import (
    BaseStore,
    GetOp,
    Item,
    ListNamespacesOp,
    Op,
    PutOp,
    Result,
    SearchOp,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from db.utils import run_sync
from utils.logger import logger


class MySQLStore(BaseStore):
    """
    MySQL-based key-value store for LangGraph long-term memory.

    Features:
    - Hierarchical namespaces
    - Batch operations
    - Async operations with aiomysql

    Usage:
        store = MySQLStore.from_conn_string(
            "mysql+aiomysql://user:pass@host:3306/db"
        )

        # Store data
        store.put(("user", "123"), "preferences", {"theme": "dark"})

        # Retrieve data
        item = store.get(("user", "123"), "preferences")
    """

    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self._owns_engine = False  # 是否拥有 engine 所有权

    @classmethod
    def from_conn_string(
        cls,
        conn_string: str,
        *,
        pool_size: int = 5,
        pool_recycle: int = 3600,
    ) -> "MySQLStore":
        """
        从连接字符串创建 (创建独立 Engine)

        注意: 生产环境推荐使用 from_engine() 共享 Engine 以节省资源。
        """
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            conn_string,
            pool_pre_ping=True,
            pool_size=pool_size,
            pool_recycle=pool_recycle,
        )
        instance = cls(engine=engine)
        instance._owns_engine = True  # 标记拥有 engine 所有权
        return instance

    @classmethod
    def from_engine(cls, engine: AsyncEngine) -> "MySQLStore":
        """
        从现有 Engine 创建 (共享 Engine，推荐)

        Args:
            engine: 共享的 AsyncEngine 实例 (如 db.base.get_shared_async_engine())

        Returns:
            MySQLStore 实例
        """
        instance = cls(engine=engine)
        instance._owns_engine = False  # 不拥有 engine 所有权
        return instance

    def _serialize_namespace(self, namespace: tuple[str, ...]) -> str:
        """Serialize namespace tuple to JSON string."""
        return json.dumps(list(namespace))

    def _deserialize_namespace(self, ns_str: str) -> tuple[str, ...]:
        """Deserialize namespace from JSON string."""
        return tuple(json.loads(ns_str))

    # =========================================================================
    # Async Batch Operations (Primary Implementation)
    # =========================================================================

    async def abatch(self, ops: Iterable[Op]) -> list[Result]:
        """Execute batch operations asynchronously."""
        results = []
        ops_list = list(ops)

        async with self.async_session_factory() as session:
            try:
                for op in ops_list:
                    if isinstance(op, GetOp):
                        result = await self._handle_get(session, op)
                    elif isinstance(op, PutOp):
                        result = await self._handle_put(session, op)
                    elif isinstance(op, SearchOp):
                        result = await self._handle_search(session, op)
                    elif isinstance(op, ListNamespacesOp):
                        result = await self._handle_list_namespaces(session, op)
                    else:
                        result = None
                    results.append(result)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in batch operation: {e}")
                raise

        return results

    async def _handle_get(self, session: AsyncSession, op: GetOp) -> Optional[Item]:
        """Handle GetOp."""
        namespace_str = self._serialize_namespace(op.namespace)

        query = text("""
            SELECT `key`, value, created_at, updated_at
            FROM agent_store
            WHERE namespace = :namespace AND `key` = :key
        """)
        result = await session.execute(query, {
            "namespace": namespace_str,
            "key": op.key,
        })
        row = result.fetchone()

        if not row:
            return None

        return Item(
            namespace=op.namespace,
            key=row[0],
            value=json.loads(row[1]),
            created_at=row[2],
            updated_at=row[3],
        )

    async def _handle_put(self, session: AsyncSession, op: PutOp) -> None:
        """Handle PutOp."""
        namespace_str = self._serialize_namespace(op.namespace)

        if op.value is None:
            # Delete operation
            query = text("""
                DELETE FROM agent_store
                WHERE namespace = :namespace AND `key` = :key
            """)
            await session.execute(query, {
                "namespace": namespace_str,
                "key": op.key,
            })
        else:
            # Upsert operation
            query = text("""
                INSERT INTO agent_store (namespace, `key`, value)
                VALUES (:namespace, :key, :value)
                ON DUPLICATE KEY UPDATE
                    value = VALUES(value),
                    updated_at = CURRENT_TIMESTAMP(6)
            """)
            await session.execute(query, {
                "namespace": namespace_str,
                "key": op.key,
                "value": json.dumps(op.value),
            })
        return None

    async def _handle_search(self, session: AsyncSession, op: SearchOp) -> list[Item]:
        """Handle SearchOp."""
        prefix_str = self._serialize_namespace(op.namespace_prefix)
        # 使用 JSON 前缀匹配 (移除末尾的 ] 并添加 %)
        # 例如: ["user", "123"] -> ["user", "123%
        prefix_pattern = prefix_str.rstrip(']') + '%'

        query = text("""
            SELECT namespace, `key`, value, created_at, updated_at
            FROM agent_store
            WHERE namespace LIKE :prefix
            ORDER BY updated_at DESC
            LIMIT :limit OFFSET :offset
        """)
        result = await session.execute(query, {
            "prefix": prefix_pattern,
            "limit": op.limit or 100,
            "offset": op.offset or 0,
        })
        rows = result.fetchall()

        return [
            Item(
                namespace=self._deserialize_namespace(row[0]),
                key=row[1],
                value=json.loads(row[2]),
                created_at=row[3],
                updated_at=row[4],
            )
            for row in rows
        ]

    async def _handle_list_namespaces(
        self, session: AsyncSession, op: ListNamespacesOp
    ) -> list[tuple[str, ...]]:
        """Handle ListNamespacesOp."""
        # 构建查询条件
        conditions = []
        params = {
            "limit": op.limit or 100,
            "offset": op.offset or 0,
        }

        if op.match_conditions:
            for cond in op.match_conditions:
                if cond.match_type == "prefix":
                    prefix = self._serialize_namespace(cond.path)
                    prefix_pattern = prefix.rstrip(']') + '%'
                    conditions.append("namespace LIKE :prefix")
                    params["prefix"] = prefix_pattern
                elif cond.match_type == "suffix":
                    # 后缀匹配较复杂，简化处理
                    pass

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = text(f"""
            SELECT DISTINCT namespace
            FROM agent_store
            WHERE {where_clause}
            LIMIT :limit OFFSET :offset
        """)
        result = await session.execute(query, params)
        rows = result.fetchall()

        namespaces = [self._deserialize_namespace(row[0]) for row in rows]

        # 应用 max_depth 过滤
        if op.max_depth is not None:
            namespaces = [ns[:op.max_depth] for ns in namespaces]
            namespaces = list(set(namespaces))  # 去重

        return namespaces

    # =========================================================================
    # Sync Batch Operations (Wrapper)
    # =========================================================================

    def batch(self, ops: Iterable[Op]) -> list[Result]:
        """Execute batch operations synchronously (wrapper)."""
        return run_sync(self.abatch(ops))

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def aget(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> Optional[Item]:
        """Get a single item (async convenience method)."""
        results = await self.abatch([GetOp(namespace=namespace, key=key)])
        return results[0]

    async def aput(
        self,
        namespace: tuple[str, ...],
        key: str,
        value: dict[str, Any],
    ) -> None:
        """Put a single item (async convenience method)."""
        await self.abatch([PutOp(namespace=namespace, key=key, value=value)])

    async def adelete(
        self,
        namespace: tuple[str, ...],
        key: str,
    ) -> None:
        """Delete a single item (async convenience method)."""
        await self.abatch([PutOp(namespace=namespace, key=key, value=None)])

    async def asearch(
        self,
        namespace_prefix: tuple[str, ...],
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Item]:
        """Search items by namespace prefix (async convenience method)."""
        results = await self.abatch([
            SearchOp(namespace_prefix=namespace_prefix, limit=limit, offset=offset)
        ])
        return results[0]

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def setup(self) -> None:
        """Verify database connection."""
        async with self.async_session_factory() as session:
            try:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("MySQL store connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to MySQL: {e}")
                raise

    async def close(self) -> None:
        """
        关闭数据库连接

        只有当实例拥有 engine 所有权时才会关闭 engine。
        共享 Engine 的情况下不会关闭，由 db.base.close_async_engine() 统一管理。
        """
        if self._owns_engine and self.engine:
            await self.engine.dispose()
            logger.info("MySQL store engine disposed")
        else:
            logger.debug("MySQL store using shared engine, skipping dispose")
