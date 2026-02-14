#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/test_openai_llm.py
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
OpenAI 格式 LLM API 测试脚本

测试内容：
1. 简单回复
2. 流式输出
3. 工具调用
4. 结构化输出

使用方法：
    uv run python scripts/test_openai_llm.py --test all
    uv run python scripts/test_openai_llm.py --test simple
    uv run python scripts/test_openai_llm.py --test stream
    uv run python scripts/test_openai_llm.py --test tools
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from scripts.test_tools import WeatherReport, calculate, get_weather

# 加载环境变量（override=True 确保 .env 覆盖系统环境变量）
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)


def get_llm(temperature: float = 0.1) -> ChatOpenAI:
    """创建 OpenAI 格式的 LLM 实例"""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

    if not api_key:
        print("错误: 未设置 OPENAI_API_KEY")
        sys.exit(1)

    print(f"配置信息:")
    print(f"  - Base URL: {base_url}")
    print(f"  - Model: {model_name}")
    print(f"  - API Key: {api_key[:10]}...{api_key[-4:]}")
    print()

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )


# ============================================================================
# 测试函数
# ============================================================================


async def test_simple_reply(llm: ChatOpenAI) -> bool:
    """测试简单对话"""
    print("=== 测试简单回复 ===")

    try:
        response = await llm.ainvoke([HumanMessage(content="你好，请用一句话介绍自己")])

        print(f"回复类型: {type(response).__name__}")
        print(f"回复内容: {response.content}")

        if response.content:
            print("✓ 简单回复测试通过")
            return True
        else:
            print("✗ 回复内容为空")
            return False

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_streaming(llm: ChatOpenAI) -> bool:
    """测试流式输出"""
    print("\n=== 测试流式输出 ===")

    try:
        print("[流式] ", end="", flush=True)
        chunk_count = 0
        full_content = ""

        async for chunk in llm.astream([HumanMessage(content="用三句话讲个简短的笑话")]):
            content = chunk.content
            if content:
                print(content, end="", flush=True)
                full_content += content
                chunk_count += 1

        print()
        print(f"收到 {chunk_count} 个 chunks")

        if chunk_count > 0 and full_content:
            print("✓ 流式输出测试通过")
            return True
        else:
            print("✗ 未收到流式内容")
            return False

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_tool_calling(llm: ChatOpenAI) -> bool:
    """测试工具调用"""
    print("\n=== 测试工具调用 ===")

    try:
        # 绑定工具
        llm_with_tools = llm.bind_tools([get_weather, calculate])

        # 第一轮：获取工具调用
        print("发送: 北京今天天气怎么样？")
        response = await llm_with_tools.ainvoke(
            [HumanMessage(content="北京今天天气怎么样？")]
        )

        print(f"回复类型: {type(response).__name__}")
        print(f"回复内容: {response.content}")
        print(f"工具调用: {response.tool_calls}")

        if not response.tool_calls:
            print("✗ 未产生工具调用")
            return False

        # 执行工具调用
        tool_call = response.tool_calls[0]
        print(f"\n[工具调用] {tool_call['name']}({tool_call['args']})")

        # 执行工具
        if tool_call["name"] == "get_weather":
            tool_result = get_weather.invoke(tool_call["args"])
        elif tool_call["name"] == "calculate":
            tool_result = calculate.invoke(tool_call["args"])
        else:
            tool_result = "未知工具"

        print(f"[工具结果] {tool_result}")

        # 第二轮：将工具结果返回给 LLM
        messages = [
            HumanMessage(content="北京今天天气怎么样？"),
            response,
            ToolMessage(content=tool_result, tool_call_id=tool_call["id"]),
        ]

        final_response = await llm_with_tools.ainvoke(messages)
        print(f"\n[最终回复] {final_response.content}")

        if final_response.content:
            print("✓ 工具调用测试通过")
            return True
        else:
            print("✗ 最终回复为空")
            return False

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_structured_output(llm: ChatOpenAI) -> bool:
    """测试结构化输出"""
    print("\n=== 测试结构化输出 ===")

    try:
        # 使用 with_structured_output
        structured_llm = llm.with_structured_output(WeatherReport)

        print("发送: 假设北京今天25度晴天，生成一个天气报告")
        response = await structured_llm.ainvoke(
            [HumanMessage(content="假设北京今天25度晴天，生成一个天气报告")]
        )

        print(f"回复类型: {type(response).__name__}")
        print(f"回复内容: {response}")

        if isinstance(response, WeatherReport):
            print(f"  - 城市: {response.city}")
            print(f"  - 温度: {response.temperature}°C")
            print(f"  - 天气: {response.condition}")
            print(f"  - 建议: {response.suggestion}")
            print("✓ 结构化输出测试通过")
            return True
        else:
            print("✗ 返回类型不正确")
            return False

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


# ============================================================================
# 主函数
# ============================================================================


async def run_tests(test_name: str) -> None:
    """运行测试"""
    print("=" * 60)
    print("OpenAI 格式 LLM 测试")
    print("=" * 60)
    print()

    llm = get_llm()

    results = {}

    if test_name in ("all", "simple"):
        results["simple"] = await test_simple_reply(llm)

    if test_name in ("all", "stream"):
        results["stream"] = await test_streaming(llm)

    if test_name in ("all", "tools"):
        results["tools"] = await test_tool_calling(llm)

    if test_name in ("all", "structured"):
        results["structured"] = await test_structured_output(llm)

    # 打印总结
    print()
    print("=" * 60)
    print("测试结果总结")
    print("=" * 60)
    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    all_passed = all(results.values())
    print()
    if all_passed:
        print("所有测试通过！")
    else:
        print("部分测试失败，请检查错误信息。")


def main():
    parser = argparse.ArgumentParser(description="OpenAI 格式 LLM 测试")
    parser.add_argument(
        "--test",
        choices=["simple", "stream", "tools", "structured", "all"],
        default="all",
        help="要运行的测试类型",
    )
    args = parser.parse_args()

    asyncio.run(run_tests(args.test))


if __name__ == "__main__":
    main()
