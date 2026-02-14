# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/utils/json_utils.py
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
JSON 解析工具 - 从 LLM 响应中提取 JSON

提供统一的 JSON 提取和修复功能，处理以下情况:
- 纯 JSON 响应
- 包含 ```json ... ``` 代码块的响应
- 包含 <think>...</think> 标签的响应
- JSON 被截断（缺少闭合括号）
"""
import json
import re
from typing import Optional


def try_repair_json(text: str) -> Optional[dict]:
    """
    尝试修复不完整的 JSON

    处理 LLM 响应被截断的情况:
    - 缺少闭合的 } 或 ]
    - 字符串没有闭合

    Args:
        text: 可能不完整的 JSON 文本

    Returns:
        修复后的字典，如果无法修复则返回 None
    """
    # 移除可能的 markdown 代码块标记
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())

    # 计算括号的平衡
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')

    # 尝试补全缺失的闭合符号
    repaired = text
    if open_braces > close_braces:
        # 可能有未闭合的字符串，先尝试截断到最后一个有效位置
        # 查找最后一个完整的字段
        last_comma = repaired.rfind(',')
        if last_comma > 0:
            # 尝试从最后一个逗号处截断
            candidate = repaired[:last_comma]
            missing_braces = candidate.count('{') - candidate.count('}')
            missing_brackets = candidate.count('[') - candidate.count(']')
            candidate += ']' * missing_brackets + '}' * missing_braces
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # 简单补全
        repaired += '}' * (open_braces - close_braces)

    if open_brackets > close_brackets:
        repaired += ']' * (open_brackets - close_brackets)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


def extract_json_from_text(text: str) -> dict:
    """
    从 LLM 响应中提取 JSON

    处理以下情况:
    - 纯 JSON 响应
    - 包含 ```json ... ``` 代码块的响应
    - 包含 <think>...</think> 标签的响应
    - 响应开头有空行或空白字符
    - 不完整的代码块（没有闭合 ```）
    - JSON 被截断（缺少闭合括号）

    Args:
        text: LLM 响应文本

    Returns:
        解析后的字典

    Raises:
        ValueError: 无法从响应中提取 JSON
    """
    # 移除 <think>...</think> 标签
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    # 移除开头的空白字符
    text = text.strip()

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试从 ```json ... ``` 代码块中提取（有闭合）
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            # 尝试修复
            repaired = try_repair_json(json_match.group(1))
            if repaired:
                return repaired

    # 尝试从 ```json ... 中提取（可能没有闭合 ```）
    json_open_match = re.search(r'```json\s*([\s\S]*)', text)
    if json_open_match:
        content = json_open_match.group(1).strip()
        # 移除末尾可能的不完整内容
        if content.endswith('```'):
            content = content[:-3].strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试修复
            repaired = try_repair_json(content)
            if repaired:
                return repaired

    # 尝试从 ``` ... ``` 代码块中提取
    code_match = re.search(r'```\s*([\s\S]*?)\s*```', text)
    if code_match:
        try:
            return json.loads(code_match.group(1).strip())
        except json.JSONDecodeError:
            repaired = try_repair_json(code_match.group(1))
            if repaired:
                return repaired

    # 尝试找到 JSON 对象（贪婪匹配最外层的花括号）
    json_obj_match = re.search(r'\{[\s\S]*\}', text)
    if json_obj_match:
        try:
            return json.loads(json_obj_match.group())
        except json.JSONDecodeError:
            repaired = try_repair_json(json_obj_match.group())
            if repaired:
                return repaired

    # 最后尝试：找到以 { 开头的内容并尝试修复
    brace_match = re.search(r'\{[\s\S]*', text)
    if brace_match:
        repaired = try_repair_json(brace_match.group())
        if repaired:
            return repaired

    raise ValueError(f"无法从响应中提取 JSON: {text[:200]}...")
