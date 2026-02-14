# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/errors.py
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
统一错误处理 - Remix Agent 工具异常定义

提供标准化的错误码和异常类，用于所有 Tool 的错误处理。
"""
from enum import Enum
from typing import Optional, Dict, Any

from i18n import t, get_language


class RemixErrorCode(str, Enum):
    """Remix Agent 错误码"""

    # 链接解析错误
    INVALID_URL = "INVALID_URL"  # 无法识别的链接格式

    # 内容获取错误
    CONTENT_NOT_FOUND = "CONTENT_NOT_FOUND"  # 内容不存在或已删除
    COOKIES_NOT_FOUND = "COOKIES_NOT_FOUND"  # 平台 cookies 未配置
    FETCH_FAILED = "FETCH_FAILED"  # 内容获取失败

    # 视频处理错误
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"  # 视频下载失败
    AUDIO_EXTRACT_FAILED = "AUDIO_EXTRACT_FAILED"  # 音频提取失败
    ASR_FAILED = "ASR_FAILED"  # 语音转录失败
    VOICE_CLONE_FAILED = "VOICE_CLONE_FAILED"  # 语音克隆失败
    TTS_FAILED = "TTS_FAILED"  # 文本转语音失败
    LIPSYNC_FAILED = "LIPSYNC_FAILED"  # 唇形同步失败

    # 分析生成错误
    ANALYSIS_FAILED = "ANALYSIS_FAILED"  # 内容分析失败
    GENERATION_FAILED = "GENERATION_FAILED"  # 文案生成失败

    # 状态错误
    MISSING_STATE = "MISSING_STATE"  # 缺少必需的状态（未按顺序调用 Tool）

    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"  # 内部错误


class RemixToolException(Exception):
    """
    Remix Agent Tool 统一异常

    所有 Tool 抛出的异常都应使用此类，确保前端能统一处理错误。

    Attributes:
        error_code: 错误码枚举
        message: 用户友好的错误消息
        details: 额外的错误详情（用于调试）
    """

    def __init__(
        self,
        error_code: RemixErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{error_code.value}] {message}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于 JSON 序列化"""
        return {
            "code": self.error_code.value,
            "message": self.message,
            "details": self.details,
        }


def require_state(state: Dict[str, Any], *fields: str) -> None:
    """
    验证状态中是否包含必需的字段

    Args:
        state: Agent 状态字典
        *fields: 必需的字段名

    Raises:
        RemixToolException: 如果缺少必需字段
    """
    missing = [f for f in fields if not state.get(f)]
    if missing:
        raise RemixToolException(
            RemixErrorCode.MISSING_STATE,
            t("errors.missingState", fields=", ".join(missing)),
            {"missing_fields": missing, "available_fields": list(state.keys())},
        )


def build_tool_user_message(error: RemixToolException) -> str:
    """生成用于工具失败的用户可读提示"""
    base_message = error.message or t("errors.internalError")
    if error.error_code not in {
        RemixErrorCode.INVALID_URL,
        RemixErrorCode.CONTENT_NOT_FOUND,
        RemixErrorCode.FETCH_FAILED,
    }:
        return base_message

    hint = t("errors.reenterUrl")
    punctuation = "。" if get_language().startswith("zh") else " "
    return f"[TOOL_ERROR] {base_message}{punctuation}{hint}"
