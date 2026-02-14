# -*- coding: utf-8 -*-
#!/usr/bin/env python
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/test_mysql_memory.py
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
测试 MySQL 记忆后端

运行方式:
1. 先创建数据库和表:
   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS remix_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   mysql -u root -p remix_agent < schema/agent_memory_ddl.sql

2. 配置环境变量 (.env):
   MEMORY_BACKEND=mysql
   AGENT_DB_HOST=localhost
   AGENT_DB_PORT=3306
   AGENT_DB_USER=root
   AGENT_DB_PASSWORD=your_password
   AGENT_DB_NAME=remix_agent

3. 运行测试:
   uv run python scripts/test_mysql_memory.py
"""

import asyncio
import os
import sys

# 添加 backend 目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_mysql_checkpointer():
    """测试 MySQLCheckpointSaver"""
    print("\n" + "=" * 60)
    print("Testing MySQLCheckpointSaver")
    print("=" * 60)

    from db.base import get_mysql_connection_string
    from db.mysql_checkpointer import MySQLCheckpointSaver

    conn_string = get_mysql_connection_string()
    print(f"Connection string: {conn_string.split('@')[1]}")

    saver = MySQLCheckpointSaver.from_conn_string(conn_string)

    # 测试连接
    await saver.setup()
    print("Connection successful!")

    # 测试存储
    config = {"configurable": {"thread_id": "test-thread-001"}}
    checkpoint = {
        "id": "cp-001",
        "v": 1,
        "channel_values": {"messages": []},
    }
    metadata = {"source": "test"}

    result_config = await saver.aput(config, checkpoint, metadata, {})
    print(f"Stored checkpoint: {result_config}")

    # 测试获取
    retrieved = await saver.aget_tuple(result_config)
    print(f"Retrieved checkpoint ID: {retrieved.checkpoint.get('id')}")

    # 测试删除
    await saver.adelete_thread("test-thread-001")
    print("Deleted test thread")

    await saver.close()
    print("MySQLCheckpointSaver test passed!")


async def test_mysql_store():
    """测试 MySQLStore"""
    print("\n" + "=" * 60)
    print("Testing MySQLStore")
    print("=" * 60)

    from db.base import get_mysql_connection_string
    from db.mysql_store import MySQLStore

    conn_string = get_mysql_connection_string()
    store = MySQLStore.from_conn_string(conn_string)

    # 测试连接
    await store.setup()
    print("Connection successful!")

    # 测试存储
    namespace = ("user", "test-user-001")
    key = "preferences"
    value = {"theme": "dark", "language": "zh"}

    await store.aput(namespace, key, value)
    print(f"Stored: {namespace} / {key}")

    # 测试获取
    item = await store.aget(namespace, key)
    print(f"Retrieved: {item.value if item else None}")

    # 测试搜索
    results = await store.asearch(("user",))
    print(f"Search results: {len(results)} items")

    # 测试删除
    await store.adelete(namespace, key)
    print("Deleted test item")

    await store.close()
    print("MySQLStore test passed!")


def test_session_manager():
    """测试 SessionManager"""
    print("\n" + "=" * 60)
    print("Testing MySQLSessionManager")
    print("=" * 60)

    from agent.memory import MySQLSessionManager
    from db.base import get_mysql_connection_string

    conn_string = get_mysql_connection_string()
    mgr = MySQLSessionManager.from_conn_string(conn_string)

    # 测试创建会话
    session = mgr.create_session(
        session_id="test-session-001",
        first_message="Hello, this is a test message!"
    )
    print(f"Created session: {session.session_id}, title: {session.title}")

    # 测试添加消息
    msg = mgr.add_message("test-session-001", "user", "Test user message")
    print(f"Added message: {msg.message_id}")

    msg = mgr.add_message("test-session-001", "assistant", "Test assistant response")
    print(f"Added message: {msg.message_id}")

    # 测试获取消息
    messages = mgr.list_messages("test-session-001")
    print(f"Messages count: {len(messages)}")

    # 测试列出会话
    sessions = mgr.list_sessions()
    print(f"Sessions count: {len(sessions)}")

    # 测试删除会话
    deleted = mgr.delete_session("test-session-001")
    print(f"Deleted session: {deleted}")

    print("MySQLSessionManager test passed!")


def test_memory_manager():
    """测试 MemoryManager (MySQL 后端)"""
    print("\n" + "=" * 60)
    print("Testing MemoryManager with MySQL backend")
    print("=" * 60)

    from config import settings
    from agent.memory.manager import MemoryManager

    # 检查配置
    print(f"MEMORY_BACKEND: {settings.MEMORY_BACKEND}")

    if settings.MEMORY_BACKEND != "mysql":
        print("Skipping: MEMORY_BACKEND is not 'mysql'")
        print("Set MEMORY_BACKEND=mysql in .env to test MySQL backend")
        return

    mgr = MemoryManager()
    mgr.initialize()

    print(f"Checkpointer type: {type(mgr.checkpointer).__name__}")
    print(f"Store type: {type(mgr.store).__name__}")

    mgr.cleanup()
    print("MemoryManager test passed!")


async def test_auto_create_tables():
    """测试自动创建表功能"""
    print("\n" + "=" * 60)
    print("Testing Auto Create Tables")
    print("=" * 60)

    from db.base import (
        get_async_engine,
        check_tables_exist,
        ensure_tables_exist,
    )

    engine = get_async_engine()

    # 检查表是否存在
    exists = await check_tables_exist(engine)
    print(f"Tables exist: {exists}")

    # 调用 ensure_tables_exist (如果表已存在则跳过)
    created = await ensure_tables_exist(engine)
    if created:
        print("Tables were created!")
    else:
        print("Tables already exist, skipped creation")

    # 再次检查确认表存在
    exists_after = await check_tables_exist(engine)
    print(f"Tables exist after ensure: {exists_after}")

    assert exists_after, "Tables should exist after ensure_tables_exist()"
    print("Auto create tables test passed!")


async def main():
    """运行所有测试"""
    from config import settings

    print("MySQL Memory Backend Tests")
    print(f"MEMORY_BACKEND: {settings.MEMORY_BACKEND}")
    print(f"AGENT_DB_NAME: {settings.AGENT_DB_NAME}")

    if settings.MEMORY_BACKEND != "mysql":
        print("\nWarning: MEMORY_BACKEND is not 'mysql'")
        print("Set MEMORY_BACKEND=mysql in .env to enable MySQL tests")
        print("\nRunning with current configuration anyway...")

    try:
        # 测试自动建表
        await test_auto_create_tables()

        # 测试各个组件
        await test_mysql_checkpointer()
        await test_mysql_store()
        test_session_manager()
        test_memory_manager()

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
