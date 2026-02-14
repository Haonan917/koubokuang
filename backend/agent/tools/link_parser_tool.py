# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/tools/link_parser_tool.py
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
链接解析工具 - 解析社交媒体链接

支持: 小红书、抖音、B站、快手

基于 LangChain 1.0 ToolRuntime 模式。
"""

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agent.state import RemixContext
from agent.errors import RemixToolException, RemixErrorCode, build_tool_user_message
from i18n import t


@tool
def parse_link(url: str, runtime: ToolRuntime[RemixContext]) -> Command:
    """解析社交媒体链接，识别平台和内容ID。

    支持的平台:
    - 小红书 (xhs): xiaohongshu.com, xhslink.com
    - 抖音 (dy): douyin.com, v.douyin.com
    - B站 (bilibili): bilibili.com, b23.tv
    - 快手 (ks): kuaishou.com, v.kuaishou.com

    Args:
        url: 社交媒体链接（支持长链接和短链接）

    Returns:
        Command 更新 parsed_link 状态
    """
    from services.link_parser import LinkParser

    # 发送进度更新
    runtime.stream_writer({"stage": "parsing", "message": t("progress.parsingLink")})

    try:
        parser = LinkParser()
        result = parser.parse(url)

        if not result:
            raise RemixToolException(
                RemixErrorCode.INVALID_URL,
                t("errors.invalidUrl"),
                {"url": url, "supported_platforms": [
                    t("platforms.xhs"), t("platforms.dy"),
                    t("platforms.bilibili"), t("platforms.ks")
                ]},
            )

        parsed_data = {
            "platform": result.platform.value,
            "content_id": result.content_id,
            "original_url": result.original_url,
            "is_short_link": result.is_short_link,
        }

        platform_name = t(f"platforms.{result.platform.value}")

        runtime.stream_writer({
            "stage": "parsing",
            "message": t("progress.parseComplete", platform=platform_name),
            "result": parsed_data,
        })

        # 返回包含 ToolMessage 的 Command
        result_text = f"链接解析成功: {platform_name} ({result.platform.value}), content_id={result.content_id}"

        return Command(update={
            "messages": [ToolMessage(content=result_text, tool_call_id=runtime.tool_call_id)],
            "parsed_link": parsed_data,
            "current_stage": "链接解析完成",
        })
    except RemixToolException as e:
        error_message = build_tool_user_message(e)
        return Command(update={
            "messages": [ToolMessage(content=error_message, tool_call_id=runtime.tool_call_id)],
            "current_stage": "链接解析失败",
        })
