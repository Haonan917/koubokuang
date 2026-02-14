# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/stream/emitter.py
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
StreamEventEmitter - 流式事件发送器

统一事件格式，所有事件都包含 type, data, timestamp 三个字段。

事件类型命名遵循 Vercel AI SDK Data Stream Protocol 标准：
- reasoning_start / reasoning_delta / reasoning_finish - 思考过程
- text_delta - 内容流
- tool_call_start / tool_call_finish - 工具调用
"""

import time
from typing import Dict, Any, Optional


class StreamEventEmitter:
    """流式事件发送器

    统一事件格式，所有事件都包含 type, data, timestamp 三个字段。

    事件类型遵循 Vercel AI SDK 标准：
    - reasoning_* 代替 thinking_*
    - text_delta 代替 content_chunk
    - tool_call_finish 代替 tool_call_end
    """

    @staticmethod
    def emit(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        }

    def reasoning_start(self, thinking_id: int) -> Dict[str, Any]:
        """发送思考开始事件（原 thinking_start）"""
        return self.emit("reasoning_start", {"thinking_id": thinking_id})

    def reasoning_delta(self, content: str, thinking_id: int) -> Dict[str, Any]:
        """发送思考内容块（原 thinking_chunk）"""
        return self.emit("reasoning_delta", {"content": content, "thinking_id": thinking_id})

    def reasoning_finish(self, thinking_id: int) -> Dict[str, Any]:
        """发送思考结束事件（原 thinking_end）"""
        return self.emit("reasoning_finish", {"thinking_id": thinking_id})

    def text_delta(self, content: str, is_process_text: bool = False) -> Dict[str, Any]:
        """发送文本内容块（原 content_chunk）

        Args:
            content: 文本内容
            is_process_text: 是否是过程性文本（工具调用之间的文本）
        """
        return self.emit("text_delta", {
            "content": content,
            "is_process_text": is_process_text,
        })

    def tool_call_start(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        return self.emit("tool_call_start", {"tool": tool_name, "input": tool_input})

    def tool_call_finish(
        self,
        tool_name: str,
        output: Any,
        structured_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送工具调用完成事件（原 tool_call_end）"""
        return self.emit("tool_call_finish", {
            "tool": tool_name,
            "output": output,
            "structured_data": structured_data
        })

    def structured_data(
        self,
        success: bool,
        data_type: str,
        data: Any
    ) -> Dict[str, Any]:
        return self.emit("structured_data", {
            "success": success,
            "type": data_type,
            "data": data
        })

    def tool_progress(self, message: str, stage: str = "") -> Dict[str, Any]:
        return self.emit("tool_progress", {"message": message, "stage": stage})

    def sub_step_start(self, step_id: str, label: str, parent_tool: str) -> Dict[str, Any]:
        """子步骤开始事件

        用于工具内部的多阶段处理（如视频处理的下载、提取、转录等）
        """
        return self.emit("sub_step_start", {
            "step_id": step_id,
            "label": label,
            "parent_tool": parent_tool,
        })

    def sub_step_end(self, step_id: str, message: Optional[str] = None) -> Dict[str, Any]:
        """子步骤完成事件"""
        return self.emit("sub_step_end", {
            "step_id": step_id,
            "message": message,
        })

    def final_report_start(self) -> Dict[str, Any]:
        """发送最终报告开始事件

        标志着所有工具调用完成，Agent 开始输出最终分析报告。
        前端收到此事件后，后续的 text_delta 应显示在"AI Report"区域。
        """
        return self.emit("final_report_start", {})

    def done(self, session_id: str) -> Dict[str, Any]:
        return self.emit("done", {"session_id": session_id})

    def error(self, message: str) -> Dict[str, Any]:
        return self.emit("error", {"message": message})
