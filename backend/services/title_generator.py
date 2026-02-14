# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/title_generator.py
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
会话标题生成模块

在 fetch_content 完成后，根据用户意图和内容信息快速生成会话标题。
"""

from typing import Optional

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from llm_provider import get_llm
from utils.logger import logger
from utils.json_utils import extract_json_from_text


TITLE_SYSTEM_PROMPT = """根据用户意图和内容信息，生成简洁的会话标题。

要求：
- 10-20 个中文字符
- 突出内容主题，不要泛泛的"分析"、"解读"开头
- 不使用标点符号

返回 JSON: {"title": "标题内容"}"""

PLATFORM_NAMES = {
    "xhs": "小红书",
    "dy": "抖音",
    "bilibili": "B站",
    "ks": "快手",
}


class TitleResult(BaseModel):
    """标题生成结果"""
    title: str = Field(default="新对话")


def fallback_title(content_info: dict = None, user_message: str = "", max_length: int = 30) -> str:
    """回退策略：优先使用 content_info.title"""
    title = (content_info or {}).get("title") or user_message or "新对话"
    return title[:max_length-3] + "..." if len(title) > max_length else title


async def generate_title(
    user_message: str,
    content_info: Optional[dict] = None,
    max_length: int = 30,
) -> TitleResult:
    """
    生成会话标题

    Args:
        user_message: 用户消息
        content_info: 内容详情 (title, desc, platform)
        max_length: 最大长度
    """
    if not content_info:
        return TitleResult(title=fallback_title(content_info, user_message, max_length))

    try:
        llm = get_llm(temperature=0, enable_thinking=False)

        # 构建简洁的上下文
        parts = [f"用户：{user_message[:100]}"]
        if content_info.get("title"):
            parts.append(f"标题：{content_info['title']}")
        if content_info.get("desc"):
            parts.append(f"描述：{content_info['desc'][:150]}")
        if content_info.get("platform"):
            parts.append(f"平台：{PLATFORM_NAMES.get(content_info['platform'], content_info['platform'])}")

        response = await llm.ainvoke([
            SystemMessage(content=TITLE_SYSTEM_PROMPT),
            HumanMessage(content="\n".join(parts)),
        ])

        json_data = extract_json_from_text(response.content)
        title = json_data.get("title", "")

        if len(title) < 3:
            return TitleResult(title=fallback_title(content_info, user_message, max_length))

        if len(title) > max_length:
            title = title[:max_length-3] + "..."

        logger.info(f"Generated title: '{title}'")
        return TitleResult(title=title)

    except Exception as e:
        logger.warning(f"Title generation failed: {e}")
        return TitleResult(title=fallback_title(content_info, user_message, max_length))


__all__ = ["TitleResult", "generate_title", "fallback_title"]
