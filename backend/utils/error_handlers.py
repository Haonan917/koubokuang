# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/utils/error_handlers.py
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
统一错误处理工具

提供 Agent/LLM 相关的错误检测和处理功能：
- 检测 reasoning 参数不支持错误
- 构建统一错误上下文
- 生成用户友好的错误信息

用法:
    from utils.error_handlers import (
        detect_reasoning_parameter_error,
        build_agent_error_context,
        log_agent_error,
    )

    try:
        async for event in agent.astream_events(...):
            ...
    except Exception as e:
        suggestion = detect_reasoning_parameter_error(e)
        context = build_agent_error_context(
            error=e,
            session_id=session_id,
            url=request.url,
            mode=mode,
        )
        log_agent_error(e, context, "analyze")

        if suggestion:
            context["suggestion"] = suggestion
"""

from typing import Any, Dict, Optional

from utils.error_formatter import log_error_with_context


def detect_reasoning_parameter_error(error: Exception) -> Optional[str]:
    """检测 reasoning 参数不支持错误

    当 API endpoint 不支持 reasoning 参数时（如使用非官方 OpenAI 代理），
    会返回 "Unknown parameter: reasoning" 错误。

    Args:
        error: 异常对象

    Returns:
        解决建议字符串，如果不是 reasoning 错误则返回 None
    """
    error_msg = str(error).lower()

    # 检测 "Unknown parameter: reasoning" 错误
    if "unknown parameter" in error_msg and "reasoning" in error_msg:
        return (
            "检测到 'Unknown parameter: reasoning' 错误。"
            "您使用的 API endpoint 可能不支持 reasoning 参数。"
            "解决方法：在 .env 中设置 LLM_FORCE_DISABLE_REASONING=true"
        )

    # 检测其他 reasoning 相关错误
    if "reasoning" in error_msg and ("not supported" in error_msg or "invalid" in error_msg):
        return (
            "检测到 reasoning 参数相关错误。"
            "您使用的模型或 API 可能不支持 reasoning 功能。"
            "解决方法：在 .env 中设置 LLM_FORCE_DISABLE_REASONING=true"
        )

    return None


def detect_rate_limit_error(error: Exception) -> Optional[str]:
    """检测 API 速率限制错误

    Args:
        error: 异常对象

    Returns:
        解决建议字符串，如果不是速率限制错误则返回 None
    """
    error_msg = str(error).lower()

    if "rate limit" in error_msg or "429" in error_msg or "too many requests" in error_msg:
        return (
            "检测到 API 速率限制错误 (429 Too Many Requests)。"
            "解决方法：1) 等待一段时间后重试 2) 升级 API 配额 3) 切换到其他 LLM Provider"
        )

    return None


def detect_authentication_error(error: Exception) -> Optional[str]:
    """检测 API 认证错误

    Args:
        error: 异常对象

    Returns:
        解决建议字符串，如果不是认证错误则返回 None
    """
    error_msg = str(error).lower()

    if "unauthorized" in error_msg or "401" in error_msg or "invalid api key" in error_msg:
        return (
            "检测到 API 认证错误 (401 Unauthorized)。"
            "解决方法：检查 .env 中的 API_KEY 是否正确配置"
        )

    if "forbidden" in error_msg or "403" in error_msg:
        return (
            "检测到 API 权限错误 (403 Forbidden)。"
            "解决方法：检查 API Key 是否有相应权限，或账户是否已激活"
        )

    return None


def build_agent_error_context(
    error: Exception,
    session_id: str,
    url: Optional[str] = None,
    mode: Optional[str] = None,
    message_preview: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """构建统一的 Agent 错误上下文

    Args:
        error: 异常对象
        session_id: 会话 ID
        url: 请求的 URL（可选）
        mode: 分析模式（可选）
        message_preview: 消息预览（可选，用于 chat 端点）
        **kwargs: 其他上下文信息

    Returns:
        错误上下文字典
    """
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "session_id": session_id,
    }

    if url:
        context["url"] = url
    if mode:
        context["mode"] = mode
    if message_preview:
        context["message_preview"] = message_preview

    # 添加其他上下文
    context.update(kwargs)

    # 检测特定错误类型并添加建议
    suggestion = (
        detect_reasoning_parameter_error(error) or
        detect_rate_limit_error(error) or
        detect_authentication_error(error)
    )

    if suggestion:
        context["suggestion"] = suggestion

    return context


def log_agent_error(
    error: Exception,
    context: Dict[str, Any],
    endpoint_name: str,
) -> None:
    """统一的 Agent 错误日志

    使用 error_formatter 输出格式化的错误信息。

    Args:
        error: 异常对象
        context: 错误上下文（由 build_agent_error_context 生成）
        endpoint_name: 端点名称（如 "analyze", "chat"）
    """
    # 构建日志上下文
    log_context = {
        "Session": context.get("session_id", "N/A"),
    }

    if context.get("url"):
        log_context["URL"] = context["url"]
    if context.get("mode"):
        log_context["Mode"] = context["mode"]
    if context.get("message_preview"):
        log_context["Message"] = context["message_preview"]

    # 构建建议列表
    suggestions = []
    if context.get("suggestion"):
        suggestions.append(context["suggestion"])

    # 调用统一的错误日志工具
    log_error_with_context(
        title=f"{endpoint_name.title()} 执行失败",
        context=log_context,
        error=error,
        suggestions=suggestions if suggestions else None,
        error_code=f"{endpoint_name.upper()}_ERROR",
    )


def build_sse_error_data(
    error: Exception,
    context: Dict[str, Any],
    error_code: str = "AGENT_ERROR",
) -> Dict[str, Any]:
    """构建 SSE 错误事件数据

    Args:
        error: 异常对象
        context: 错误上下文
        error_code: 错误码

    Returns:
        SSE 错误事件数据
    """
    error_data = {
        "code": error_code,
        "message": str(error),
        "context": context,
    }

    if context.get("suggestion"):
        error_data["suggestion"] = context["suggestion"]

    return error_data
