# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/utils/error_formatter.py
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
统一错误日志格式化工具

解决 loguru 处理多行字符串时的格式问题:
- 使用 print(stderr) 输出格式化的错误框（保持格式）
- 使用 logger.exception 输出堆栈

用法:
    from utils.error_formatter import log_error_with_context

    try:
        ...
    except Exception as e:
        log_error_with_context(
            title="Agent 执行失败",
            context={
                "Session": session_id,
                "URL": request.url,
            },
            error=e,
            suggestions=["检查网络连接", "验证 API Key"]
        )
"""
import sys
from typing import Optional

from utils.logger import logger


def log_error_with_context(
    title: str,
    context: dict,
    error: Exception,
    suggestions: Optional[list[str]] = None,
    error_code: Optional[str] = None,
) -> None:
    """
    输出格式化的错误日志框 + 堆栈

    Args:
        title: 错误标题（如 "Agent 执行失败"）
        context: 上下文信息字典（如 {"Session": "xxx", "URL": "xxx"}）
        error: 异常对象
        suggestions: 解决建议列表（可选）
        error_code: 错误码（可选，用于日志搜索）

    示例输出:
        ================================================================================
        ❌ Agent 执行失败
        ================================================================================

        【上下文信息】
          Session: abc123
          URL: https://example.com

        【错误详情】
          Error Type: ValueError
          Error Message: Invalid input

        【解决建议】
          - 检查网络连接
          - 验证 API Key

        ================================================================================
    """
    error_type = type(error).__name__
    error_msg = str(error)

    # 构建错误日志行
    lines = [
        "=" * 80,
        f"❌ {title}",
        "=" * 80,
        "",
    ]

    # 添加上下文信息
    if context:
        lines.append("【上下文信息】")
        for key, value in context.items():
            lines.append(f"  {key}: {value}")
        lines.append("")

    # 添加错误详情
    lines.extend([
        "【错误详情】",
        f"  Error Type: {error_type}",
        f"  Error Message: {error_msg}",
    ])

    # 添加解决建议
    if suggestions:
        lines.append("")
        lines.append("【解决建议】")
        for suggestion in suggestions:
            lines.append(f"  - {suggestion}")

    lines.extend(["", "=" * 80])

    # 使用 print 输出到 stderr（避免 loguru 格式化问题）
    print("\n".join(lines), file=sys.stderr)

    # 使用 logger.exception 输出堆栈（loguru 正确用法）
    log_msg = f"{title}: {error_type}: {error_msg}"
    if error_code:
        log_msg = f"[{error_code}] {log_msg}"
    logger.exception(log_msg)


def format_error_box(
    title: str,
    sections: dict[str, list[str] | dict[str, str]],
) -> str:
    """
    格式化错误信息框（不输出日志，仅返回字符串）

    Args:
        title: 错误标题
        sections: 各部分内容，支持 list 或 dict
            - list: 每项作为一行输出
            - dict: 输出为 "key: value" 格式

    Returns:
        格式化后的错误信息字符串

    示例:
        error_box = format_error_box(
            title="LLM API 调用失败",
            sections={
                "请求信息": {
                    "Model": "gpt-4",
                    "Base URL": "https://api.openai.com",
                },
                "错误分类": [
                    "❌ 400 Bad Request: True",
                    "⏱️ 429 Rate Limit: False",
                ]
            }
        )
    """
    lines = [
        "=" * 80,
        f"❌ {title}",
        "=" * 80,
        "",
    ]

    for section_name, content in sections.items():
        lines.append(f"【{section_name}】")
        if isinstance(content, dict):
            for key, value in content.items():
                lines.append(f"  {key}: {value}")
        elif isinstance(content, list):
            for item in content:
                lines.append(f"  {item}")
        lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)
