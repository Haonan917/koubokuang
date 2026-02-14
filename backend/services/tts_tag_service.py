# -*- coding: utf-8 -*-
"""Voicv TTS 标签规范化服务"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional


class TTSTagError(Exception):
    """TTS 标签不合法"""


BASIC_EMOTION_TAGS = (
    "(happy)",
    "(sad)",
    "(angry)",
    "(excited)",
    "(calm)",
    "(nervous)",
    "(confident)",
    "(surprised)",
    "(satisfied)",
    "(delighted)",
    "(scared)",
    "(worried)",
    "(upset)",
    "(frustrated)",
    "(depressed)",
    "(empathetic)",
    "(embarrassed)",
    "(disgusted)",
    "(moved)",
    "(proud)",
    "(relaxed)",
    "(grateful)",
    "(curious)",
    "(sarcastic)",
)

ADVANCED_EMOTION_TAGS = (
    "(disdainful)",
    "(unhappy)",
    "(anxious)",
    "(hysterical)",
    "(indifferent)",
    "(uncertain)",
    "(doubtful)",
    "(confused)",
    "(disappointed)",
    "(regretful)",
    "(guilty)",
    "(ashamed)",
    "(jealous)",
    "(envious)",
    "(hopeful)",
    "(optimistic)",
    "(pessimistic)",
    "(nostalgic)",
    "(lonely)",
    "(bored)",
    "(contemptuous)",
    "(sympathetic)",
    "(compassionate)",
    "(determined)",
    "(resigned)",
)

TONE_TAGS = (
    "(in a hurry tone)",
    "(shouting)",
    "(screaming)",
    "(whispering)",
    "(soft tone)",
)

EFFECT_TAGS = (
    "(laughing)",
    "(chuckling)",
    "(sobbing)",
    "(crying loudly)",
    "(sighing)",
    "(groaning)",
    "(panting)",
    "(snoring)",
    "(yawning)",
    "(gasping)",
    "(audience laughing)",
    "(background laughter)",
    "(crowd laughing)",
    "(laugh)",
    "(breath)",
    "(long-break)",
)

EMOTION_TAGS = BASIC_EMOTION_TAGS + ADVANCED_EMOTION_TAGS

_TAG_PATTERN = re.compile(r"\([^()]+\)")
_SPACE_PATTERN = re.compile(r"\s{2,}")

_EMOTION_LOOKUP = {tag.lower(): tag for tag in EMOTION_TAGS}
_TONE_LOOKUP = {tag.lower(): tag for tag in TONE_TAGS}
_EFFECT_LOOKUP = {tag.lower(): tag for tag in EFFECT_TAGS}
_EFFECT_ALIASES = {
    "(break)": "(breath)",
}


def _normalize_tag(raw_tag: str, lookup: dict) -> Optional[str]:
    if raw_tag is None:
        return None
    tag = str(raw_tag).strip().lower()
    if not tag:
        return None
    if not tag.startswith("("):
        tag = f"({tag}"
    if not tag.endswith(")"):
        tag = f"{tag})"
    return lookup.get(tag)


def normalize_emotion_tag(raw_tag: Optional[str]) -> Optional[str]:
    if raw_tag is None:
        return None
    normalized = _normalize_tag(raw_tag, _EMOTION_LOOKUP)
    if not normalized:
        raise TTSTagError(f"不支持的情绪标签: {raw_tag}")
    return normalized


def normalize_tone_tags(raw_tags: Optional[Iterable[str]]) -> List[str]:
    return _normalize_tag_list(raw_tags, _TONE_LOOKUP, "语气标签")


def _normalize_effect_tag(raw_tag: Optional[str]) -> Optional[str]:
    if raw_tag is None:
        return None
    tag = str(raw_tag).strip().lower()
    if not tag:
        return None
    if not tag.startswith("("):
        tag = f"({tag}"
    if not tag.endswith(")"):
        tag = f"{tag})"
    tag = _EFFECT_ALIASES.get(tag, tag)
    return _EFFECT_LOOKUP.get(tag)


def normalize_effect_tags(raw_tags: Optional[Iterable[str]]) -> List[str]:
    if raw_tags is None:
        return []
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]

    result: List[str] = []
    seen = set()
    for raw_tag in raw_tags:
        normalized = _normalize_effect_tag(raw_tag)
        if not normalized:
            raise TTSTagError(f"不支持的音效标签: {raw_tag}")
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _normalize_tag_list(raw_tags: Optional[Iterable[str]], lookup: dict, tag_type_name: str) -> List[str]:
    if raw_tags is None:
        return []
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]

    result: List[str] = []
    seen = set()
    for raw_tag in raw_tags:
        normalized = _normalize_tag(raw_tag, lookup)
        if not normalized:
            raise TTSTagError(f"不支持的{tag_type_name}: {raw_tag}")
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _find_first_emotion(text: str) -> Optional[str]:
    for match in _TAG_PATTERN.finditer(text):
        normalized = _normalize_tag(match.group(0), _EMOTION_LOOKUP)
        if normalized:
            return normalized
    return None


def _strip_emotion_tags(text: str) -> str:
    def replacer(match: re.Match) -> str:
        tag = match.group(0)
        return "" if _normalize_tag(tag, _EMOTION_LOOKUP) else tag

    without_emotion = _TAG_PATTERN.sub(replacer, text)
    return _SPACE_PATTERN.sub(" ", without_emotion).strip()


def normalize_tts_text(
    text: str,
    *,
    emotion: Optional[str] = None,
    tone_tags: Optional[Iterable[str]] = None,
    effect_tags: Optional[Iterable[str]] = None,
) -> dict:
    """
    规范化 Voicv TTS 输入文本。

    规则：
    - 情绪标签固定放在文本开头（若文本中存在情绪标签，会被前置）
    - 语气/音效标签允许任意位置；通过参数传入的标签会统一前置
    """
    stripped_text = (text or "").strip()
    if not stripped_text:
        raise TTSTagError("text 不能为空")

    normalized_emotion = normalize_emotion_tag(emotion) if emotion else None
    normalized_tones = normalize_tone_tags(tone_tags)
    normalized_effects = normalize_effect_tags(effect_tags)

    existing_emotion = _find_first_emotion(stripped_text)
    effective_emotion = normalized_emotion or existing_emotion
    body_text = _strip_emotion_tags(stripped_text)

    prefix_tags: List[str] = []
    if effective_emotion:
        prefix_tags.append(effective_emotion)
    prefix_tags.extend(normalized_tones)
    prefix_tags.extend(normalized_effects)

    result_parts: List[str] = []
    if prefix_tags:
        result_parts.append(" ".join(prefix_tags))
    if body_text:
        result_parts.append(body_text)

    normalized_text = " ".join(result_parts).strip()
    if not normalized_text:
        raise TTSTagError("text 不能为空")

    return {
        "text": normalized_text,
        "emotion": effective_emotion,
        "tone_tags": normalized_tones,
        "effect_tags": normalized_effects,
    }
