# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/db/mysql_checkpointer.py
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
MySQL Checkpoint Saver - LangGraph 短期记忆持久化

实现 BaseCheckpointSaver 接口，将 Agent 状态检查点存储到 MySQL。
使用 aiomysql 异步驱动。
"""

from typing import Any, AsyncIterator, Iterator, Optional, Sequence

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from db.utils import run_sync
from utils.logger import logger


class MySQLCheckpointSaver(BaseCheckpointSaver):
    """
    MySQL-based checkpoint saver for LangGraph.

    Stores checkpoint state in MySQL database for persistence across
    application restarts. Uses async operations with aiomysql.

    Usage:
        # From connection string
        saver = MySQLCheckpointSaver.from_conn_string(
            "mysql+aiomysql://user:pass@host:3306/db"
        )

        # From existing engine
        saver = MySQLCheckpointSaver(engine=existing_engine)
    """

    serde = JsonPlusSerializer()

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        serde: Optional[Any] = None,
    ):
        super().__init__(serde=serde)
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
    ) -> "MySQLCheckpointSaver":
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
    def from_engine(cls, engine: AsyncEngine) -> "MySQLCheckpointSaver":
        """
        从现有 Engine 创建 (共享 Engine，推荐)

        Args:
            engine: 共享的 AsyncEngine 实例 (如 db.base.get_shared_async_engine())

        Returns:
            MySQLCheckpointSaver 实例
        """
        instance = cls(engine=engine)
        instance._owns_engine = False  # 不拥有 engine 所有权
        return instance

    async def _get_session(self) -> AsyncSession:
        """Get a new async session."""
        return self.async_session_factory()

    # =========================================================================
    # Async Methods (Primary Implementation)
    # =========================================================================

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Fetch checkpoint tuple by config (async)."""
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable.get("checkpoint_id")

        if not thread_id:
            return None

        async with self.async_session_factory() as session:
            if checkpoint_id:
                # 获取特定检查点
                query = text("""
                    SELECT checkpoint_id, parent_checkpoint_id, checkpoint, metadata
                    FROM agent_checkpoints
                    WHERE thread_id = :thread_id
                      AND checkpoint_ns = :checkpoint_ns
                      AND checkpoint_id = :checkpoint_id
                """)
                result = await session.execute(query, {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                })
                row = result.fetchone()
            else:
                # 获取最新检查点
                query = text("""
                    SELECT checkpoint_id, parent_checkpoint_id, checkpoint, metadata
                    FROM agent_checkpoints
                    WHERE thread_id = :thread_id
                      AND checkpoint_ns = :checkpoint_ns
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = await session.execute(query, {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                })
                row = result.fetchone()

            if not row:
                return None

            checkpoint_id = row[0]
            parent_checkpoint_id = row[1]
            checkpoint_data = row[2]
            metadata_data = row[3]

            # 获取 pending writes
            writes_query = text("""
                SELECT task_id, channel, `type`, `blob`
                FROM agent_checkpoint_writes
                WHERE thread_id = :thread_id
                  AND checkpoint_ns = :checkpoint_ns
                  AND checkpoint_id = :checkpoint_id
                ORDER BY task_id, idx
            """)
            writes_result = await session.execute(writes_query, {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            })
            writes_rows = writes_result.fetchall()

            pending_writes = []
            for w in writes_rows:
                task_id, channel, type_, blob = w
                if type_ and blob:
                    value = self.serde.loads_typed((type_, blob))
                    pending_writes.append((task_id, channel, value))

            # 反序列化 checkpoint 和 metadata (使用 loads_typed，类型固定为 msgpack)
            checkpoint = self.serde.loads_typed(("msgpack", checkpoint_data)) if checkpoint_data else {}
            metadata = self.serde.loads_typed(("msgpack", metadata_data)) if metadata_data else {}

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": checkpoint_id,
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                } if parent_checkpoint_id else None,
                pending_writes=pending_writes,
            )

    async def alist(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """List checkpoints matching criteria (async)."""
        configurable = (config or {}).get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_ns = configurable.get("checkpoint_ns", "")

        if not thread_id:
            return

        # 构建查询条件
        conditions = ["thread_id = :thread_id", "checkpoint_ns = :checkpoint_ns"]
        params = {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns}

        if before:
            before_id = before.get("configurable", {}).get("checkpoint_id")
            if before_id:
                conditions.append("""
                    created_at < (
                        SELECT created_at FROM agent_checkpoints
                        WHERE thread_id = :thread_id
                          AND checkpoint_ns = :checkpoint_ns
                          AND checkpoint_id = :before_id
                    )
                """)
                params["before_id"] = before_id

        where_clause = " AND ".join(conditions)
        limit_clause = f"LIMIT {limit}" if limit else ""

        query = text(f"""
            SELECT checkpoint_id, parent_checkpoint_id, checkpoint, metadata
            FROM agent_checkpoints
            WHERE {where_clause}
            ORDER BY created_at DESC
            {limit_clause}
        """)

        async with self.async_session_factory() as session:
            result = await session.execute(query, params)
            rows = result.fetchall()

            for row in rows:
                checkpoint_id = row[0]
                parent_checkpoint_id = row[1]
                checkpoint_data = row[2]
                metadata_data = row[3]

                checkpoint = self.serde.loads_typed(("msgpack", checkpoint_data)) if checkpoint_data else {}
                metadata = self.serde.loads_typed(("msgpack", metadata_data)) if metadata_data else {}

                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": checkpoint_id,
                        }
                    },
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": parent_checkpoint_id,
                        }
                    } if parent_checkpoint_id else None,
                )

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Store a checkpoint (async)."""
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = checkpoint.get("id") or get_checkpoint_id(checkpoint)
        parent_id = configurable.get("checkpoint_id")

        if not thread_id:
            raise ValueError("thread_id is required in config")

        async with self.async_session_factory() as session:
            # 序列化数据 (使用 dumps_typed，只取 blob 部分，类型固定为 msgpack)
            _, checkpoint_blob = self.serde.dumps_typed(checkpoint)
            _, metadata_blob = self.serde.dumps_typed(metadata)

            query = text("""
                INSERT INTO agent_checkpoints
                    (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id,
                     checkpoint, metadata)
                VALUES
                    (:thread_id, :checkpoint_ns, :checkpoint_id, :parent_id,
                     :checkpoint, :metadata)
                ON DUPLICATE KEY UPDATE
                    checkpoint = VALUES(checkpoint),
                    metadata = VALUES(metadata)
            """)
            await session.execute(query, {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
                "parent_id": parent_id,
                "checkpoint": checkpoint_blob,
                "metadata": metadata_blob,
            })
            await session.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Store intermediate writes (async)."""
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable.get("checkpoint_id")

        if not thread_id or not checkpoint_id:
            return

        async with self.async_session_factory() as session:
            for idx, (channel, value) in enumerate(writes):
                type_, blob = self.serde.dumps_typed(value)

                query = text("""
                    INSERT INTO agent_checkpoint_writes
                        (thread_id, checkpoint_ns, checkpoint_id, task_id,
                         task_path, idx, channel, `type`, `blob`)
                    VALUES
                        (:thread_id, :checkpoint_ns, :checkpoint_id, :task_id,
                         :task_path, :idx, :channel, :type, :blob)
                    ON DUPLICATE KEY UPDATE
                        `type` = VALUES(`type`),
                        `blob` = VALUES(`blob`)
                """)
                await session.execute(query, {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                    "task_id": task_id,
                    "task_path": task_path,
                    "idx": idx,
                    "channel": channel,
                    "type": type_,
                    "blob": blob,
                })
            await session.commit()

    async def adelete_thread(self, thread_id: str) -> None:
        """Delete all checkpoints for a thread (async)."""
        async with self.async_session_factory() as session:
            # 删除 writes (外键约束会自动级联删除，但显式删除更安全)
            await session.execute(
                text("DELETE FROM agent_checkpoint_writes WHERE thread_id = :tid"),
                {"tid": thread_id}
            )
            # 删除 checkpoints
            await session.execute(
                text("DELETE FROM agent_checkpoints WHERE thread_id = :tid"),
                {"tid": thread_id}
            )
            await session.commit()
            logger.info(f"Deleted all checkpoints for thread: {thread_id}")

    # =========================================================================
    # Sync Methods (Wrapper around async)
    # =========================================================================

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Fetch checkpoint tuple by config (sync wrapper)."""
        return run_sync(self.aget_tuple(config))

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints matching criteria (sync wrapper)."""
        async def _collect():
            results = []
            async for item in self.alist(config, filter=filter, before=before, limit=limit):
                results.append(item)
            return results

        return iter(run_sync(_collect()))

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Store a checkpoint (sync wrapper)."""
        return run_sync(self.aput(config, checkpoint, metadata, new_versions))

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Store intermediate writes (sync wrapper)."""
        run_sync(self.aput_writes(config, writes, task_id, task_path))

    def delete_thread(self, thread_id: str) -> None:
        """Delete all checkpoints for a thread (sync wrapper)."""
        run_sync(self.adelete_thread(thread_id))

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def setup(self) -> None:
        """
        Verify database connection and tables exist.

        Note: Prefer using DDL scripts to create tables.
        """
        async with self.async_session_factory() as session:
            try:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("MySQL checkpoint saver connected successfully")
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
            logger.info("MySQL checkpoint saver engine disposed")
        else:
            logger.debug("MySQL checkpoint saver using shared engine, skipping dispose")
