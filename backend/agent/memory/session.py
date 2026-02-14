# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/memory/session.py
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
会话元数据管理器 - 存储和管理会话列表

支持多种存储后端:
- InMemorySessionManager: 内存存储 (开发环境)
- MySQLSessionManager: MySQL 持久化存储 (生产环境)

通过 MEMORY_BACKEND 配置切换。
"""

import asyncio
import json
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class ChatMessageEntry:
    """会话消息"""
    message_id: str
    role: str
    content: str
    segments_json: Optional[List[Dict[str, Any]]] = None  # 消息 segments 元数据
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        result = {
            "id": self.message_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.created_at.isoformat(),
        }
        if self.segments_json is not None:
            result["segments_json"] = self.segments_json
        return result


@dataclass
class SessionMetadata:
    """会话元数据"""
    session_id: str
    title: str
    first_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "first_message": self.first_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@runtime_checkable
class SessionManagerProtocol(Protocol):
    """会话管理器协议"""

    def create_session(
        self, session_id: str, title: str = "新对话", first_message: str = "",
        user_id: Optional[str] = None,
    ) -> SessionMetadata: ...

    def get_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[SessionMetadata]: ...

    def update_session(
        self, session_id: str, title: Optional[str] = None, first_message: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[SessionMetadata]: ...

    def delete_session(self, session_id: str, user_id: Optional[str] = None) -> bool: ...

    def list_sessions(self, limit: int = 20, offset: int = 0, user_id: Optional[str] = None) -> List[SessionMetadata]: ...

    def count_sessions(self, user_id: Optional[str] = None) -> int: ...

    def add_message(
        self, session_id: str, role: str, content: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> ChatMessageEntry: ...

    def list_messages(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[ChatMessageEntry]: ...

    def count_messages(self, session_id: str) -> int: ...


# =============================================================================
# InMemory Implementation (Original)
# =============================================================================

class InMemorySessionManager:
    """
    内存会话管理器

    线程安全的内存存储，用于开发环境。
    重启后数据丢失。
    """

    def __init__(self):
        self._sessions: Dict[str, SessionMetadata] = {}
        self._session_owners: Dict[str, Optional[str]] = {}  # session_id -> user_id
        self._messages: Dict[str, List[ChatMessageEntry]] = {}
        self._lock = threading.Lock()

    def create_session(
        self,
        session_id: str,
        title: str = "新对话",
        first_message: str = "",
        user_id: Optional[str] = None,
    ) -> SessionMetadata:
        with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.updated_at = datetime.now()
                if first_message and not session.first_message:
                    session.first_message = first_message
                    session.title = first_message[:30] + ("..." if len(first_message) > 30 else "")
                return session
            else:
                title = first_message[:30] + ("..." if len(first_message) > 30 else "") if first_message else title
                session = SessionMetadata(
                    session_id=session_id,
                    title=title,
                    first_message=first_message,
                )
                self._sessions[session_id] = session
                self._session_owners[session_id] = user_id
                self._messages[session_id] = []
                return session

    def _check_owner(self, session_id: str, user_id: Optional[str]) -> bool:
        """检查 user_id 是否匹配会话归属"""
        owner = self._session_owners.get(session_id)
        if user_id is None:
            return owner is None
        return owner == user_id

    def get_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[SessionMetadata]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            if not self._check_owner(session_id, user_id):
                return None
            return session

    def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        first_message: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[SessionMetadata]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            if not self._check_owner(session_id, user_id):
                return None
            if title:
                session.title = title
            if first_message:
                session.first_message = first_message
            session.updated_at = datetime.now()
            return session

    def add_message(
        self, session_id: str, role: str, content: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> ChatMessageEntry:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionMetadata(session_id=session_id, title="新对话")
                self._messages[session_id] = []

            message = ChatMessageEntry(
                message_id=str(uuid.uuid4()),
                role=role,
                content=content,
                segments_json=segments,
            )
            self._messages[session_id].append(message)
            self._sessions[session_id].updated_at = datetime.now()
            return message

    def list_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[ChatMessageEntry]:
        with self._lock:
            messages = self._messages.get(session_id, [])
            sorted_messages = sorted(messages, key=lambda m: m.created_at)
            return sorted_messages[offset:offset + limit]

    def count_messages(self, session_id: str) -> int:
        with self._lock:
            return len(self._messages.get(session_id, []))

    def delete_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        with self._lock:
            if session_id in self._sessions:
                if not self._check_owner(session_id, user_id):
                    return False
                del self._sessions[session_id]
                self._session_owners.pop(session_id, None)
                self._messages.pop(session_id, None)
                return True
            return False

    def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
        user_id: Optional[str] = None,
    ) -> List[SessionMetadata]:
        with self._lock:
            filtered = [
                s for sid, s in self._sessions.items()
                if self._check_owner(sid, user_id)
            ]
            sorted_sessions = sorted(
                filtered,
                key=lambda s: s.updated_at,
                reverse=True
            )
            return sorted_sessions[offset:offset + limit]

    def count_sessions(self, user_id: Optional[str] = None) -> int:
        with self._lock:
            return sum(
                1 for sid in self._sessions
                if self._check_owner(sid, user_id)
            )

    # -------------------------------------------------------------------------
    # Async Methods (直接返回，与 MySQLSessionManager 接口兼容)
    # -------------------------------------------------------------------------

    async def acreate_session(
        self,
        session_id: str,
        title: str = "新对话",
        first_message: str = "",
        user_id: Optional[str] = None,
    ) -> SessionMetadata:
        """创建或更新会话 (async)"""
        return self.create_session(session_id, title, first_message, user_id=user_id)

    async def aget_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[SessionMetadata]:
        """获取会话 (async)"""
        return self.get_session(session_id, user_id=user_id)

    async def aupdate_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        first_message: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[SessionMetadata]:
        """更新会话 (async)"""
        return self.update_session(session_id, title, first_message, user_id=user_id)

    async def adelete_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """删除会话 (async)"""
        return self.delete_session(session_id, user_id=user_id)

    async def alist_sessions(self, limit: int = 20, offset: int = 0, user_id: Optional[str] = None) -> List[SessionMetadata]:
        """获取会话列表 (async)"""
        return self.list_sessions(limit, offset, user_id=user_id)

    async def acount_sessions(self, user_id: Optional[str] = None) -> int:
        """获取会话总数 (async)"""
        return self.count_sessions(user_id=user_id)

    async def aadd_message(
        self, session_id: str, role: str, content: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> ChatMessageEntry:
        """添加消息 (async)"""
        return self.add_message(session_id, role, content, segments)

    async def alist_messages(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[ChatMessageEntry]:
        """获取消息列表 (async)"""
        return self.list_messages(session_id, limit, offset)

    async def acount_messages(self, session_id: str) -> int:
        """获取消息数量 (async)"""
        return self.count_messages(session_id)


# =============================================================================
# MySQL Implementation
# =============================================================================

class MySQLSessionManager:
    """
    MySQL 会话管理器

    使用 aiomysql 异步驱动，支持持久化存储。
    生产环境推荐使用。

    API 使用方式:
    - 在 async 上下文中 (FastAPI 路由): 直接调用 async 方法 (如 alist_sessions)
    - 在 sync 上下文中: 调用同步方法 (如 list_sessions)
    """

    def __init__(self, engine):
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
        self.engine = engine
        self.async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @classmethod
    def from_conn_string(cls, conn_string: str) -> "MySQLSessionManager":
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(conn_string, pool_pre_ping=True)
        return cls(engine=engine)

    @classmethod
    def from_engine(cls, engine) -> "MySQLSessionManager":
        """从现有 Engine 创建 (共享 Engine，推荐)"""
        return cls(engine=engine)

    def _run_async(self, coro):
        """
        安全运行协程的同步包装

        注意: 在 FastAPI async 路由中，应直接调用 async 方法而非同步包装器。
        """
        import nest_asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 已经在异步环境中，尝试使用 nest_asyncio
            try:
                nest_asyncio.apply()
                return loop.run_until_complete(coro)
            except ValueError:
                # uvloop 不支持 nest_asyncio
                # 在这种情况下，应该直接使用 async 方法
                raise RuntimeError(
                    "Cannot run async code synchronously in uvloop. "
                    "Use async methods directly (e.g., alist_sessions instead of list_sessions)"
                )
        else:
            return asyncio.run(coro)

    # -------------------------------------------------------------------------
    # Session Operations
    # -------------------------------------------------------------------------

    def create_session(
        self,
        session_id: str,
        title: str = "新对话",
        first_message: str = "",
        user_id: Optional[str] = None,
    ) -> SessionMetadata:
        return self._run_async(self._create_session_async(session_id, title, first_message, user_id=user_id))

    async def _create_session_async(
        self,
        session_id: str,
        title: str,
        first_message: str,
        user_id: Optional[str] = None,
    ) -> SessionMetadata:
        from sqlalchemy import text

        async with self.async_session_factory() as session:
            # 检查是否存在
            check_query = text("""
                SELECT session_id, title, first_message, created_at, updated_at
                FROM agent_sessions WHERE session_id = :sid
            """)
            result = await session.execute(check_query, {"sid": session_id})
            row = result.fetchone()

            if row:
                # 更新现有会话
                # COALESCE 保留已有 user_id，仅在 NULL 时认领
                if first_message and not row[2]:
                    auto_title = first_message[:30] + ("..." if len(first_message) > 30 else "")
                    update_query = text("""
                        UPDATE agent_sessions
                        SET first_message = :fm, title = :title, updated_at = NOW(6),
                            user_id = COALESCE(user_id, :uid)
                        WHERE session_id = :sid
                    """)
                    await session.execute(update_query, {
                        "sid": session_id,
                        "fm": first_message,
                        "title": auto_title,
                        "uid": user_id,
                    })
                    await session.commit()
                    return SessionMetadata(
                        session_id=session_id,
                        title=auto_title,
                        first_message=first_message,
                        created_at=row[3],
                        updated_at=datetime.now(),
                    )
                else:
                    update_query = text("""
                        UPDATE agent_sessions SET updated_at = NOW(6),
                            user_id = COALESCE(user_id, :uid)
                        WHERE session_id = :sid
                    """)
                    await session.execute(update_query, {"sid": session_id, "uid": user_id})
                    await session.commit()
                    return SessionMetadata(
                        session_id=session_id,
                        title=row[1],
                        first_message=row[2] or "",
                        created_at=row[3],
                        updated_at=datetime.now(),
                    )
            else:
                # 创建新会话
                if first_message:
                    title = first_message[:30] + ("..." if len(first_message) > 30 else "")

                insert_query = text("""
                    INSERT INTO agent_sessions (session_id, title, first_message, user_id)
                    VALUES (:sid, :title, :fm, :uid)
                """)
                await session.execute(insert_query, {
                    "sid": session_id,
                    "title": title,
                    "fm": first_message,
                    "uid": user_id,
                })
                await session.commit()

                return SessionMetadata(
                    session_id=session_id,
                    title=title,
                    first_message=first_message,
                )

    def get_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[SessionMetadata]:
        return self._run_async(self._get_session_async(session_id, user_id=user_id))

    async def _get_session_async(self, session_id: str, user_id: Optional[str] = None) -> Optional[SessionMetadata]:
        from sqlalchemy import text

        async with self.async_session_factory() as session:
            if user_id is not None:
                query = text("""
                    SELECT session_id, title, first_message, created_at, updated_at
                    FROM agent_sessions WHERE session_id = :sid AND user_id = :uid
                """)
                result = await session.execute(query, {"sid": session_id, "uid": user_id})
            else:
                query = text("""
                    SELECT session_id, title, first_message, created_at, updated_at
                    FROM agent_sessions WHERE session_id = :sid AND user_id IS NULL
                """)
                result = await session.execute(query, {"sid": session_id})
            row = result.fetchone()

            if not row:
                return None

            return SessionMetadata(
                session_id=row[0],
                title=row[1],
                first_message=row[2] or "",
                created_at=row[3],
                updated_at=row[4],
            )

    def update_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        first_message: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[SessionMetadata]:
        return self._run_async(self._update_session_async(session_id, title, first_message, user_id=user_id))

    async def _update_session_async(
        self,
        session_id: str,
        title: Optional[str],
        first_message: Optional[str],
        user_id: Optional[str] = None,
    ) -> Optional[SessionMetadata]:
        from sqlalchemy import text

        async with self.async_session_factory() as session:
            updates = []
            params: Dict[str, Any] = {"sid": session_id}

            if title:
                updates.append("title = :title")
                params["title"] = title
            if first_message:
                updates.append("first_message = :fm")
                params["fm"] = first_message

            if not updates:
                return await self._get_session_async(session_id, user_id=user_id)

            updates.append("updated_at = NOW(6)")
            set_clause = ", ".join(updates)

            if user_id is not None:
                where = "session_id = :sid AND user_id = :uid"
                params["uid"] = user_id
            else:
                where = "session_id = :sid AND user_id IS NULL"

            query = text(f"UPDATE agent_sessions SET {set_clause} WHERE {where}")
            result = await session.execute(query, params)
            await session.commit()

            if result.rowcount == 0:
                return None

            return await self._get_session_async(session_id, user_id=user_id)

    def delete_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        return self._run_async(self._delete_session_async(session_id, user_id=user_id))

    async def _delete_session_async(self, session_id: str, user_id: Optional[str] = None) -> bool:
        from sqlalchemy import text

        async with self.async_session_factory() as session:
            if user_id is not None:
                query = text("DELETE FROM agent_sessions WHERE session_id = :sid AND user_id = :uid")
                result = await session.execute(query, {"sid": session_id, "uid": user_id})
            else:
                query = text("DELETE FROM agent_sessions WHERE session_id = :sid AND user_id IS NULL")
                result = await session.execute(query, {"sid": session_id})
            await session.commit()
            return result.rowcount > 0

    def list_sessions(self, limit: int = 20, offset: int = 0, user_id: Optional[str] = None) -> List[SessionMetadata]:
        return self._run_async(self._list_sessions_async(limit, offset, user_id=user_id))

    async def _list_sessions_async(self, limit: int, offset: int, user_id: Optional[str] = None) -> List[SessionMetadata]:
        from sqlalchemy import text

        async with self.async_session_factory() as session:
            if user_id is not None:
                query = text("""
                    SELECT session_id, title, first_message, created_at, updated_at
                    FROM agent_sessions
                    WHERE user_id = :uid
                    ORDER BY updated_at DESC
                    LIMIT :limit OFFSET :offset
                """)
                result = await session.execute(query, {"uid": user_id, "limit": limit, "offset": offset})
            else:
                query = text("""
                    SELECT session_id, title, first_message, created_at, updated_at
                    FROM agent_sessions
                    WHERE user_id IS NULL
                    ORDER BY updated_at DESC
                    LIMIT :limit OFFSET :offset
                """)
                result = await session.execute(query, {"limit": limit, "offset": offset})
            rows = result.fetchall()

            return [
                SessionMetadata(
                    session_id=row[0],
                    title=row[1],
                    first_message=row[2] or "",
                    created_at=row[3],
                    updated_at=row[4],
                )
                for row in rows
            ]

    def count_sessions(self, user_id: Optional[str] = None) -> int:
        return self._run_async(self._count_sessions_async(user_id=user_id))

    async def _count_sessions_async(self, user_id: Optional[str] = None) -> int:
        from sqlalchemy import text

        async with self.async_session_factory() as session:
            if user_id is not None:
                query = text("SELECT COUNT(*) FROM agent_sessions WHERE user_id = :uid")
                result = await session.execute(query, {"uid": user_id})
            else:
                query = text("SELECT COUNT(*) FROM agent_sessions WHERE user_id IS NULL")
                result = await session.execute(query)
            return result.scalar() or 0

    # -------------------------------------------------------------------------
    # Message Operations
    # -------------------------------------------------------------------------

    def add_message(
        self, session_id: str, role: str, content: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> ChatMessageEntry:
        return self._run_async(self._add_message_async(session_id, role, content, segments))

    async def _add_message_async(
        self, session_id: str, role: str, content: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> ChatMessageEntry:
        from sqlalchemy import text

        message_id = str(uuid.uuid4())
        segments_str = json.dumps(segments, ensure_ascii=False) if segments else None

        async with self.async_session_factory() as session:
            # 确保会话存在
            await self._create_session_async(session_id, "新对话", "")

            insert_query = text("""
                INSERT INTO agent_session_messages (message_id, session_id, role, content, segments_json)
                VALUES (:mid, :sid, :role, :content, :segments)
            """)
            await session.execute(insert_query, {
                "mid": message_id,
                "sid": session_id,
                "role": role,
                "content": content,
                "segments": segments_str,
            })

            # 更新会话 updated_at
            update_query = text("""
                UPDATE agent_sessions SET updated_at = NOW(6)
                WHERE session_id = :sid
            """)
            await session.execute(update_query, {"sid": session_id})
            await session.commit()

        return ChatMessageEntry(
            message_id=message_id,
            role=role,
            content=content,
            segments_json=segments,
        )

    def list_messages(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[ChatMessageEntry]:
        return self._run_async(self._list_messages_async(session_id, limit, offset))

    async def _list_messages_async(
        self, session_id: str, limit: int, offset: int
    ) -> List[ChatMessageEntry]:
        from sqlalchemy import text

        async with self.async_session_factory() as session:
            query = text("""
                SELECT message_id, role, content, segments_json, created_at
                FROM agent_session_messages
                WHERE session_id = :sid
                ORDER BY created_at ASC
                LIMIT :limit OFFSET :offset
            """)
            result = await session.execute(query, {
                "sid": session_id,
                "limit": limit,
                "offset": offset,
            })
            rows = result.fetchall()

            messages = []
            for row in rows:
                # 解析 segments_json
                segments_data = None
                if row[3]:
                    try:
                        segments_data = json.loads(row[3]) if isinstance(row[3], str) else row[3]
                    except (json.JSONDecodeError, TypeError):
                        pass
                messages.append(ChatMessageEntry(
                    message_id=row[0],
                    role=row[1],
                    content=row[2],
                    segments_json=segments_data,
                    created_at=row[4],
                ))
            return messages

    def count_messages(self, session_id: str) -> int:
        return self._run_async(self._count_messages_async(session_id))

    async def _count_messages_async(self, session_id: str) -> int:
        from sqlalchemy import text

        async with self.async_session_factory() as session:
            query = text("""
                SELECT COUNT(*) FROM agent_session_messages WHERE session_id = :sid
            """)
            result = await session.execute(query, {"sid": session_id})
            return result.scalar() or 0

    # -------------------------------------------------------------------------
    # Public Async Methods (推荐在 FastAPI 路由中使用)
    # -------------------------------------------------------------------------

    async def acreate_session(
        self,
        session_id: str,
        title: str = "新对话",
        first_message: str = "",
        user_id: Optional[str] = None,
    ) -> SessionMetadata:
        """创建或更新会话 (async)"""
        return await self._create_session_async(session_id, title, first_message, user_id=user_id)

    async def aget_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[SessionMetadata]:
        """获取会话 (async)"""
        return await self._get_session_async(session_id, user_id=user_id)

    async def aupdate_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        first_message: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[SessionMetadata]:
        """更新会话 (async)"""
        return await self._update_session_async(session_id, title, first_message, user_id=user_id)

    async def adelete_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """删除会话 (async)"""
        return await self._delete_session_async(session_id, user_id=user_id)

    async def alist_sessions(self, limit: int = 20, offset: int = 0, user_id: Optional[str] = None) -> List[SessionMetadata]:
        """获取会话列表 (async)"""
        return await self._list_sessions_async(limit, offset, user_id=user_id)

    async def acount_sessions(self, user_id: Optional[str] = None) -> int:
        """获取会话总数 (async)"""
        return await self._count_sessions_async(user_id=user_id)

    async def aadd_message(
        self, session_id: str, role: str, content: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> ChatMessageEntry:
        """添加消息 (async)"""
        return await self._add_message_async(session_id, role, content, segments)

    async def alist_messages(
        self, session_id: str, limit: int = 100, offset: int = 0
    ) -> List[ChatMessageEntry]:
        """获取消息列表 (async)"""
        return await self._list_messages_async(session_id, limit, offset)

    async def acount_messages(self, session_id: str) -> int:
        """获取消息数量 (async)"""
        return await self._count_messages_async(session_id)


# =============================================================================
# Factory Function
# =============================================================================

def create_session_manager() -> SessionManagerProtocol:
    """
    工厂函数 - 根据配置创建会话管理器

    根据 MEMORY_BACKEND 配置选择:
    - "mysql": MySQLSessionManager
    - 其他: InMemorySessionManager
    """
    from config import settings
    from utils.logger import logger

    backend = getattr(settings, "MEMORY_BACKEND", "memory")

    if backend == "mysql":
        from db.base import get_mysql_connection_string
        conn_string = get_mysql_connection_string()
        logger.info(f"Creating MySQLSessionManager")
        return MySQLSessionManager.from_conn_string(conn_string)
    else:
        logger.info("Creating InMemorySessionManager")
        return InMemorySessionManager()


# =============================================================================
# Global Instance (Lazy Initialization)
# =============================================================================

_session_manager: Optional[SessionManagerProtocol] = None


def get_session_manager() -> SessionManagerProtocol:
    """获取会话管理器实例 (单例)"""
    global _session_manager
    if _session_manager is None:
        _session_manager = create_session_manager()
    return _session_manager


def reset_session_manager() -> None:
    """重置会话管理器 (用于测试)"""
    global _session_manager
    _session_manager = None
