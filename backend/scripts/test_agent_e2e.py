# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/test_agent_e2e.py
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
端到端测试脚本 - 测试 Agent 完整流程

使用数据库中已有的 B站视频进行测试。
"""
import asyncio
import uuid
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, '/Users/nanmi/workspace/github/MediaCrawlerPro-AIAgents/content_remix_agent/backend')

from langchain_core.messages import HumanMessage
from agent.remix_agent import create_remix_agent, get_session_config, get_agent_state
from agent.state import RemixContext
from utils.logger import logger


async def test_fetch_content():
    """测试 DownloadServer API 内容获取"""
    print("\n" + "="*60)
    print("测试 1: DownloadServer API 内容获取")
    print("="*60)

    from services.download_server_client import DownloadServerClient

    client = DownloadServerClient()
    try:
        # 测试 B站视频
        url = "https://www.bilibili.com/video/BV1WP6dBbE3h/"
        print(f"正在获取: {url}")
        result = await client.fetch_content(url)

        print(f"✅ 内容获取成功!")
        print(f"   标题: {result.title[:50]}...")
        print(f"   作者: {result.author_name}")
        print(f"   平台: {result.platform.value}")
        print(f"   视频URL: {result.video_url[:80] if result.video_url else 'N/A'}...")
        return True
    except Exception as e:
        print(f"❌ 内容获取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_basic():
    """测试 Agent 基本功能"""
    print("\n" + "="*60)
    print("测试 2: Agent 创建和调用")
    print("="*60)

    try:
        # 创建 Agent
        print("正在创建 Agent...")
        agent = create_remix_agent()
        print(f"✅ Agent 创建成功: {type(agent).__name__}")

        # 测试简单对话
        session_id = str(uuid.uuid4())
        config = get_session_config(session_id)

        print("\n正在测试简单对话...")
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content="你好，请简单介绍一下你的功能")]},
            config=config,
        )

        # 获取最后一条消息
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            content = getattr(last_message, "content", str(last_message))
            print(f"✅ Agent 响应: {content[:200]}...")
        else:
            print("❌ 没有收到响应")
            return False

        return True
    except Exception as e:
        print(f"❌ Agent 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_with_url():
    """测试 Agent 处理 URL"""
    print("\n" + "="*60)
    print("测试 3: Agent 处理 B站视频链接")
    print("="*60)

    try:
        # 创建 Agent
        agent = create_remix_agent()

        # 使用 DownloadServer 测试过的视频
        url = "https://www.bilibili.com/video/BV1WP6dBbE3h/"
        session_id = str(uuid.uuid4())

        # 创建上下文
        context = RemixContext(
            session_id=session_id,
            use_mock=False,  # 使用真实数据库
        )

        config = get_session_config(session_id)

        print(f"正在分析视频: {url}")
        print("这可能需要一些时间...")

        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=f"请分析这个视频: {url}")]},
            config=config,
            context=context,
        )

        # 获取响应
        messages = result.get("messages", [])
        if messages:
            for msg in messages[-3:]:  # 最后3条消息
                content = getattr(msg, "content", str(msg))
                if content:
                    print(f"\n📝 消息: {content[:500]}...")

        # 检查状态
        state = await get_agent_state(agent, session_id)
        if state:
            print("\n📊 Agent 状态:")
            if state.get("content_info"):
                print(f"   - 内容信息: 已获取")
            if state.get("analysis"):
                print(f"   - 分析结果: 已生成")
            if state.get("copywriting"):
                print(f"   - 文案结果: 已生成")

        return True
    except Exception as e:
        print(f"❌ Agent URL 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("="*60)
    print("Content Remix Agent 端到端测试")
    print("="*60)

    results = []

    # 测试 1: 数据库内容获取
    results.append(("数据库内容获取", await test_fetch_content()))

    # 测试 2: Agent 基本功能
    results.append(("Agent 基本功能", await test_agent_basic()))

    # 测试 3: Agent 处理 URL (可能比较耗时)
    results.append(("Agent 处理 URL", await test_agent_with_url()))

    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过!")
    else:
        print("⚠️ 部分测试失败，请检查日志")
    print("="*60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
