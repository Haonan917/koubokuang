# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/test_tools.py
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
共享的 LLM 测试工具定义

被 test_anthropic_llm.py 和 test_openai_llm.py 共同使用。
"""

import ast
import operator
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================================
# 安全的数学表达式求值器
# ============================================================================

# 支持的操作符映射
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval_node(node: ast.AST) -> Any:
    """递归求值 AST 节点"""
    if isinstance(node, ast.Constant):
        # Python 3.8+ 使用 ast.Constant
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"不支持的常量类型: {type(node.value).__name__}")
    elif isinstance(node, ast.Num):
        # Python 3.7 兼容
        return node.n
    elif isinstance(node, ast.BinOp):
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"不支持的操作符: {type(node.op).__name__}")
        return op_func(left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _safe_eval_node(node.operand)
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"不支持的操作符: {type(node.op).__name__}")
        return op_func(operand)
    elif isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)
    else:
        raise ValueError(f"不支持的表达式类型: {type(node).__name__}")


def safe_eval(expression: str) -> Any:
    """
    安全地计算数学表达式

    仅支持基本算术运算: +, -, *, /, //, %, **
    不允许函数调用、属性访问或任何其他操作。

    Args:
        expression: 数学表达式字符串

    Returns:
        计算结果

    Raises:
        ValueError: 表达式包含不支持的操作
        SyntaxError: 表达式语法错误
    """
    tree = ast.parse(expression, mode="eval")
    return _safe_eval_node(tree)


# ============================================================================
# 测试工具定义
# ============================================================================


@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气信息

    Args:
        city: 城市名称，如 "北京"、"上海"
    """
    weather_data = {
        "北京": "晴朗，温度 25°C，湿度 40%",
        "上海": "多云，温度 28°C，湿度 65%",
        "广州": "阵雨，温度 30°C，湿度 80%",
    }
    return weather_data.get(city, f"{city}天气数据暂无")


@tool
def calculate(expression: str) -> str:
    """计算数学表达式

    Args:
        expression: 数学表达式，如 "2 + 2"、"10 * 5"
    """
    try:
        result = safe_eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"


# ============================================================================
# 测试用 Schema 定义
# ============================================================================


class WeatherReport(BaseModel):
    """天气报告结构"""

    city: str = Field(description="城市名称")
    temperature: int = Field(description="温度（摄氏度）")
    condition: str = Field(description="天气状况，如晴、雨、多云")
    suggestion: str = Field(description="穿衣建议")
