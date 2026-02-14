# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/test_llm_logging.py
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
测试 LLM 调试日志 - 验证 callback 和错误处理是否正常工作

用法:
    uv run python scripts/test_llm_logging.py
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from langchain_core.messages import HumanMessage
from llm_provider import get_llm
from utils.logger import logger


async def test_normal_call():
    """测试正常的 LLM 调用"""
    logger.info("=" * 60)
    logger.info("测试 1: 正常的 LLM 调用")
    logger.info("=" * 60)

    try:
        llm = get_llm(temperature=0.3)
        response = await llm.ainvoke([HumanMessage(content="你好，请用一句话介绍你自己")])
        logger.info(f"✅ 测试成功，响应长度: {len(response.content)} 字符")
    except Exception as e:
        logger.exception(f"❌ 测试失败: {e}")


async def test_error_call():
    """测试错误的 LLM 调用（模拟 API 错误）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 错误的 LLM 调用（无效 API Key）")
    logger.info("=" * 60)

    try:
        # 使用无效的 API key
        llm = get_llm(temperature=0.3, model_name="gpt-3.5-turbo")
        llm.api_key = "invalid_key"
        response = await llm.ainvoke([HumanMessage(content="测试")])
        logger.info(f"响应: {response.content}")
    except Exception as e:
        logger.exception(
            f"❌ 预期的错误（用于测试错误日志）: "
            f"错误类型={type(e).__name__}, 错误消息={str(e)}"
        )


async def test_reasoning_parameter():
    """测试 reasoning 参数配置"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: Reasoning 参数配置检查")
    logger.info("=" * 60)

    from config import settings

    logger.info(f"当前配置:")
    logger.info(f"  LLM_PROVIDER: {settings.LLM_PROVIDER}")
    logger.info(f"  LLM_FORCE_DISABLE_REASONING: {getattr(settings, 'LLM_FORCE_DISABLE_REASONING', False)}")
    logger.info(f"  LLM_DEBUG_LOGGING: {getattr(settings, 'LLM_DEBUG_LOGGING', False)}")
    logger.info(f"  LOG_LEVEL: {settings.LOG_LEVEL}")
    logger.info(f"  LOG_FORMAT: {getattr(settings, 'LOG_FORMAT', 'pretty')}")


async def main():
    """运行所有测试"""
    logger.info("开始 LLM 日志测试")
    logger.info(f"当前工作目录: {Path.cwd()}")

    await test_reasoning_parameter()
    await test_normal_call()
    await test_error_call()

    logger.info("\n" + "=" * 60)
    logger.info("测试完成！")
    logger.info("=" * 60)
    logger.info("\n检查要点:")
    logger.info("1. 是否看到 [LLM Request] 日志（包含 model、temperature、base_url 等）")
    logger.info("2. 是否看到 [LLM Response] 日志（包含 latency、token 统计）")
    logger.info("3. 错误日志是否包含完整的堆栈和上下文信息")
    logger.info("\n如果看不到 [LLM Request/Response] 日志，请检查:")
    logger.info("- config/settings.py 中是否正确配置了 LLM provider")
    logger.info("- .env 文件是否存在并配置正确")


if __name__ == "__main__":
    asyncio.run(main())
