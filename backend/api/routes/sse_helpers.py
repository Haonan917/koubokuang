# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/api/routes/sse_helpers.py
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
SSE 事件生成辅助模块

提取 /analyze 和 /chat 端点共享的事件流处理逻辑。
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SegmentCollector:
    """
    收集流式事件并转换为 segments 用于持久化

    将 intent_*, reasoning_*, tool_call_*, text_delta 等事件转换为结构化的 segments 列表。
    """

    segments: list[dict] = field(default_factory=list)
    assistant_chunks: list[str] = field(default_factory=list)

    # 内部状态
    _current_intent: Optional[dict] = field(default=None, repr=False)
    _current_thinking: Optional[dict] = field(default=None, repr=False)
    _current_tool_call: Optional[dict] = field(default=None, repr=False)
    _current_sub_step: Optional[dict] = field(default=None, repr=False)
    _thinking_chunks: list[str] = field(default_factory=list, repr=False)

    def process_event(self, event_type: str, event_data: dict, timestamp: float = 0) -> Optional[dict]:
        """
        处理单个事件，更新内部状态

        Args:
            event_type: 事件类型（Vercel AI SDK 标准）
            event_data: 事件数据
            timestamp: 事件时间戳

        Returns:
            如果是 tool_call_finish 且是 fetch_content，返回 content_info 数据供额外发送
        """
        extra_event = None

        # ========== 意图识别事件 ==========
        if event_type == "intent_start":
            self._current_intent = {
                "type": "intent",
                "status": "running",
                "message": event_data.get("message", ""),
                "start_time": timestamp,
            }

        elif event_type == "intent_end":
            if self._current_intent:
                self._current_intent.update({
                    "status": "completed",
                    "mode": event_data.get("mode"),
                    "mode_name": event_data.get("mode_name"),
                    "confidence": event_data.get("confidence"),
                    "reasoning": event_data.get("reasoning"),
                    "duration": timestamp - self._current_intent.get("start_time", 0),
                })
                self._current_intent.pop("start_time", None)
                self.segments.append(self._current_intent)
                self._current_intent = None

        # ========== 思考事件 ==========
        elif event_type == "reasoning_start":
            self._current_thinking = {
                "type": "thinking",
                "thinking_id": event_data.get("thinking_id"),
                "start_time": timestamp,
            }
            self._thinking_chunks = []

        elif event_type == "reasoning_delta":
            self._thinking_chunks.append(event_data.get("content", ""))

        elif event_type == "reasoning_finish":
            if self._current_thinking:
                self._current_thinking["content"] = "".join(self._thinking_chunks)
                self._current_thinking["duration"] = timestamp - self._current_thinking.get("start_time", 0)
                self._current_thinking.pop("start_time", None)
                self.segments.append(self._current_thinking)
                self._current_thinking = None
                self._thinking_chunks = []

        elif event_type == "tool_call_start":
            self._current_tool_call = {
                "type": "tool_call",
                "tool": event_data.get("tool"),
                "input": event_data.get("input"),
                "start_time": timestamp,
            }

        elif event_type == "tool_call_finish":
            if self._current_tool_call:
                self._current_tool_call["output"] = event_data.get("output")
                self._current_tool_call["duration"] = timestamp - self._current_tool_call.get("start_time", 0)
                self._current_tool_call.pop("start_time", None)
                self.segments.append(self._current_tool_call)
                self._current_tool_call = None
            else:
                # 兼容缺失 tool_call_start 的情况，直接落一条完成记录
                self.segments.append({
                    "type": "tool_call",
                    "tool": event_data.get("tool"),
                    "input": event_data.get("input"),
                    "output": event_data.get("output"),
                    "status": "completed",
                })

        # content_info 事件（由 fetch_content_tool 通过 stream_writer 发送）
        # 只收集到 segments，不返回 extra_event（避免与主循环重复发送）
        elif event_type == "content_info":
            content_info = event_data.get("content_info")
            if content_info:
                self.segments.append({
                    "type": "content_info",
                    "data": content_info,
                })

        elif event_type == "text_delta":
            content = event_data.get("content", "")
            if content:
                self.assistant_chunks.append(content)

        # ========== 子步骤事件 ==========
        elif event_type == "sub_step_start":
            self._current_sub_step = {
                "type": "sub_step",
                "step_id": event_data.get("step_id"),
                "label": event_data.get("label"),
                "parent_tool": event_data.get("parent_tool"),
                "status": "running",
                "start_time": timestamp,
            }

        elif event_type == "sub_step_end":
            if self._current_sub_step and self._current_sub_step.get("step_id") == event_data.get("step_id"):
                self._current_sub_step.update({
                    "status": "completed",
                    "message": event_data.get("message"),
                    "duration": timestamp - self._current_sub_step.get("start_time", 0),
                })
                self._current_sub_step.pop("start_time", None)
                self.segments.append(self._current_sub_step)
                self._current_sub_step = None

        return extra_event

    def flush(self) -> None:
        """刷新未完成的内容（意图识别、思考和工具调用）"""
        # 刷新未完成的意图识别（标记为中断）
        if self._current_intent:
            self._current_intent["status"] = "interrupted"
            self._current_intent.pop("start_time", None)
            self.segments.append(self._current_intent)
            self._current_intent = None

        # 刷新未完成的思考内容
        if self._current_thinking:
            self._current_thinking["content"] = "".join(self._thinking_chunks)
            self.segments.append(self._current_thinking)
            self._current_thinking = None
            self._thinking_chunks = []

        # 刷新未完成的工具调用（标记为中断）
        if self._current_tool_call:
            self._current_tool_call["output"] = None
            self._current_tool_call["interrupted"] = True
            self._current_tool_call.pop("start_time", None)
            self.segments.append(self._current_tool_call)
            self._current_tool_call = None

        # 刷新未完成的子步骤（标记为中断）
        if self._current_sub_step:
            self._current_sub_step["status"] = "interrupted"
            self._current_sub_step.pop("start_time", None)
            self.segments.append(self._current_sub_step)
            self._current_sub_step = None

    def get_assistant_message(self) -> str:
        """获取完整的助手消息"""
        return "".join(self.assistant_chunks).strip()

    def finalize_segments(self) -> list[dict]:
        """
        完成收集，添加最终的 markdown segment 并返回完整列表

        Returns:
            完整的 segments 列表
        """
        self.flush()
        message = self.get_assistant_message()
        if message:
            self.segments.append({
                "type": "markdown",
                "content": message,
            })
        return self.segments


def format_sse_event(event_type: str, data: Any) -> dict:
    """
    格式化 SSE 事件

    Args:
        event_type: 事件类型
        data: 事件数据（会被 JSON 序列化）

    Returns:
        SSE 事件字典
    """
    return {
        "event": event_type,
        "data": json.dumps(data, ensure_ascii=False),
    }


def format_sse_done() -> dict:
    """
    生成 SSE 流结束信号（行业标准）

    符合 Vercel AI SDK 和 OpenAI 流式 API 的终止信号格式。

    Returns:
        SSE 终止事件字典
    """
    return {"data": "[DONE]"}


class SSEEventBuilder:
    """
    SSE 事件构建器，支持 id/retry 字段

    用于生成符合行业标准的 SSE 事件：
    - 每个事件自动递增 id，支持客户端断点续传
    - 首个事件包含 retry 字段，指导客户端重连间隔
    - 流结束时发送 [DONE] 终止信号

    Usage:
        builder = SSEEventBuilder(retry_ms=5000)
        yield builder.build_with_retry("intent_start", {"message": "..."})  # 首个事件
        yield builder.build("text_delta", {"content": "..."})  # 后续事件
        yield builder.build("done", {"session_id": "..."})  # 完成事件
        yield builder.build_done()  # 终止信号
    """

    def __init__(self, retry_ms: int = 5000):
        """
        初始化构建器

        Args:
            retry_ms: 客户端重连间隔（毫秒），默认 5000ms
        """
        self._event_id = 0
        self.retry_ms = retry_ms

    def build(self, event_type: str, data: Any, include_id: bool = True) -> dict:
        """
        构建带 id 的 SSE 事件

        Args:
            event_type: 事件类型
            data: 事件数据（会被 JSON 序列化）
            include_id: 是否包含 id 字段，默认 True

        Returns:
            SSE 事件字典
        """
        event = {
            "event": event_type,
            "data": json.dumps(data, ensure_ascii=False),
        }
        if include_id:
            self._event_id += 1
            event["id"] = str(self._event_id)
        return event

    def build_with_retry(self, event_type: str, data: Any) -> dict:
        """
        构建首个事件，包含 retry 字段

        客户端会根据 retry 字段决定断线后的重连间隔。

        Args:
            event_type: 事件类型
            data: 事件数据

        Returns:
            包含 retry 字段的 SSE 事件字典
        """
        event = self.build(event_type, data)
        event["retry"] = self.retry_ms
        return event

    def build_done(self) -> dict:
        """
        构建终止信号

        Returns:
            SSE 终止事件字典
        """
        return {"data": "[DONE]"}
