# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/intent_classifier.py
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
意图识别模块

使用 LLM 分析用户输入，判断用户想要的学习模式。
在 Agent 主流程之前运行，为动态 System Prompt 提供 mode 参数。

实现说明：
- 直接调用 llm.ainvoke() 获取响应
- 使用 extract_json_from_text() 解析 JSON（已内置 <think> 标签移除）
- 支持关键词回退分类
"""

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from agent.prompts import INTENT_CLASSIFIER_SYSTEM
from llm_provider import get_llm
from utils.logger import logger
from utils.json_utils import extract_json_from_text


def _build_intent_classifier_prompt() -> str:
    """
    动态构建意图分类器的 System Prompt

    优先从数据库获取模式信息，失败时使用硬编码默认值。

    Returns:
        构建好的 System Prompt
    """
    keywords = _get_intent_keywords()

    # 构建模式描述
    mode_descriptions = []
    mode_info = {
        "summarize": ("精华提炼", "用户想快速了解要点、精简内容、提炼核心"),
        "analyze": ("深度拆解", "用户想深入学习、理解技巧、拆解方法论（默认模式）"),
        "template": ("模板学习", "用户想获取可复用模板、套路、框架"),
        "style_explore": ("风格探索", "用户想探索不同表达风格、换种说法"),
    }

    for idx, (mode_key, (label, desc)) in enumerate(mode_info.items(), start=1):
        mode_keywords = keywords.get(mode_key, {})
        zh_kw = ", ".join(mode_keywords.get("zh", []))
        en_kw = ", ".join(mode_keywords.get("en", []))
        keyword_str = f"关键词: {zh_kw}" if zh_kw else ""
        if en_kw:
            keyword_str += f" / {en_kw}" if keyword_str else f"Keywords: {en_kw}"

        mode_descriptions.append(f"{idx}. **{mode_key}** ({label}): {desc}\n   - {keyword_str}")

    modes_text = "\n\n".join(mode_descriptions)

    return f"""你是一个意图分类器。根据用户输入判断他们想要的学习模式。

## 可用模式

{modes_text}

## 输出要求

**严格输出以下 JSON 格式，不要包含任何其他内容：**

```json
{{"mode": "analyze", "confidence": 0.9, "reasoning": "用户只发了链接，没有明确意图"}}
```

如果意图不明确或只是发了链接，默认返回 analyze。"""


async def _build_intent_classifier_prompt_async() -> str:
    """
    异步构建意图分类器的 System Prompt（优先数据库）

    Returns:
        构建好的 System Prompt
    """
    try:
        from services.insight_mode_service import insight_mode_service
        modes = await insight_mode_service.list_all(active_only=True)
        if not modes:
            return _build_intent_classifier_prompt()

        # 构建模式描述（按 sort_order 排序）
        mode_descriptions = []
        for idx, mode in enumerate(modes, start=1):
            label = mode.label_zh or mode.label_en or mode.mode_key
            desc = (
                mode.description_zh
                or mode.description_en
                or "用户希望使用该模式进行学习/创作"
            )

            zh_kw = [k.strip() for k in (mode.keywords_zh or "").split(",") if k.strip()]
            en_kw = [k.strip() for k in (mode.keywords_en or "").split(",") if k.strip()]
            keyword_str = f"关键词: {', '.join(zh_kw)}" if zh_kw else ""
            if en_kw:
                keyword_str += f" / {', '.join(en_kw)}" if keyword_str else f"Keywords: {', '.join(en_kw)}"

            mode_descriptions.append(
                f"{idx}. **{mode.mode_key}** ({label}): {desc}\n   - {keyword_str}"
            )

        modes_text = "\n\n".join(mode_descriptions)

        return f"""你是一个意图分类器。根据用户输入判断他们想要的学习模式。

## 可用模式

{modes_text}

## 输出要求

**严格输出以下 JSON 格式，不要包含任何其他内容：**

```json
{{"mode": "analyze", "confidence": 0.9, "reasoning": "用户只发了链接，没有明确意图"}}
```

如果意图不明确或只是发了链接，默认返回 analyze。"""
    except Exception as e:
        logger.debug(f"Async prompt build failed, fallback to default: {e}")
        return _build_intent_classifier_prompt()


class IntentResult(BaseModel):
    """意图识别结果"""
    mode: str = Field(
        default="analyze",
        description="识别的模式: summarize/analyze/template/style_explore"
    )
    confidence: float = Field(
        default=0.8,
        description="置信度 0-1"
    )
    reasoning: str = Field(
        default="",
        description="识别理由"
    )


# 关键词缓存
_keywords_cache: dict = {}
_keywords_cache_timestamp: float = 0
_keywords_cache_ttl: float = 300  # 5 分钟缓存

# 硬编码回退关键词（当数据库不可用时使用）
_FALLBACK_KEYWORDS = {
    "summarize": {
        "zh": ["总结", "提炼", "精简", "要点", "核心", "概括", "快速了解"],
        "en": ["summarize", "summary", "key points", "extract", "brief"],
    },
    "analyze": {
        "zh": ["分析", "拆解", "学习", "为什么", "怎么做到的", "技巧", "方法论"],
        "en": ["analyze", "analysis", "learn", "why", "how", "technique", "method"],
    },
    "template": {
        "zh": ["模板", "套路", "框架", "结构", "公式", "仿写", "照着写"],
        "en": ["template", "pattern", "framework", "structure", "formula", "imitate"],
    },
    "style_explore": {
        "zh": ["风格", "换种说法", "不同角度", "改写", "变体", "多种版本"],
        "en": ["style", "rephrase", "different angle", "rewrite", "variation", "version"],
    },
}


def _get_intent_keywords() -> dict:
    """
    获取意图识别关键词（从数据库或回退到硬编码）

    Returns:
        {mode_key: {"zh": [...], "en": [...]}} 字典
    """
    import time
    global _keywords_cache, _keywords_cache_timestamp

    # 检查缓存是否有效
    current_time = time.time()
    cache_valid = (current_time - _keywords_cache_timestamp) < _keywords_cache_ttl

    if cache_valid and _keywords_cache:
        return _keywords_cache

    # 尝试从数据库加载（同步上下文）
    try:
        import asyncio
        from services.insight_mode_service import insight_mode_service

        try:
            asyncio.get_running_loop()
            # 在异步上下文中，不能用 asyncio.run()，使用缓存或默认值
            if cache_valid and _keywords_cache:
                return _keywords_cache
            return _FALLBACK_KEYWORDS
        except RuntimeError:
            pass

        keywords = asyncio.run(insight_mode_service.get_intent_keywords())
        if keywords:
            _keywords_cache = keywords
            _keywords_cache_timestamp = current_time
            return keywords

    except Exception as e:
        logger.warning(f"Failed to load keywords from database: {e}, using fallback")

    return _FALLBACK_KEYWORDS


async def _get_intent_keywords_async() -> dict:
    """
    异步获取意图识别关键词（优先数据库）

    Returns:
        {mode_key: {"zh": [...], "en": [...]}} 字典
    """
    import time
    global _keywords_cache, _keywords_cache_timestamp

    current_time = time.time()
    cache_valid = (current_time - _keywords_cache_timestamp) < _keywords_cache_ttl

    if cache_valid and _keywords_cache:
        return _keywords_cache

    try:
        from services.insight_mode_service import insight_mode_service
        keywords = await insight_mode_service.get_intent_keywords()
        if keywords:
            _keywords_cache = keywords
            _keywords_cache_timestamp = current_time
            return keywords
    except Exception as e:
        logger.warning(f"Failed to load keywords from database (async): {e}, using fallback")

    return _FALLBACK_KEYWORDS


def _fallback_classify(text: str) -> IntentResult:
    """
    关键词回退分类

    当 JSON 解析失败时，使用关键词匹配进行回退分类。
    优先从数据库获取关键词，失败时使用硬编码默认值。
    """
    text_lower = text.lower()
    keywords = _get_intent_keywords()

    # 按优先级检查各模式的关键词
    for mode_key in ["summarize", "template", "style_explore"]:
        mode_keywords = keywords.get(mode_key, {})
        zh_keywords = mode_keywords.get("zh", [])
        en_keywords = mode_keywords.get("en", [])

        # 检查中文关键词
        for kw in zh_keywords:
            if kw in text:
                return IntentResult(
                    mode=mode_key,
                    confidence=0.7,
                    reasoning=f"关键词匹配: {kw}"
                )

        # 检查英文关键词
        for kw in en_keywords:
            if kw in text_lower:
                return IntentResult(
                    mode=mode_key,
                    confidence=0.7,
                    reasoning=f"Keyword match: {kw}"
                )

    # 默认返回 analyze 模式
    return IntentResult(mode="analyze", confidence=0.6, reasoning="默认模式")


async def _fallback_classify_async(text: str) -> IntentResult:
    """
    异步关键词回退分类（支持数据库动态模式）
    """
    text_lower = text.lower()
    keywords = await _get_intent_keywords_async()

    # 按优先级检查各模式的关键词（优先排除 analyze）
    priority_modes = [m for m in keywords.keys() if m != "analyze"]
    for mode_key in priority_modes:
        mode_keywords = keywords.get(mode_key, {})
        zh_keywords = mode_keywords.get("zh", [])
        en_keywords = mode_keywords.get("en", [])

        for kw in zh_keywords:
            if kw in text:
                return IntentResult(
                    mode=mode_key,
                    confidence=0.7,
                    reasoning=f"关键词匹配: {kw}"
                )

        for kw in en_keywords:
            if kw in text_lower:
                return IntentResult(
                    mode=mode_key,
                    confidence=0.7,
                    reasoning=f"Keyword match: {kw}"
                )

    return IntentResult(mode="analyze", confidence=0.6, reasoning="默认模式")


async def classify_intent(user_input: str) -> IntentResult:
    """
    使用 LLM 识别用户意图

    Args:
        user_input: 用户输入文本（可能包含链接和自然语言指令）

    Returns:
        IntentResult: 包含 mode、confidence、reasoning 的识别结果
    """
    # 如果输入太短或只是链接，直接返回默认模式
    if not user_input or len(user_input.strip()) < 10:
        logger.info("Input too short, using default mode: analyze")
        return IntentResult(
            mode="analyze",
            confidence=1.0,
            reasoning="输入过短，使用默认模式"
        )

    response_content = ""
    try:
        # 获取 LLM（保持 thinking 模式开启，由 extract_json_from_text 处理）
        llm = get_llm(temperature=0)

        # 构建消息（使用动态构建的 prompt，失败时回退到静态 prompt）
        try:
            system_prompt = await _build_intent_classifier_prompt_async()
        except Exception:
            system_prompt = _build_intent_classifier_prompt()

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input),
        ]

        # 直接调用模型
        response = await llm.ainvoke(messages)
        response_content = response.content

        # 使用 extract_json_from_text 解析（已内置 <think> 标签移除）
        json_data = extract_json_from_text(response_content)
        result = IntentResult(**json_data)

        logger.info(
            f"Intent classified: mode={result.mode}, "
            f"confidence={result.confidence:.2f}, "
            f"reasoning={result.reasoning[:50]}..."
        )

        return result

    except ValueError as e:
        # JSON 解析失败，尝试关键词匹配
        logger.warning(f"JSON parsing failed: {e}, trying fallback classification")
        return await _fallback_classify_async(response_content)

    except Exception as e:
        logger.warning(f"Intent classification failed: {e}, using default mode")
        return IntentResult(
            mode="analyze",
            confidence=0.5,
            reasoning=f"分类失败，使用默认模式: {str(e)}"
        )


def classify_intent_sync(user_input: str) -> IntentResult:
    """
    同步版本的意图识别（用于非异步上下文）

    Args:
        user_input: 用户输入文本

    Returns:
        IntentResult: 识别结果
    """
    import asyncio
    return asyncio.run(classify_intent(user_input))


# 导出
__all__ = ["IntentResult", "classify_intent", "classify_intent_sync"]
