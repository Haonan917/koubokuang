# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/db/utils.py
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
数据库工具函数

提供异步/同步转换等通用工具。
"""

import asyncio
from typing import Coroutine, TypeVar

import nest_asyncio

# nest_asyncio 用于解决 "event loop already running" 问题
# 注意：延迟到 run_sync() 中按需 apply，避免与 uvloop 冲突
_nest_asyncio_applied = False

T = TypeVar("T")


def run_sync(coro: Coroutine[None, None, T]) -> T:
    """
    安全运行协程的同步包装

    使用 nest_asyncio 允许在已运行的事件循环中嵌套执行。
    这解决了 "RuntimeError: This event loop is already running" 问题。

    Args:
        coro: 要执行的协程

    Returns:
        协程的返回值

    Raises:
        RuntimeError: 当在不支持嵌套执行的事件循环（如 uvloop）中调用时
    """
    global _nest_asyncio_applied
    try:
        loop = asyncio.get_running_loop()
        # 已经在事件循环中，需要 nest_asyncio 允许嵌套执行
        if not _nest_asyncio_applied:
            try:
                nest_asyncio.apply()
                _nest_asyncio_applied = True
            except ValueError as e:
                # uvloop 不支持 nest_asyncio
                raise RuntimeError(
                    "在已运行的事件循环中调用 run_sync，"
                    "但当前事件循环不支持嵌套执行（如 uvloop）。"
                    "请使用异步方法代替。"
                ) from e
        return loop.run_until_complete(coro)
    except RuntimeError as e:
        # 检查是否是 "no running event loop" 错误
        if "no running event loop" in str(e).lower() or "no current event loop" in str(e).lower():
            # 没有运行中的事件循环，使用 asyncio.run()
            return asyncio.run(coro)
        # 其他 RuntimeError 继续抛出
        raise
