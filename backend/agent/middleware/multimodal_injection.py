# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/middleware/multimodal_injection.py
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
多模态消息注入中间件

当启用多模态且存在本地图片时，将图片嵌入到最后一条 HumanMessage 中。

基于 LangChain 1.0 的 @before_model 中间件模式实现。

工作原理:
1. 检查多模态是否启用 (is_multimodal_enabled())
2. 检查 state.content_info.local_image_paths 是否有图片
3. 如果条件满足，将图片 Base64 嵌入到最后一条 HumanMessage.content 中
"""

from typing import Optional, Dict, Any, List

from langchain.agents.middleware import before_model
from langchain_core.messages import HumanMessage, BaseMessage

from utils.logger import logger


def _find_last_human_message_index(messages: List[BaseMessage]) -> int:
    """
    找到最后一条 HumanMessage 的索引

    Args:
        messages: 消息列表

    Returns:
        索引，如果没有找到返回 -1
    """
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            return i
    return -1


def _inject_images_to_message(
    message: HumanMessage,
    image_paths: List[str],
    max_images: int = 5
) -> HumanMessage:
    """
    将图片注入到 HumanMessage 中

    Args:
        message: 原始 HumanMessage
        image_paths: 本地图片路径列表
        max_images: 最多注入的图片数

    Returns:
        包含图片的新 HumanMessage
    """
    from services.image_utils import build_multimodal_content

    # 获取原始文本内容
    original_content = message.content
    if isinstance(original_content, str):
        text = original_content
    elif isinstance(original_content, list):
        # 如果已经是列表，提取文本部分
        text_parts = [
            item.get("text", "") if isinstance(item, dict) and item.get("type") == "text"
            else str(item) if not isinstance(item, dict)
            else ""
            for item in original_content
        ]
        text = "\n".join(filter(None, text_parts))
    else:
        text = str(original_content)

    # 构建多模态内容
    multimodal_content = build_multimodal_content(text, image_paths, max_images)

    # 创建新的 HumanMessage
    return HumanMessage(content=multimodal_content)


def _get_image_paths_from_state(state: Dict[str, Any]) -> List[str]:
    """
    从 Agent 状态中获取本地图片路径

    Args:
        state: Agent 状态字典

    Returns:
        图片路径列表
    """
    content_info = state.get("content_info")
    if not content_info:
        return []

    return content_info.get("local_image_paths", [])


@before_model
def multimodal_injection_middleware(state: Dict[str, Any], runtime: Any) -> Optional[Dict[str, Any]]:
    """
    多模态消息注入中间件

    在模型调用前检查是否需要将图片嵌入到消息中。

    触发条件:
    1. 多模态已启用 (is_multimodal_enabled() 返回 True)
    2. state.content_info.local_image_paths 非空
    3. 存在 HumanMessage

    实现 LangChain 1.0 的 @before_model 中间件模式。

    Args:
        state: Agent 状态字典，包含 messages、content_info 等字段
        runtime: Runtime 对象，包含 context 等信息

    Returns:
        状态更新字典（包含修改后的 messages），或 None 表示无需更新
    """
    from llm_provider import is_multimodal_enabled
    from config import settings

    # 1. 检查多模态是否启用
    if not is_multimodal_enabled():
        return None

    # 2. 获取图片路径
    image_paths = _get_image_paths_from_state(state)
    if not image_paths:
        return None

    # 3. 获取消息列表
    messages = state.get("messages", [])
    if not messages:
        return None

    # 4. 找到最后一条 HumanMessage
    last_human_idx = _find_last_human_message_index(messages)
    if last_human_idx < 0:
        return None

    last_human_msg = messages[last_human_idx]

    # 5. 检查是否已经注入过图片（避免重复注入）
    # 如果 content 已经是列表且包含 image_url 类型，说明已注入
    if isinstance(last_human_msg.content, list):
        for item in last_human_msg.content:
            if isinstance(item, dict) and item.get("type") == "image_url":
                logger.debug("[MultimodalInjection] Images already injected, skipping")
                return None

    # 6. 注入图片
    max_images = getattr(settings, 'MULTIMODAL_MAX_IMAGES', 5)

    try:
        new_human_msg = _inject_images_to_message(
            last_human_msg,
            image_paths,
            max_images
        )

        # 7. 构建新的消息列表
        new_messages = list(messages)
        new_messages[last_human_idx] = new_human_msg

        logger.info(
            f"[MultimodalInjection] Injected {min(len(image_paths), max_images)} images "
            f"into message at index {last_human_idx}"
        )

        return {"messages": new_messages}

    except Exception as e:
        logger.warning(f"[MultimodalInjection] Failed to inject images: {e}")
        return None


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "multimodal_injection_middleware",
]
