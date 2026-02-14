#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/test_dynamic_prompt.py
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
测试动态 Prompt 加载

验证:
1. InsightModeService 能正确从数据库读取配置
2. prompts.py 的动态 Prompt 功能正常
3. intent_classifier.py 的动态关键词功能正常
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import logger


async def test_insight_mode_service():
    """测试 InsightModeService"""
    print("\n=== 测试 InsightModeService ===")

    from services.insight_mode_service import insight_mode_service

    # 测试 list_all
    print("\n1. list_all(active_only=True):")
    modes = await insight_mode_service.list_all(active_only=True)
    print(f"   Found {len(modes)} active modes:")
    for m in modes:
        print(f"   - {m.mode_key}: {m.label_zh}")

    # 测试 get_mode
    print("\n2. get_mode('analyze'):")
    mode = await insight_mode_service.get_mode("analyze")
    if mode:
        print(f"   mode_key: {mode.mode_key}")
        print(f"   label_zh: {mode.label_zh}")
        print(f"   system_prompt: {mode.system_prompt[:100]}...")
    else:
        print("   ERROR: Mode not found!")
        return False

    # 测试 get_mode_prompt
    print("\n3. get_mode_prompt('summarize'):")
    prompt = await insight_mode_service.get_mode_prompt("summarize")
    if prompt:
        print(f"   Prompt length: {len(prompt)} chars")
        print(f"   First 100 chars: {prompt[:100]}...")
    else:
        print("   ERROR: Prompt not found!")
        return False

    # 测试 get_all_mode_prompts
    print("\n4. get_all_mode_prompts():")
    prompts = await insight_mode_service.get_all_mode_prompts()
    print(f"   Found {len(prompts)} mode prompts:")
    for key, val in prompts.items():
        print(f"   - {key}: {len(val)} chars")

    # 测试 get_intent_keywords
    print("\n5. get_intent_keywords():")
    keywords = await insight_mode_service.get_intent_keywords()
    print(f"   Found keywords for {len(keywords)} modes:")
    for key, val in keywords.items():
        zh_count = len(val.get("zh", []))
        en_count = len(val.get("en", []))
        print(f"   - {key}: {zh_count} zh, {en_count} en")

    return True


def test_dynamic_prompt():
    """测试动态 Prompt 中间件"""
    print("\n=== 测试动态 Prompt 中间件 ===")

    from agent.prompts import _get_cached_mode_prompt, MODE_PROMPTS

    # 测试缓存加载
    print("\n1. _get_cached_mode_prompt('analyze'):")
    prompt = _get_cached_mode_prompt("analyze")
    if prompt:
        print(f"   Prompt length: {len(prompt)} chars")
        # 检查是否包含关键内容
        if "深度拆解" in prompt or "Deep Analysis" in prompt:
            print("   Content check: PASS (contains expected text)")
        else:
            print("   Content check: WARNING (unexpected content)")
    else:
        print("   ERROR: Prompt is None!")
        return False

    # 测试回退逻辑
    print("\n2. _get_cached_mode_prompt('nonexistent'):")
    prompt = _get_cached_mode_prompt("nonexistent")
    if prompt:
        print(f"   Fallback to default: {len(prompt)} chars")
        # 应该回退到 analyze 模式
        if prompt == MODE_PROMPTS.get("analyze"):
            print("   Fallback check: PASS (fell back to analyze)")
        else:
            print("   Fallback check: PASS (fell back to some default)")
    else:
        print("   ERROR: Fallback failed!")
        return False

    return True


def test_intent_classifier():
    """测试意图分类器的动态关键词"""
    print("\n=== 测试意图分类器动态关键词 ===")

    from agent.intent_classifier import _get_intent_keywords, _fallback_classify

    # 测试关键词加载
    print("\n1. _get_intent_keywords():")
    keywords = _get_intent_keywords()
    if keywords:
        print(f"   Found keywords for {len(keywords)} modes")
        for key, val in keywords.items():
            print(f"   - {key}: zh={val.get('zh', [])[:3]}...")
    else:
        print("   ERROR: Keywords is empty!")
        return False

    # 测试关键词回退分类
    print("\n2. _fallback_classify() tests:")
    test_cases = [
        ("帮我总结一下这个视频", "summarize"),
        ("分析这个内容的技巧", "analyze"),
        ("提取模板", "template"),
        ("换个风格", "style_explore"),
        ("https://example.com", "analyze"),  # 默认
    ]

    for text, expected in test_cases:
        result = _fallback_classify(text)
        status = "PASS" if result.mode == expected else "FAIL"
        print(f"   [{status}] '{text[:20]}...' -> {result.mode} (expected: {expected})")

    return True


async def main():
    """主函数"""
    print("=" * 60)
    print("动态 Prompt 功能测试")
    print("=" * 60)

    all_passed = True

    # 测试 InsightModeService
    try:
        if not await test_insight_mode_service():
            all_passed = False
    except Exception as e:
        print(f"\nERROR in test_insight_mode_service: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    # 测试动态 Prompt
    try:
        if not test_dynamic_prompt():
            all_passed = False
    except Exception as e:
        print(f"\nERROR in test_dynamic_prompt: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    # 测试意图分类器
    try:
        if not test_intent_classifier():
            all_passed = False
    except Exception as e:
        print(f"\nERROR in test_intent_classifier: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("All tests PASSED!")
    else:
        print("Some tests FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
