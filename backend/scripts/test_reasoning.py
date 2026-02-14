#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/test_reasoning.py
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
统一的 Reasoning/Thinking 测试脚本

测试各 LLM Provider 的思维链输出功能：
- Anthropic Claude (Extended Thinking)
- OpenAI GPT-5 (Reasoning)
- DeepSeek Reasoner
- GLM-4.7 (Thinking)
- Kimi K2 (Reasoning)
- MiniMax M2.x (<think> 标签)

使用方法：
    # 测试当前配置的 LLM
    uv run python scripts/test_reasoning.py

    # 测试指定 Provider
    uv run python scripts/test_reasoning.py --provider openai

    # 测试指定模型
    uv run python scripts/test_reasoning.py --provider openai --model glm-4.7

    # 测试所有已知配置
    uv run python scripts/test_reasoning.py --all
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# 加载环境变量
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)

from agent.stream.reasoning_extractor import ReasoningExtractor
from llm_provider import get_llm
from utils.logger import logger


# 测试提示词（需要推理的问题）
TEST_PROMPT = "请逐步思考：9.11 和 9.8 哪个更大？先分析整数部分，再分析小数部分。"


async def test_reasoning_stream(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    enable_thinking: bool = True,
) -> Tuple[bool, str, str]:
    """
    测试单个 Provider 的 reasoning 流式输出功能

    Args:
        provider: LLM 提供商（如果不指定，使用当前配置）
        model_name: 模型名称
        enable_thinking: 是否启用 thinking

    Returns:
        Tuple[has_reasoning, text_content, reasoning_content]
    """
    try:
        # 如果指定了 provider，临时修改环境变量
        original_provider = os.environ.get("LLM_PROVIDER")
        if provider:
            os.environ["LLM_PROVIDER"] = provider

        # 获取 LLM 实例
        llm = get_llm(
            temperature=0.7,
            model_name=model_name,
            enable_thinking=enable_thinking,
        )

        # 恢复原始 provider
        if original_provider:
            os.environ["LLM_PROVIDER"] = original_provider
        elif provider:
            del os.environ["LLM_PROVIDER"]

        # 流式调用测试
        extractor = ReasoningExtractor()
        reasoning_content = ""
        text_content = ""

        print(f"\n[流式输出]")
        print("-" * 40)

        async for chunk in llm.astream([HumanMessage(content=TEST_PROMPT)]):
            result = extractor.extract(chunk)

            # 显示 reasoning 内容（带 [R] 前缀）
            if result.reasoning_content:
                reasoning_content += result.reasoning_content
                print(f"[R] {result.reasoning_content}", end="", flush=True)

            # 显示文本内容
            if result.text_content:
                text_content += result.text_content
                print(result.text_content, end="", flush=True)

        # 刷新缓冲区
        final = extractor.flush()
        if final.reasoning_content:
            reasoning_content += final.reasoning_content
            print(f"[R] {final.reasoning_content}", end="", flush=True)
        if final.text_content:
            text_content += final.text_content
            print(final.text_content, end="", flush=True)

        print()
        print("-" * 40)

        # 判断结果
        has_reasoning = bool(reasoning_content.strip())
        has_content = bool(text_content.strip())

        # 打印检测来源
        if extractor.detected_source:
            print(f"[检测来源] {extractor.detected_source}")

        return has_reasoning, text_content, reasoning_content

    except Exception as e:
        logger.exception(f"测试失败: {e}")
        return False, "", ""


async def test_single_provider(
    provider: str,
    model_name: str,
    description: str,
) -> bool:
    """测试单个 Provider"""
    print()
    print("=" * 60)
    print(f"测试: {description}")
    print(f"Provider: {provider}, Model: {model_name}")
    print("=" * 60)

    has_reasoning, text_content, reasoning_content = await test_reasoning_stream(
        provider=provider,
        model_name=model_name,
        enable_thinking=True,
    )

    # 打印结果摘要
    print()
    print("[结果摘要]")
    if has_reasoning:
        print(f"  ✅ Reasoning 检测成功")
        print(f"  Reasoning 长度: {len(reasoning_content)} 字符")
        preview = reasoning_content[:200].replace("\n", " ")
        print(f"  Reasoning 预览: {preview}...")
    else:
        print(f"  ⚠️ 未检测到 Reasoning 输出")

    if text_content:
        print(f"  ✅ 文本内容输出正常")
        print(f"  文本长度: {len(text_content)} 字符")
    else:
        print(f"  ⚠️ 无文本内容输出")

    return has_reasoning


async def test_all_providers() -> None:
    """测试所有已知的 Provider 配置"""
    # 定义测试配置
    test_configs = [
        # (provider, model_name, description)
        ("anthropic", None, "Claude Extended Thinking"),
        ("deepseek", "deepseek-reasoner", "DeepSeek Reasoner"),
        ("openai", "gpt-5", "GPT-5 Reasoning"),
        ("openai", "glm-4.7", "GLM-4.7 Thinking"),
        ("openai", "kimi-k2-thinking", "Kimi K2 Reasoning"),
        ("openai", "MiniMax-M2.1-lightning", "MiniMax <think> tags"),
    ]

    results = []

    for provider, model, desc in test_configs:
        try:
            success = await test_single_provider(provider, model, desc)
            results.append((desc, success))
        except Exception as e:
            logger.warning(f"跳过 {desc}: {e}")
            results.append((desc, False))

    # 汇总结果
    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for desc, success in results:
        status = "✅ Reasoning" if success else "❌ No Reasoning"
        print(f"  {status} - {desc}")


async def main():
    parser = argparse.ArgumentParser(description="LLM Reasoning/Thinking 测试")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai", "deepseek", "ollama"],
        help="LLM 提供商",
    )
    parser.add_argument(
        "--model",
        help="模型名称",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="测试所有已知配置",
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="禁用 thinking/reasoning",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("LLM Reasoning/Thinking 统一测试")
    print("=" * 60)

    if args.all:
        await test_all_providers()
    else:
        # 测试当前配置或指定的配置
        provider = args.provider
        model = args.model
        enable_thinking = not args.no_thinking

        if provider:
            desc = f"{provider.upper()} ({model or 'default'})"
        else:
            desc = "当前配置"

        success = await test_single_provider(
            provider=provider or os.environ.get("LLM_PROVIDER", "openai"),
            model_name=model,
            description=desc,
        )

        print()
        if success:
            print("✅ 测试通过！Reasoning 输出正常")
        else:
            print("⚠️ 测试完成，但未检测到 Reasoning 输出")
            print("  可能原因：")
            print("  1. 模型不支持 thinking/reasoning")
            print("  2. llm_provider.py 中缺少该模型的配置")
            print("  3. API 参数格式不正确")


if __name__ == "__main__":
    asyncio.run(main())
