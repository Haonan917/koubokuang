# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/stream/think_tag_fsm.py
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
ThinkTagFSM - <think> 标签状态机解析器

使用有限状态机（FSM）进行单遍扫描 O(n)，替代原来 parser.py 中复杂的 14 种部分标签检测。

支持解析 MiniMax M2.x 等模型输出的 <think>...</think> 标签格式。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class FSMState(Enum):
    """状态机状态"""
    NORMAL = "normal"        # 普通文本
    IN_TAG = "in_tag"        # 正在读取标签名（遇到 '<' 后）
    IN_THINK = "in_think"    # 在 <think> 块内


@dataclass
class FSMResult:
    """状态机单次处理结果"""
    reasoning_content: str = ""
    text_content: str = ""
    is_reasoning_start: bool = False
    is_reasoning_end: bool = False


class ThinkTagFSM:
    """<think> 标签状态机解析器

    单遍扫描 O(n)，自动处理流式切分的部分标签。

    使用方式：
    ```python
    fsm = ThinkTagFSM()

    # 处理流式 chunk
    for chunk in stream:
        result = fsm.process(chunk)
        if result.reasoning_content:
            yield reasoning_event(result.reasoning_content)
        if result.text_content:
            yield text_event(result.text_content)

    # 流结束时刷新缓冲区
    final = fsm.flush()
    ```
    """

    THINK_START = "<think>"
    THINK_END = "</think>"

    def __init__(self):
        self._state = FSMState.NORMAL
        self._buffer = ""
        self._tag_buffer = ""  # 正在读取的标签名

    def reset(self) -> None:
        """重置状态机"""
        self._state = FSMState.NORMAL
        self._buffer = ""
        self._tag_buffer = ""

    @property
    def is_in_thinking(self) -> bool:
        """是否在 <think> 块内"""
        return self._state == FSMState.IN_THINK

    @property
    def has_pending_state(self) -> bool:
        """是否有待处理状态（正在读取标签或在思考块内）

        用于判断是否需要继续调用 FSM 处理后续 chunk。
        当标签被分割时（如 '<thi' + 'nk>'），第一个 chunk 会使 FSM
        进入 IN_TAG 状态，此时需要继续处理后续 chunk。
        """
        # 额外包含 _buffer：避免 '<think>...</think>' 后不足 50 字符的文本
        # 被留在缓冲区直到流结束才 flush，导致文本顺序错位。
        return self._state != FSMState.NORMAL or bool(self._tag_buffer) or bool(self._buffer)

    def process(self, text: str) -> FSMResult:
        """处理输入文本

        Args:
            text: 输入文本（可能是完整的或流式切分的部分）

        Returns:
            FSMResult: 包含解析出的 reasoning/text 内容和状态标志
        """
        result = FSMResult()

        for char in text:
            if self._state == FSMState.NORMAL:
                self._process_normal(char, result)
            elif self._state == FSMState.IN_TAG:
                self._process_in_tag(char, result)
            elif self._state == FSMState.IN_THINK:
                self._process_in_think(char, result)

        return result

    def _process_normal(self, char: str, result: FSMResult) -> None:
        """处理 NORMAL 状态"""
        if char == "<":
            # 可能是标签开始
            self._state = FSMState.IN_TAG
            self._tag_buffer = "<"
        else:
            # 普通文本
            self._buffer += char
            # 适时刷新文本缓冲区
            if len(self._buffer) >= 50:
                result.text_content += self._buffer
                self._buffer = ""

    def _process_in_tag(self, char: str, result: FSMResult) -> None:
        """处理 IN_TAG 状态（正在读取标签）"""
        self._tag_buffer += char

        if char == ">":
            # 标签结束
            tag = self._tag_buffer.lower()
            if tag == self.THINK_START:
                # <think> 开始
                # 先输出之前的文本缓冲
                if self._buffer:
                    result.text_content += self._buffer
                    self._buffer = ""
                self._state = FSMState.IN_THINK
                result.is_reasoning_start = True
            elif tag == self.THINK_END:
                # 意外的 </think>（不在 IN_THINK 状态）
                # 当作普通文本处理
                self._buffer += self._tag_buffer
                self._state = FSMState.NORMAL
            else:
                # 其他标签，当作普通文本
                self._buffer += self._tag_buffer
                self._state = FSMState.NORMAL
            self._tag_buffer = ""
        elif len(self._tag_buffer) > 10:
            # 标签太长，不是有效标签
            self._buffer += self._tag_buffer
            self._tag_buffer = ""
            self._state = FSMState.NORMAL

    def _process_in_think(self, char: str, result: FSMResult) -> None:
        """处理 IN_THINK 状态（在 <think> 块内）"""
        if char == "<":
            # 可能是 </think> 开始
            self._tag_buffer = "<"
        elif self._tag_buffer:
            # 继续读取标签
            self._tag_buffer += char
            if char == ">":
                tag = self._tag_buffer.lower()
                if tag == self.THINK_END:
                    # </think> 结束
                    # 输出 reasoning 缓冲
                    if self._buffer:
                        result.reasoning_content += self._buffer
                        self._buffer = ""
                    self._state = FSMState.NORMAL
                    result.is_reasoning_end = True
                else:
                    # 其他标签，当作 reasoning 内容
                    self._buffer += self._tag_buffer
                self._tag_buffer = ""
            elif len(self._tag_buffer) > 10:
                # 标签太长，不是有效标签
                self._buffer += self._tag_buffer
                self._tag_buffer = ""
        else:
            # 普通 reasoning 内容
            self._buffer += char
            # 适时刷新 reasoning 缓冲区
            if len(self._buffer) >= 50:
                result.reasoning_content += self._buffer
                self._buffer = ""

    def flush(self) -> FSMResult:
        """刷新缓冲区（流结束时调用）

        Returns:
            FSMResult: 包含剩余的 reasoning/text 内容
        """
        result = FSMResult()

        # 处理未完成的标签
        remaining = self._tag_buffer + self._buffer

        if remaining:
            if self._state == FSMState.IN_THINK:
                result.reasoning_content = remaining
                result.is_reasoning_end = True
            else:
                result.text_content = remaining

        # 重置状态
        self._buffer = ""
        self._tag_buffer = ""
        if self._state == FSMState.IN_THINK:
            self._state = FSMState.NORMAL

        return result
