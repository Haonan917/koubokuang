# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/db/base.py
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
MySQL 数据库连接管理

使用 aiomysql + SQLAlchemy[asyncio] 提供异步数据库访问。
支持自动创建表结构（首次启动时）。
"""

from typing import Optional
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from config import settings
from utils.logger import logger


# 全局异步引擎实例
_async_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

# 标记表是否已初始化检查
_tables_checked: bool = False


def get_mysql_connection_string() -> str:
    """
    构建 MySQL 异步连接字符串

    使用 AGENT_DB_* 配置，如果未设置则使用默认值。

    Returns:
        MySQL 连接字符串 (aiomysql 驱动)
    """
    host = getattr(settings, "AGENT_DB_HOST", None) or "localhost"
    port = getattr(settings, "AGENT_DB_PORT", None) or 3306
    user = getattr(settings, "AGENT_DB_USER", None) or "root"
    password = getattr(settings, "AGENT_DB_PASSWORD", None) or ""
    database = getattr(settings, "AGENT_DB_NAME", None) or "remix_agent"

    # aiomysql 驱动的连接字符串格式
    conn_string = f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}"

    return conn_string


def get_async_engine(
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_recycle: int = 3600,
    echo: bool = False,
) -> AsyncEngine:
    """
    获取异步数据库引擎 (单例)

    Args:
        pool_size: 连接池大小
        max_overflow: 最大溢出连接数
        pool_recycle: 连接回收时间 (秒)
        echo: 是否打印 SQL

    Returns:
        AsyncEngine 实例
    """
    global _async_engine

    if _async_engine is None:
        conn_string = get_mysql_connection_string()
        logger.info(f"Creating async MySQL engine: {conn_string.split('@')[1]}")

        _async_engine = create_async_engine(
            conn_string,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            echo=echo,
        )

    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    获取异步会话工厂 (单例)

    Returns:
        async_sessionmaker 实例
    """
    global _async_session_factory

    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _async_session_factory


@asynccontextmanager
async def get_async_session():
    """
    获取异步数据库会话 (上下文管理器)

    Usage:
        async with get_async_session() as session:
            result = await session.execute(query)
    """
    factory = get_async_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_async_engine() -> None:
    """
    关闭异步引擎

    在应用关闭时调用。
    """
    global _async_engine, _async_session_factory, _tables_checked

    if _async_engine is not None:
        await _async_engine.dispose()
        logger.info("Async MySQL engine disposed")
        _async_engine = None
        _async_session_factory = None
        _tables_checked = False


def get_shared_async_engine() -> AsyncEngine:
    """
    获取共享的异步 Engine (别名函数)

    所有 MySQL 组件应使用此方法获取 Engine，
    而非各自创建独立的 Engine，以避免连接池资源浪费。

    Returns:
        共享的 AsyncEngine 实例
    """
    return get_async_engine()


async def verify_engine_connection(engine: AsyncEngine) -> bool:
    """
    验证 Engine 连接是否正常

    Args:
        engine: AsyncEngine 实例

    Returns:
        True 如果连接正常

    Raises:
        Exception 如果连接失败
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        logger.info("MySQL connection verified successfully")
        return True


async def ensure_database_exists() -> bool:
    """
    确保目标数据库存在，如果不存在则创建

    连接到 MySQL 服务器（不指定数据库），检查并创建目标数据库。
    使用 aiomysql 直接连接，避免 SQLAlchemy Engine 的数据库依赖。

    Returns:
        True 如果创建了新数据库，False 如果数据库已存在
    """
    import aiomysql

    host = getattr(settings, "AGENT_DB_HOST", None) or "localhost"
    port = int(getattr(settings, "AGENT_DB_PORT", None) or 3306)
    user = getattr(settings, "AGENT_DB_USER", None) or "root"
    password = getattr(settings, "AGENT_DB_PASSWORD", None) or ""
    database = getattr(settings, "AGENT_DB_NAME", None) or "remix_agent"

    # 连接到 MySQL 服务器（不指定数据库）
    conn = await aiomysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
    )

    try:
        async with conn.cursor() as cursor:
            # 检查数据库是否存在
            await cursor.execute(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s",
                (database,)
            )
            exists = await cursor.fetchone()

            if not exists:
                # 创建数据库
                await cursor.execute(
                    f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                logger.info(f"Database '{database}' created successfully")
                return True
            else:
                logger.debug(f"Database '{database}' already exists")
                return False
    finally:
        conn.close()


# =============================================================================
# 自动创建表结构
# =============================================================================

# DDL 语句 - Agent 记忆存储所需的表
_AGENT_TABLES_DDL = """
-- Agent 检查点表 (短期记忆)
CREATE TABLE IF NOT EXISTS agent_checkpoints (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    thread_id VARCHAR(255) NOT NULL COMMENT '会话线程 ID',
    checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '' COMMENT '检查点命名空间',
    checkpoint_id VARCHAR(255) NOT NULL COMMENT '检查点 ID (UUID)',
    parent_checkpoint_id VARCHAR(255) DEFAULT NULL COMMENT '父检查点 ID',
    checkpoint LONGBLOB NOT NULL COMMENT '序列化的检查点数据',
    metadata LONGBLOB COMMENT '检查点元数据',
    channel_versions JSON COMMENT '通道版本信息',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uk_checkpoint (thread_id(64), checkpoint_ns(64), checkpoint_id(64)),
    INDEX idx_thread_ns (thread_id(64), checkpoint_ns(64)),
    INDEX idx_parent (parent_checkpoint_id),
    INDEX idx_created (created_at),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 检查点存储';

-- Agent 检查点中间写入表
CREATE TABLE IF NOT EXISTS agent_checkpoint_writes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL COMMENT '会话线程 ID',
    checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '' COMMENT '检查点命名空间',
    checkpoint_id VARCHAR(255) NOT NULL COMMENT '关联的检查点 ID',
    task_id VARCHAR(255) NOT NULL COMMENT '任务 ID',
    task_path VARCHAR(255) NOT NULL DEFAULT '' COMMENT '任务路径',
    idx INT NOT NULL COMMENT '写入序号',
    channel VARCHAR(255) NOT NULL COMMENT '通道名称',
    `type` VARCHAR(255) DEFAULT NULL COMMENT '写入类型',
    `blob` LONGBLOB COMMENT '序列化的写入数据',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uk_write (thread_id(64), checkpoint_ns(64), checkpoint_id(64), task_id(64), idx),
    INDEX idx_checkpoint (thread_id(64), checkpoint_ns(64), checkpoint_id(64))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 检查点中间写入';

-- Agent 长期记忆存储表 (Store)
CREATE TABLE IF NOT EXISTS agent_store (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    namespace VARCHAR(1024) NOT NULL COMMENT '命名空间 (JSON 数组序列化)',
    `key` VARCHAR(255) NOT NULL COMMENT '存储键',
    value LONGBLOB NOT NULL COMMENT '存储值 (JSON)',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uk_ns_key (namespace(191), `key`),
    INDEX idx_updated (updated_at),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 长期记忆存储';

-- 会话元数据表
CREATE TABLE IF NOT EXISTS agent_sessions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE COMMENT '会话 ID (UUID)',
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    title VARCHAR(255) NOT NULL DEFAULT '新对话' COMMENT '会话标题',
    first_message TEXT COMMENT '首条消息内容',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_updated (updated_at DESC),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Agent 会话元数据';

-- 会话消息表
CREATE TABLE IF NOT EXISTS agent_session_messages (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(255) NOT NULL UNIQUE COMMENT '消息 ID (UUID)',
    session_id VARCHAR(255) NOT NULL COMMENT '关联会话 ID',
    role VARCHAR(50) NOT NULL COMMENT '角色: user/assistant/system',
    content LONGTEXT NOT NULL COMMENT '消息内容',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_session (session_id),
    INDEX idx_session_time (session_id, created_at),
    FOREIGN KEY (session_id) REFERENCES agent_sessions(session_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Agent 会话消息历史';
"""


async def check_tables_exist(engine: AsyncEngine) -> bool:
    """
    检查 Agent 记忆存储表是否存在

    通过检查 agent_checkpoints 表来判断是否已初始化。

    Args:
        engine: 异步数据库引擎

    Returns:
        True 如果表存在，False 如果不存在
    """
    async with engine.connect() as conn:
        try:
            # 检查 agent_checkpoints 表是否存在
            result = await conn.execute(text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'agent_checkpoints' "
                "LIMIT 1"
            ))
            row = result.fetchone()
            return row is not None
        except Exception as e:
            logger.warning(f"Failed to check table existence: {e}")
            return False


async def create_tables(engine: AsyncEngine) -> None:
    """
    创建 Agent 记忆存储所需的表

    Args:
        engine: 异步数据库引擎
    """
    async with engine.begin() as conn:
        # 先移除所有 SQL 注释行
        lines = _AGENT_TABLES_DDL.split('\n')
        clean_lines = [line for line in lines if not line.strip().startswith('--')]
        clean_ddl = '\n'.join(clean_lines)

        # 按分号分割为单独的语句
        statements = [s.strip() for s in clean_ddl.split(';') if s.strip()]
        for stmt in statements:
            await conn.execute(text(stmt))
        logger.info("Agent memory tables created successfully")


async def ensure_tables_exist(engine: AsyncEngine) -> bool:
    """
    确保 Agent 记忆存储所需的表存在

    如果表不存在则创建，如果已存在则跳过。
    这是一次性操作，只在首次启动时执行。

    Args:
        engine: 异步数据库引擎

    Returns:
        True 如果创建了新表，False 如果表已存在
    """
    global _tables_checked

    # 如果已经检查过，直接返回
    if _tables_checked:
        return False

    _tables_checked = True

    # 检查表是否存在
    tables_exist = await check_tables_exist(engine)

    if tables_exist:
        logger.info("Agent memory tables already exist, skipping creation")
        return False

    # 创建表
    logger.info("Agent memory tables not found, creating...")
    await create_tables(engine)
    return True


async def ensure_database_initialized() -> bool:
    """
    确保数据库已初始化（便捷函数）

    获取全局引擎并检查/创建表。

    Returns:
        True 如果创建了新表，False 如果表已存在
    """
    engine = get_async_engine()
    return await ensure_tables_exist(engine)
