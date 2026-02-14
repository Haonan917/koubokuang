# -*- coding: utf-8 -*-
"""TTS 标签智能生成（LLM 语义理解）"""

from __future__ import annotations

from typing import Optional, Sequence

from langchain_core.messages import HumanMessage, SystemMessage

from llm_provider import get_llm
from services.tts_tag_service import EMOTION_TAGS, TONE_TAGS, EFFECT_TAGS
from utils.json_utils import extract_json_from_text
from utils.logger import logger


TAGGING_SYSTEM_PROMPT = """你是专业的演讲稿语气/音效标注助手。

任务：在不改动原文的前提下，仅插入标签，让文本更适合演讲场景（具有煽动性、感染力、节奏感）。

硬性规则：
1. 只能插入标签，禁止改写/增删任何原文字符。
2. 情绪标签必须放在“每句话开头”，且句子里只能出现一次情绪标签。
3. 语气/音效/停顿标签可放在句中或句末，避免在句与句之间单独插入。
4. 只允许使用给定标签列表中的标签。
5. 在停顿类标签中，优先使用 (breath)，只有需要明显长停顿时才用 (long-break)。
6. 输出严格 JSON：{"tagged_text": "..."}，不要输出多余文字。
"""


def _format_tag_list(tags: Sequence[str]) -> str:
    return ", ".join(tags)


def _build_user_prompt(
    text: str,
    *,
    speech_style: str = "speech",
    preferred_tones: Optional[Sequence[str]] = None,
    preferred_effects: Optional[Sequence[str]] = None,
) -> str:
    style_hint = "演讲/号召/煽动" if speech_style == "speech" else speech_style or "自然表达"
    preferred_tones = [t for t in (preferred_tones or []) if t]
    preferred_effects = [t for t in (preferred_effects or []) if t]

    hint_lines = [
        f"风格目标：{style_hint}",
        f"可用情绪标签：{_format_tag_list(EMOTION_TAGS)}",
        f"可用语气标签：{_format_tag_list(TONE_TAGS)}",
        f"可用音效/停顿标签：{_format_tag_list(EFFECT_TAGS)}",
    ]
    if preferred_tones:
        hint_lines.append(f"语气偏好（尽量使用）：{_format_tag_list(preferred_tones)}")
    if preferred_effects:
        hint_lines.append(f"音效偏好（尽量使用）：{_format_tag_list(preferred_effects)}")

    hint_lines.append("原文如下（保持原样，仅插入标签）：")
    hint_lines.append(text)
    return "\n".join(hint_lines)


async def generate_tagged_text(
    text: str,
    *,
    speech_style: str = "speech",
    preferred_tones: Optional[Sequence[str]] = None,
    preferred_effects: Optional[Sequence[str]] = None,
) -> Optional[str]:
    if not text or not text.strip():
        return None

    try:
        llm = get_llm(temperature=0.25, enable_thinking=False)
        response = await llm.ainvoke([
            SystemMessage(content=TAGGING_SYSTEM_PROMPT),
            HumanMessage(content=_build_user_prompt(
                text.strip(),
                speech_style=speech_style,
                preferred_tones=preferred_tones,
                preferred_effects=preferred_effects,
            )),
        ])
        json_data = extract_json_from_text(response.content)
        tagged_text = (json_data.get("tagged_text") or "").strip()
        if not tagged_text:
            return None
        return tagged_text
    except Exception as e:
        logger.warning(f"[tts-llm] tagging failed: {e}")
        return None


__all__ = ["generate_tagged_text"]
