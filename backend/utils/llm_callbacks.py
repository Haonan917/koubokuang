# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/utils/llm_callbacks.py
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
LLM Debug Callback Handler - LLM 调用调试回调

功能：
- 记录 LLM 请求参数（model, temperature, prompt等）
- 记录 LLM 响应内容和 token 使用量
- 记录调用延迟
- 记录错误详情
- 敏感信息脱敏（API Key）
"""
import sys
import time
import json
import traceback
from typing import Any, Dict, List, Optional
from datetime import datetime

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from utils.logger import logger


class LLMDebugCallbackHandler(BaseCallbackHandler):
    """LLM 调试回调处理器"""

    def __init__(
        self,
        log_level: str = "DEBUG",
        mask_api_keys: bool = True,
        max_content_length: int = 500,
    ):
        super().__init__()
        self.log_level = log_level
        self.mask_api_keys = mask_api_keys
        self.max_content_length = max_content_length
        self._call_times: Dict[str, float] = {}
        # 缓存最近的请求信息，用于错误时输出
        self._last_request: Dict[str, Any] = {}

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """LLM 调用开始 - 缓存请求信息，仅在 DEBUG 级别记录"""
        self._call_times[str(run_id)] = time.time()

        # 提取关键信息
        model_name = serialized.get("name", "unknown")
        model_kwargs = serialized.get("kwargs", {}).copy()

        # 脱敏处理
        if self.mask_api_keys and "api_key" in model_kwargs:
            api_key = model_kwargs["api_key"]
            model_kwargs["api_key"] = api_key[:12] + "..." if api_key else None

        # 截断 prompt
        prompt_preview = prompts[0][:self.max_content_length] if prompts else ""
        full_prompt = prompts[0] if prompts else ""
        if prompts and len(prompts[0]) > self.max_content_length:
            prompt_preview += f"... ({len(prompts[0])} chars total)"

        # 缓存请求信息（用于错误时输出）
        self._last_request[str(run_id)] = {
            "model": model_name,
            "temperature": model_kwargs.get("temperature"),
            "max_tokens": model_kwargs.get("max_tokens"),
            "base_url": model_kwargs.get("base_url"),
            "extra_body": model_kwargs.get("extra_body", {}),
            "reasoning": model_kwargs.get("reasoning", {}),
            "prompt_preview": prompt_preview,
            "prompt_full": full_prompt,
        }

        # 正常情况下使用 DEBUG 级别（不干扰）
        logger.debug(
            f"[LLM Request] run_id={run_id}\n"
            f"  Model: {model_name}\n"
            f"  Temperature: {model_kwargs.get('temperature')}\n"
            f"  Base URL: {model_kwargs.get('base_url')}\n"
            f"  Prompt: {prompt_preview}"
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """LLM 调用结束 - 仅在 DEBUG 级别记录"""
        elapsed = time.time() - self._call_times.pop(str(run_id), time.time())

        # 清理缓存的请求信息
        self._last_request.pop(str(run_id), None)

        # 提取 token 使用量
        llm_output = response.llm_output or {}
        token_usage = llm_output.get("token_usage", {})

        # 提取响应内容
        generations = response.generations[0] if response.generations else []
        response_text = generations[0].text if generations else ""
        response_preview = response_text[:self.max_content_length]
        if len(response_text) > self.max_content_length:
            response_preview += f"... ({len(response_text)} chars total)"

        # 正常情况下使用 DEBUG 级别（不干扰）
        logger.debug(
            f"[LLM Response] run_id={run_id}\n"
            f"  Latency: {elapsed:.2f}s\n"
            f"  Tokens: {token_usage.get('total_tokens', 'N/A')}\n"
            f"  Response: {response_preview}"
        )

    def on_llm_error(
        self,
        error: Exception,
        *,
        run_id: Any,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """LLM 调用错误 - 输出完整的请求上下文和错误信息"""
        elapsed = time.time() - self._call_times.pop(str(run_id), time.time())

        # 获取缓存的请求信息
        request_info = self._last_request.pop(str(run_id), {})

        # 分析错误类型
        error_type = type(error).__name__
        error_msg = str(error)

        # 特殊处理常见错误
        is_bad_request = "400" in error_msg
        is_rate_limit = "429" in error_msg or "rate limit" in error_msg.lower()
        is_timeout = "timeout" in error_msg.lower()
        is_reasoning_error = "Unknown parameter" in error_msg and "reasoning" in error_msg

        # 构建详细的错误日志（包含请求上下文）
        error_log = [
            "=" * 80,
            f"❌ LLM API 调用失败 [run_id={run_id}]",
            "=" * 80,
            "",
            "【请求信息】",
            f"  Model: {request_info.get('model', 'N/A')}",
            f"  Base URL: {request_info.get('base_url', 'N/A')}",
            f"  Temperature: {request_info.get('temperature', 'N/A')}",
            f"  Max Tokens: {request_info.get('max_tokens', 'N/A')}",
            f"  Extra Body: {json.dumps(request_info.get('extra_body', {}), ensure_ascii=False)}",
            f"  Reasoning: {json.dumps(request_info.get('reasoning', {}), ensure_ascii=False)}",
            "",
            "【Prompt (前500字符)】",
            f"  {request_info.get('prompt_preview', 'N/A')}",
            "",
            "【错误详情】",
            f"  Error Type: {error_type}",
            f"  Error Message: {error_msg}",
            f"  Elapsed: {elapsed:.2f}s",
            "",
            "【错误分类】",
            f"  ❌ 400 Bad Request: {is_bad_request}",
            f"  ⏱️  429 Rate Limit: {is_rate_limit}",
            f"  🕐 Timeout: {is_timeout}",
            f"  🔧 Reasoning Parameter Error: {is_reasoning_error}",
            "",
            "【解决建议】",
        ]

        # 根据错误类型添加具体建议
        if is_reasoning_error:
            error_log.extend([
                "  ⚠️  检测到 reasoning 参数错误！",
                "  👉 解决方法：在 .env 中设置 LLM_FORCE_DISABLE_REASONING=true",
                "  👉 原因：您的 API endpoint 不支持 reasoning 参数",
            ])
        elif is_rate_limit:
            error_log.extend([
                "  ⚠️  触发了 API 速率限制！",
                "  👉 解决方法：降低请求频率或升级 API plan",
            ])
        elif is_timeout:
            error_log.extend([
                "  ⚠️  请求超时！",
                "  👉 解决方法：检查网络连接，或增加 timeout 配置",
            ])
        elif is_bad_request:
            error_log.extend([
                "  ⚠️  请求参数错误！",
                "  👉 解决方法：检查 model、temperature、max_tokens 等参数是否正确",
            ])
        else:
            error_log.append("  👉 查看下方完整错误堆栈获取更多信息")

        # 从 error 对象提取堆栈（因为 on_llm_error 回调中没有活跃的异常上下文）
        error_log.append("")
        error_log.append("【错误堆栈】")
        if error.__traceback__:
            # 使用 format_exception 从异常对象提取堆栈
            tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
            error_log.append("".join(tb_lines))
        else:
            error_log.append(f"  {error_type}: {error_msg}")
        error_log.append("=" * 80)
        error_log.append("")

        # 直接打印错误信息到 stderr（避免 loguru 格式化问题）
        print("\n".join(error_log), file=sys.stderr)

        # 使用 logger.error 记录（注意：on_llm_error 回调中没有活跃异常上下文，不能用 exception）
        logger.error(f"LLM API 调用失败: {error_type}: {error_msg}")


def get_debug_callback_handler() -> LLMDebugCallbackHandler:
    """每次调用返回新的 callback handler 实例

    避免跨请求的状态泄漏。每个请求有独立的 _call_times 和 _last_request 字典。
    """
    return LLMDebugCallbackHandler(
        log_level="DEBUG",
        mask_api_keys=True,
        max_content_length=500,
    )
