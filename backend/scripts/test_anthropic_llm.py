#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/test_anthropic_llm.py
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
Anthropic Claude LLM API 测试脚本

测试内容：
1. 简单回复
2. 流式输出
3. 思考功能 (Extended Thinking)
4. 工具调用

使用方法：
    uv run python scripts/test_anthropic_llm.py --test all
    uv run python scripts/test_anthropic_llm.py --test simple
    uv run python scripts/test_anthropic_llm.py --test stream
    uv run python scripts/test_anthropic_llm.py --test thinking
    uv run python scripts/test_anthropic_llm.py --test tools

    # 使用系统环境变量配置（Claude Code 的配置）
    uv run python scripts/test_anthropic_llm.py --test simple --use-system-env
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, ToolMessage

from scripts.test_tools import WeatherReport, calculate, get_weather

# 全局变量：是否使用系统环境变量
USE_SYSTEM_ENV = False


def init_env(use_system_env: bool = False):
    """初始化环境变量"""
    global USE_SYSTEM_ENV
    USE_SYSTEM_ENV = use_system_env

    if use_system_env:
        print("使用系统环境变量配置")
        # 不加载 .env 文件，直接使用系统环境变量
    else:
        # 加载 .env 文件并覆盖系统环境变量
        load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
        print("使用 .env 文件配置")


def get_llm(
    temperature: float = 0.1,
    enable_thinking: bool = False,
    thinking_budget: int = 10000,
) -> ChatAnthropic:
    """创建 Anthropic Claude LLM 实例

    Args:
        temperature: 采样温度
        enable_thinking: 是否启用 extended thinking
        thinking_budget: thinking token 预算
    """
    # 尝试获取 API Key（支持两种变量名）
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    model_name = os.getenv("ANTHROPIC_MODEL_NAME") or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    if not api_key:
        print("错误: 未设置 ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN")
        sys.exit(1)

    print(f"配置信息:")
    print(f"  - Base URL: {base_url or '默认 (api.anthropic.com)'}")
    print(f"  - Model: {model_name}")
    print(f"  - API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
    print(f"  - Extended Thinking: {enable_thinking}")
    print()

    kwargs = {
        "model": model_name,
        "api_key": api_key,
    }

    if base_url:
        kwargs["base_url"] = base_url

    # 启用 extended thinking
    if enable_thinking:
        kwargs["temperature"] = 1  # thinking 模式必须 temperature=1
        kwargs["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget,
        }
        # max_tokens 必须大于 thinking_budget
        kwargs["max_tokens"] = thinking_budget + 4096
    else:
        kwargs["temperature"] = temperature
        kwargs["max_tokens"] = 4096

    return ChatAnthropic(**kwargs)


# ============================================================================
# 辅助函数
# ============================================================================


def parse_content_blocks(content: Any) -> tuple[str, str]:
    """解析 Claude 的 content blocks

    Returns:
        (thinking_content, text_content)
    """
    thinking_content = ""
    text_content = ""

    if isinstance(content, str):
        return "", content

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type == "thinking":
                    thinking_content += block.get("thinking", "")
                elif block_type == "text":
                    text_content += block.get("text", "")
            elif isinstance(block, str):
                text_content += block

    return thinking_content, text_content


# ============================================================================
# 测试函数
# ============================================================================


async def test_simple_reply(llm: ChatAnthropic) -> bool:
    """测试简单对话"""
    print("=== 测试简单回复 ===")

    try:
        response = await llm.ainvoke([HumanMessage(content="你好，请用一句话介绍自己")])

        print(f"回复类型: {type(response).__name__}")
        print(f"原始内容类型: {type(response.content)}")

        thinking, text = parse_content_blocks(response.content)

        if thinking:
            print(f"[思考] {thinking[:100]}...")
        print(f"[回复] {text}")

        if text:
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


async def test_streaming(llm: ChatAnthropic) -> bool:
    """测试流式输出"""
    print("\n=== 测试流式输出 ===")

    try:
        print("[流式] ", end="", flush=True)
        chunk_count = 0
        full_content = ""

        async for chunk in llm.astream([HumanMessage(content="用三句话讲个简短的笑话")]):
            content = chunk.content

            # Claude 的流式输出可能是 list 或 string
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        text = block.get("text", "")
                        if text:
                            print(text, end="", flush=True)
                            full_content += text
                    elif isinstance(block, str):
                        print(block, end="", flush=True)
                        full_content += block
            elif isinstance(content, str) and content:
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


async def test_thinking(llm_factory) -> bool:
    """测试 Extended Thinking 功能"""
    print("\n=== 测试 Extended Thinking ===")

    try:
        # 创建启用 thinking 的 LLM
        llm = llm_factory(enable_thinking=True, thinking_budget=5000)

        print("发送: 请分析 25 * 37 等于多少，展示你的思考过程")

        # 非流式测试
        print("\n--- 非流式模式 ---")
        response = await llm.ainvoke(
            [HumanMessage(content="请分析 25 * 37 等于多少，展示你的思考过程")]
        )

        print(f"回复类型: {type(response).__name__}")
        print(f"原始内容类型: {type(response.content)}")

        thinking, text = parse_content_blocks(response.content)

        has_thinking = False
        if thinking:
            print(f"\n[思考内容] (共 {len(thinking)} 字符)")
            print(f"  {thinking[:500]}...")
            has_thinking = True
        else:
            print("[思考内容] 无")

        print(f"\n[回复内容]")
        print(f"  {text}")

        # 流式测试
        print("\n--- 流式模式 ---")
        thinking_content = ""
        text_content = ""

        async for chunk in llm.astream(
            [HumanMessage(content="15 + 28 等于多少？")]
        ):
            content = chunk.content

            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type", "")
                        if block_type in ("thinking", "thinking_delta"):
                            t = block.get("thinking", "")
                            if t:
                                thinking_content += t
                                print(f"[T]", end="", flush=True)
                        elif block_type in ("text", "text_delta"):
                            t = block.get("text", "")
                            if t:
                                text_content += t
                                print(t, end="", flush=True)
                        elif block_type == "content_block_delta":
                            # 处理嵌套的 delta 结构
                            delta = block.get("delta", {})
                            delta_type = delta.get("type", "")
                            if delta_type == "thinking_delta":
                                t = delta.get("thinking", "")
                                if t:
                                    thinking_content += t
                                    print(f"[T]", end="", flush=True)
                            elif delta_type == "text_delta":
                                t = delta.get("text", "")
                                if t:
                                    text_content += t
                                    print(t, end="", flush=True)

        print()
        print(f"\n流式思考内容长度: {len(thinking_content)} 字符")
        print(f"流式文本内容: {text_content}")

        if has_thinking or thinking_content:
            print("\n✓ Extended Thinking 测试通过")
            return True
        else:
            print("\n⚠ 未检测到思考内容（可能模型不支持或配置问题）")
            return False

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_tool_calling(llm: ChatAnthropic) -> bool:
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

        thinking, text = parse_content_blocks(response.content)
        if thinking:
            print(f"[思考] {thinking[:100]}...")
        if text:
            print(f"[回复] {text}")

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

        _, final_text = parse_content_blocks(final_response.content)
        print(f"\n[最终回复] {final_text}")

        if final_text:
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


async def test_structured_output(llm: ChatAnthropic) -> bool:
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
    print("Anthropic Claude LLM 测试")
    print("=" * 60)
    print()

    # 创建 LLM 工厂函数
    def llm_factory(enable_thinking: bool = False, thinking_budget: int = 10000):
        return get_llm(enable_thinking=enable_thinking, thinking_budget=thinking_budget)

    # 普通 LLM（不启用 thinking）
    llm = llm_factory()

    results = {}

    if test_name in ("all", "simple"):
        results["simple"] = await test_simple_reply(llm)

    if test_name in ("all", "stream"):
        results["stream"] = await test_streaming(llm)

    if test_name in ("all", "thinking"):
        results["thinking"] = await test_thinking(llm_factory)

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
    parser = argparse.ArgumentParser(description="Anthropic Claude LLM 测试")
    parser.add_argument(
        "--test",
        choices=["simple", "stream", "thinking", "tools", "structured", "all"],
        default="all",
        help="要运行的测试类型",
    )
    parser.add_argument(
        "--use-system-env",
        action="store_true",
        help="使用系统环境变量配置（而非 .env 文件）",
    )
    args = parser.parse_args()

    # 初始化环境变量
    init_env(use_system_env=args.use_system_env)

    asyncio.run(run_tests(args.test))


if __name__ == "__main__":
    main()
