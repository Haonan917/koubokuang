# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/stream/processor.py
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
StreamEventProcessor - 流式事件处理器

处理 LangChain astream_events 产生的事件，转换为统一的流式输出格式。

重构后使用 ReasoningExtractor 统一处理多 Provider 的推理内容。
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Generator

from agent.stream.reasoning_extractor import ReasoningExtractor
from agent.stream.emitter import StreamEventEmitter
from i18n.translator import t

logger = logging.getLogger(__name__)


@dataclass
class ToolCallInfo:
    """工具调用信息"""
    name: str
    args_str: str = ""
    input: Dict[str, Any] = field(default_factory=dict)


class ToolCallTracker:
    """工具调用追踪器"""

    def __init__(self):
        self._calls: Dict[str, ToolCallInfo] = {}

    def register(self, tool_id: str, name: str, args: str = "") -> None:
        self._calls[tool_id] = ToolCallInfo(name=name, args_str=args)

    def register_with_input(self, run_id: str, name: str, tool_input: Dict[str, Any]) -> None:
        self._calls[run_id] = ToolCallInfo(name=name, input=tool_input)

    def append_args(self, tool_id: str, args: str) -> None:
        if tool_id in self._calls:
            self._calls[tool_id].args_str += args

    def get_name(self, tool_id: str, default: str = "unknown") -> str:
        if tool_id in self._calls:
            return self._calls[tool_id].name
        return default

    def remove(self, tool_id: str) -> Optional[ToolCallInfo]:
        return self._calls.pop(tool_id, None)

    def has(self, tool_id: str) -> bool:
        return tool_id in self._calls


class StreamEventProcessor:
    """流式事件处理器

    处理 LangChain astream_events 产生的事件，转换为统一的流式输出格式。

    使用 ReasoningExtractor 统一处理多 Provider 的推理内容：
    - Anthropic Claude: content_blocks (type="thinking")
    - OpenAI GPT-5: content_blocks (type="reasoning")
    - DeepSeek: additional_kwargs.reasoning_content
    - MiniMax: <think> 标签
    """

    def __init__(self):
        self.emitter = StreamEventEmitter()
        self.extractor = ReasoningExtractor()
        self.tool_tracker = ToolCallTracker()

        # reasoning 状态（集中管理）
        self._reasoning_active = False
        self._reasoning_id = 0

        # 工具调用状态追踪（用于区分过程性文本和最终报告）
        self._tools_ever_called = False  # 是否调用过任何工具
        self._pending_tool_count = 0      # 当前待完成的工具调用数量
        self._final_report_started = False  # 是否已发送 final_report_start

    def reset(self):
        """重置处理器状态，用于连接断开时的清理

        避免跨请求的状态泄漏。
        """
        self._reasoning_active = False
        self._reasoning_id = 0
        self._tools_ever_called = False
        self._pending_tool_count = 0
        self._final_report_started = False
        self.tool_tracker = ToolCallTracker()
        self.extractor.reset()  # ReasoningExtractor 已有 reset 方法

    def process_event(self, event: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """处理单个 LangChain astream_events 事件"""
        kind = event.get("event")
        # 记录所有事件类型（用于调试 stream_writer）
        if kind and kind not in ("on_chat_model_stream", "on_llm_stream"):
            logger.info(f"[StreamEventProcessor] Processing event: {kind}, name={event.get('name', 'N/A')}")

        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk:
                yield from self.process_chat_model_stream(chunk)

        elif kind == "on_llm_stream":
            # 处理原始 token 流（某些 provider 会通过此事件发送内容）
            yield from self.process_llm_stream(event)

        elif kind == "on_tool_start":
            yield self.process_tool_start(event)

        elif kind == "on_tool_end":
            yield from self.process_tool_end(event)

        elif kind == "on_custom_event":
            result = self.process_custom_event(event)
            if result:
                yield result

    def process_chat_model_stream(self, chunk: Any) -> Generator[Dict[str, Any], None, None]:
        """处理 on_chat_model_stream 事件

        使用 ReasoningExtractor 统一提取 reasoning 和 text 内容。
        """
        if chunk is None:
            return

        # 使用统一提取器
        result = self.extractor.extract(chunk)

        # reasoning 开始事件
        # 只有当有实际内容时才发送 start 事件，避免创建空的 thinking segment
        if result.reasoning_content:
            if not self._reasoning_active:
                self._reasoning_active = True
                self._reasoning_id += 1
                yield self.emitter.reasoning_start(self._reasoning_id)
            yield self.emitter.reasoning_delta(result.reasoning_content, self._reasoning_id)
        # 如果只有 is_reasoning_start=True 但没有内容，等待下一个 chunk
        # 不要发送空的 reasoning_start 事件

        # reasoning 结束事件
        if result.is_reasoning_end:
            yield from self._end_reasoning_if_active()

        # text content 处理
        if result.text_content:
            yield from self._end_reasoning_if_active()
            # 判断是否是过程性文本
            # - 如果没有调用过工具，文本直接作为最终报告
            # - 如果调用过工具但最终报告未开始，是过程性文本
            # - 如果最终报告已开始，是最终报告
            if not self._tools_ever_called:
                is_process_text = False  # 无工具调用，直接是最终报告
            else:
                is_process_text = not self._final_report_started
            yield self.emitter.text_delta(result.text_content, is_process_text=is_process_text)

        # tool call 处理
        yield from self._process_tool_call_chunks(chunk)

    def _end_reasoning_if_active(self) -> Generator[Dict[str, Any], None, None]:
        """结束 reasoning（如果正在进行中）

        集中管理 reasoning 状态，避免分散的 end_if_started 调用。
        """
        if self._reasoning_active:
            self._reasoning_active = False
            yield self.emitter.reasoning_finish(self._reasoning_id)

    def _process_tool_call_chunks(self, chunk: Any) -> Generator[Dict[str, Any], None, None]:
        tool_call_chunks = getattr(chunk, "tool_call_chunks", [])

        for tc_chunk in tool_call_chunks:
            tool_id = tc_chunk.get("id")
            tool_name = tc_chunk.get("name")
            tool_args = tc_chunk.get("args", "")

            if tool_id and tool_name:
                yield from self._end_reasoning_if_active()
                self.tool_tracker.register(tool_id, tool_name, tool_args or "")
            elif tool_id and self.tool_tracker.has(tool_id):
                self.tool_tracker.append_args(tool_id, tool_args or "")

    def process_llm_stream(self, event: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """处理 on_llm_stream 事件（token 级别流）

        某些 LLM provider 会通过此事件发送 token 流，
        特别是在混合思考和内容输出的场景中。
        """
        data = event.get("data", {})
        chunk = data.get("chunk", "")

        if not chunk or not isinstance(chunk, str):
            return

        logger.debug(f"LLM stream chunk: {chunk[:50]}...")

        # 根据当前 extractor 状态判断是思考还是内容
        # 只有当有实际内容时才发送 reasoning 事件
        if self.extractor.is_in_reasoning and chunk:
            if not self._reasoning_active:
                self._reasoning_active = True
                self._reasoning_id += 1
                yield self.emitter.reasoning_start(self._reasoning_id)
            yield self.emitter.reasoning_delta(chunk, self._reasoning_id)
        else:
            # 结束思考（如果在进行中）
            yield from self._end_reasoning_if_active()
            yield self.emitter.text_delta(chunk)

    def process_tool_start(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """处理 on_tool_start 事件"""
        tool_name = event.get("name", "")
        tool_input = event.get("data", {}).get("input", {})
        run_id = event.get("run_id", "")

        # 追踪工具调用状态
        self._tools_ever_called = True
        self._pending_tool_count += 1

        self.tool_tracker.register_with_input(run_id, tool_name, tool_input)
        return self.emitter.tool_call_start(tool_name, tool_input)

    def process_tool_end(self, event: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """处理 on_tool_end 事件"""
        # 减少待完成的工具调用计数
        self._pending_tool_count = max(0, self._pending_tool_count - 1)

        tool_name = event.get("name", "unknown")
        run_id = event.get("run_id", "")
        output = event.get("data", {}).get("output", "")

        tool_result = self._extract_tool_result(output)

        tool_name = self.tool_tracker.get_name(run_id, tool_name)
        self.tool_tracker.remove(run_id)

        structured_data = self._parse_structured_data(tool_result)

        yield self.emitter.tool_call_finish(tool_name, tool_result, structured_data)

        if structured_data and structured_data.get("success"):
            yield self.emitter.structured_data(
                success=structured_data.get("success"),
                data_type=structured_data.get("type", ""),
                data=structured_data.get("data")
            )

        # 关键：当所有工具完成时，发送 final_report_start
        if self._tools_ever_called and self._pending_tool_count == 0 and not self._final_report_started:
            self._final_report_started = True
            yield self.emitter.final_report_start()

    def process_custom_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理 on_custom_event 事件（工具进度、子步骤等）

        支持两种事件格式:
        1. adispatch_custom_event(name, data): event["name"] 是事件类型
        2. stream_writer({"type": ...}): event["data"]["type"] 是事件类型
        """
        logger.info(f"[StreamEventProcessor] Received on_custom_event: {event}")
        custom_data = event.get("data", {})
        # adispatch_custom_event 的事件类型在 event["name"] 中
        event_name = event.get("name", "")
        logger.info(f"[StreamEventProcessor] event_name: {event_name}, custom_data: {custom_data}")

        # 处理 adispatch_custom_event 格式的事件
        if event_name == "sub_step_start":
            return self.emitter.sub_step_start(
                step_id=custom_data.get("step_id", ""),
                label=custom_data.get("label", ""),
                parent_tool=custom_data.get("parent_tool", ""),
            )
        elif event_name == "sub_step_end":
            return self.emitter.sub_step_end(
                step_id=custom_data.get("step_id", ""),
                message=custom_data.get("message"),
            )
        elif event_name == "content_info":
            # 处理 content_info 事件（视频卡片数据）- adispatch_custom_event 格式
            content_info = custom_data.get("content_info")
            if content_info:
                return self.emitter.emit("content_info", {"content_info": content_info})
            return None
        elif event_name == "transcript":
            # 处理 transcript 事件（视频转录数据）- adispatch_custom_event 格式
            transcript = custom_data.get("transcript")
            if transcript:
                return self.emitter.emit("transcript", transcript)
            return None

        if isinstance(custom_data, dict):
            # 兼容旧格式: stream_writer({"type": ...})
            event_type = custom_data.get("type", "")

            # 处理子步骤事件 (旧格式)
            if event_type == "sub_step_start":
                return self.emitter.sub_step_start(
                    step_id=custom_data.get("step_id", ""),
                    label=custom_data.get("label", ""),
                    parent_tool=custom_data.get("parent_tool", ""),
                )
            elif event_type == "sub_step_end":
                return self.emitter.sub_step_end(
                    step_id=custom_data.get("step_id", ""),
                    message=custom_data.get("message"),
                )
            # 处理 content_info 事件（视频卡片数据）
            elif event_type == "content_info":
                content_info = custom_data.get("content_info")
                if content_info:
                    return self.emitter.emit("content_info", {"content_info": content_info})
                return None

            # 检查是否是 progress 事件
            stage = custom_data.get("stage", "")
            message = custom_data.get("message", "")
            if stage or message:
                return self.emitter.tool_progress(message, stage)

            # 其他自定义事件
            if event_type:
                return self.emitter.emit(event_type, custom_data)
            return self.emitter.emit("tool_progress", custom_data)
        else:
            return self.emitter.tool_progress(str(custom_data))

    def flush(self) -> Generator[Dict[str, Any], None, None]:
        """流结束时刷新缓冲区"""
        final_result = self.extractor.flush()

        if final_result.reasoning_content:
            if not self._reasoning_active:
                self._reasoning_active = True
                self._reasoning_id += 1
                yield self.emitter.reasoning_start(self._reasoning_id)
            yield self.emitter.reasoning_delta(final_result.reasoning_content, self._reasoning_id)

        if final_result.text_content:
            yield from self._end_reasoning_if_active()
            yield self.emitter.text_delta(final_result.text_content)

        # 确保 reasoning 状态结束
        yield from self._end_reasoning_if_active()

    def finalize(self, session_id: str) -> Dict[str, Any]:
        """生成完成信号"""
        if self.extractor.detected_source:
            logger.info(f"Detected reasoning source: {self.extractor.detected_source}")

        logger.info("Agent stream completed")
        return self.emitter.done(session_id)

    def create_error(self, error: Exception) -> Dict[str, Any]:
        """创建错误事件"""
        logger.exception(f"Error in process_chat_stream: {error}")
        return self.emitter.error(t("errors.serviceUnavailable", error=str(error)))

    @staticmethod
    def _extract_tool_result(output: Any) -> Any:
        """从工具输出中提取可序列化的结果

        处理不同类型的工具输出：
        - Command: 提取 update 中的 messages 或其他字段
        - ToolMessage: 提取 content
        - 其他: 直接返回
        """
        if output is None:
            return ""

        # 处理 Command 对象（LangGraph 工具返回）
        # Command 有 update 和 goto 属性
        if hasattr(output, "update") and hasattr(output, "goto"):
            update_dict = output.update or {}
            messages = update_dict.get("messages", [])

            if messages:
                # 提取第一条消息的内容
                first_msg = messages[0]
                if hasattr(first_msg, "content"):
                    return first_msg.content
                return str(first_msg)
            else:
                # 无消息，提取其他有意义的字段
                result_fields = {k: v for k, v in update_dict.items() if k not in ("messages", "current_stage")}
                if result_fields:
                    return result_fields
                return update_dict.get("current_stage", "完成")

        # 处理 ToolMessage 或其他有 content 属性的对象
        if hasattr(output, "content"):
            return output.content

        # 字符串或其他可序列化类型直接返回
        if isinstance(output, (str, int, float, bool, dict, list)):
            return output

        # 其他情况转为字符串
        return str(output)

    @staticmethod
    def _parse_structured_data(tool_result: Any) -> Optional[Dict[str, Any]]:
        """解析工具返回的结构化数据"""
        if not tool_result:
            return None

        if isinstance(tool_result, dict):
            return tool_result if "type" in tool_result else None

        if isinstance(tool_result, str):
            try:
                parsed = json.loads(tool_result)
                if isinstance(parsed, dict) and "type" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass

        return None
