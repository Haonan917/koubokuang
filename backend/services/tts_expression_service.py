# -*- coding: utf-8 -*-
"""TTS 文本情绪识别与表达标签增强"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence

from services.tts_tag_service import (
    TTSTagError,
    normalize_effect_tags,
    normalize_emotion_tag,
    normalize_tone_tags,
    normalize_tts_text,
)
from services.tts_llm_tag_service import generate_tagged_text

_SENTENCE_PATTERN = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?")
_CLAUSE_PATTERN = re.compile(r"[^，,、；;：:\n]+[，,、；;：:]?")
_TAG_PATTERN = re.compile(r"\([^()]+\)")
_SPACE_PATTERN = re.compile(r"\s{2,}")

_INLINE_EFFECT_TAGS = {
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
    "(long-break)",
    "(breath)",  # 兼容历史模板
    "(laugh)",   # 兼容历史模板
}
_INLINE_TONE_TAGS = {
    "(soft tone)",
    "(whispering)",
    "(screaming)",
    "(shouting)",
    "(in a hurry tone)",
}
_AUTO_EFFECT_TAGS = {
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
    "(breath)",
}

_EFFECT_HINTS = [
    ("(laughing)", ("哈哈", "笑死", "太好笑", "laughing")),
    ("(chuckling)", ("呵呵", "偷笑", "轻笑", "chuckling")),
    ("(crying loudly)", ("痛哭", "大哭", "嚎啕", "崩溃大哭", "crying loudly")),
    ("(sobbing)", ("抽泣", "哽咽", "啜泣", "泪目", "sobbing")),
    ("(gasping)", ("倒吸", "震惊", "天哪", "竟然", "不可思议", "gasping")),
    ("(sighing)", ("唉", "叹气", "无奈", "可惜", "sighing")),
    ("(groaning)", ("哎哟", "头疼", "难受", "烦死", "呻吟", "groaning")),
    ("(panting)", ("气喘", "喘不过气", "上气不接下气", "跑得", "panting")),
    ("(snoring)", ("打呼", "鼾", "呼噜", "snoring")),
    ("(yawning)", ("哈欠", "困死", "太困", "yawning")),
    ("(laugh)", ("哈哈", "笑死", "好笑", "laugh")),
]

_TONE_HINTS = [
    ("(screaming)", ("尖叫", "啊啊啊", "失声", "screaming")),
    ("(shouting)", ("大喊", "吼", "喊道", "高声", "shouting")),
    ("(whispering)", ("悄悄", "小声", "低声", "耳语", "whispering")),
    ("(soft tone)", ("温柔", "轻声", "柔和", "安抚", "soft tone")),
    ("(in a hurry tone)", ("赶紧", "快点", "马上", "立刻", "来不及", "in a hurry")),
]

_TSK_HINTS = ("啧", "离谱", "无语", "嫌弃", "不屑", "阴阳")


def _dedupe(items: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def split_sentences(text: str) -> List[str]:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    result: List[str] = []
    for line in normalized.split("\n"):
        line = line.strip()
        if not line:
            continue
        chunks = [m.group(0).strip() for m in _SENTENCE_PATTERN.finditer(line) if m.group(0).strip()]
        if chunks:
            result.extend(chunks)
        else:
            result.append(line)
    return result


def _extract_emotion_from_text(text: str) -> Optional[str]:
    for match in _TAG_PATTERN.finditer(text or ""):
        raw_tag = match.group(0)
        try:
            return normalize_emotion_tag(raw_tag)
        except TTSTagError:
            continue
    return None


def _strip_tags(text: str) -> str:
    return _TAG_PATTERN.sub("", text or "")


def _normalize_plain_text(text: str) -> str:
    stripped = _strip_tags(text)
    return re.sub(r"\s+", "", stripped or "")


def _normalize_any_tag(raw_tag: str) -> Optional[str]:
    try:
        return normalize_emotion_tag(raw_tag)
    except TTSTagError:
        pass
    try:
        return normalize_tone_tags([raw_tag])[0]
    except TTSTagError:
        pass
    try:
        return normalize_effect_tags([raw_tag])[0]
    except TTSTagError:
        return None


def _sanitize_tagged_text(text: str) -> str:
    def replacer(match: re.Match) -> str:
        raw = match.group(0)
        normalized = _normalize_any_tag(raw)
        return normalized or ""

    sanitized = _TAG_PATTERN.sub(replacer, text or "")
    sanitized = _SPACE_PATTERN.sub(" ", sanitized).strip()
    return _ensure_emotion_prefix(sanitized)


def _ensure_emotion_prefix(text: str) -> str:
    sentences = split_sentences(text or "")
    if not sentences:
        return (text or "").strip()

    rendered: List[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        emotions: List[str] = []

        def strip_emotions(match: re.Match) -> str:
            raw = match.group(0)
            try:
                emotions.append(normalize_emotion_tag(raw))
                return ""
            except TTSTagError:
                return raw

        cleaned = _TAG_PATTERN.sub(strip_emotions, sentence)
        cleaned = _SPACE_PATTERN.sub(" ", cleaned).strip()
        if emotions:
            rendered.append(f"{emotions[0]} {cleaned}".strip())
        else:
            rendered.append(cleaned)

    return " ".join(rendered).strip()


def _extract_inline_tags(text: str) -> Dict[str, List[str]]:
    emotions: List[str] = []
    tones: List[str] = []
    effects: List[str] = []
    for match in _TAG_PATTERN.finditer(text or ""):
        raw = match.group(0)
        try:
            emotions.append(normalize_emotion_tag(raw))
            continue
        except TTSTagError:
            pass
        try:
            tones.append(normalize_tone_tags([raw])[0])
            continue
        except TTSTagError:
            pass
        try:
            effects.append(normalize_effect_tags([raw])[0])
        except TTSTagError:
            continue
    return {
        "emotions": _dedupe(emotions),
        "tones": _dedupe(tones),
        "effects": _dedupe(effects),
    }


def _visible_text_len(text: str) -> int:
    stripped = _strip_tags(text)
    stripped = re.sub(r"\s+", "", stripped)
    return len(stripped)


def _has_inline_effect_tag(text: str) -> bool:
    lowered = (text or "").lower()
    for tag in _INLINE_EFFECT_TAGS:
        if tag in lowered:
            return True
    return False


def _has_inline_tone_tag(text: str) -> bool:
    lowered = (text or "").lower()
    for tag in _INLINE_TONE_TAGS:
        if tag in lowered:
            return True
    return False


def _split_clauses(text: str) -> List[str]:
    chunks = [m.group(0) for m in _CLAUSE_PATTERN.finditer(text or "") if m.group(0).strip()]
    return chunks if chunks else [text or ""]


def _contains_hint(text: str, hints: Iterable[str]) -> bool:
    lowered = (text or "").lower()
    return any(hint in text or hint in lowered for hint in hints)


def _detect_semantic_tag(text: str, *, allowed_tags: set[str], tag_hints: List[tuple[str, tuple[str, ...]]]) -> Optional[str]:
    for tag, hints in tag_hints:
        if tag not in allowed_tags:
            continue
        if _contains_hint(text, hints):
            return tag
    return None


def _detect_tone_tag(text: str, *, allowed_tags: set[str]) -> Optional[str]:
    tone_tag = _detect_semantic_tag(text, allowed_tags=allowed_tags, tag_hints=_TONE_HINTS)
    if tone_tag:
        return tone_tag

    exclamations = text.count("!") + text.count("！")
    if exclamations >= 2 and "(screaming)" in allowed_tags:
        return "(screaming)"
    if exclamations >= 1 and "(shouting)" in allowed_tags:
        return "(shouting)"
    return None


def _detect_effect_tag(text: str, *, allowed_tags: set[str]) -> Optional[str]:
    effect_tag = _detect_semantic_tag(text, allowed_tags=allowed_tags, tag_hints=_EFFECT_HINTS)
    if effect_tag:
        return effect_tag

    if _contains_hint(text, _TSK_HINTS):
        if "(groaning)" in allowed_tags:
            return "(groaning)"
        if "(breath)" in allowed_tags:
            return "(breath)"
    return None


def _inject_intra_sentence_expressions(
    sentence: str,
    *,
    auto_breaks: bool,
    inline_effect_tags: Optional[Iterable[str]] = None,
    inline_tone_tags: Optional[Iterable[str]] = None,
) -> str:
    """在长句句中/句末注入语气与音效标签，不做句间拼接。"""
    original = (sentence or "").strip()
    if not original:
        return original
    if _has_inline_effect_tag(original) or _has_inline_tone_tag(original):
        return original

    inline_effect_tags = set(inline_effect_tags or []) & _INLINE_EFFECT_TAGS
    inline_tone_tags = set(inline_tone_tags or []) & _INLINE_TONE_TAGS
    active_effects = set(inline_effect_tags) if inline_effect_tags else (set(_AUTO_EFFECT_TAGS) if auto_breaks else set())
    active_tones = set(inline_tone_tags) if inline_tone_tags else (set(_INLINE_TONE_TAGS) if auto_breaks else set())

    visible_len = _visible_text_len(original)

    need_auto_rhythm = auto_breaks and visible_len >= 24
    need_template_rhythm = bool(inline_effect_tags) and visible_len >= 20
    need_semantic_effect = bool(active_effects)
    need_semantic_tone = bool(active_tones)
    if not (need_auto_rhythm or need_template_rhythm or need_semantic_effect or need_semantic_tone):
        return original

    clauses = _split_clauses(original)
    boundary_count = max(0, len(clauses) - 1)
    clause_prefix_tones: Dict[int, str] = {}
    max_semantic_tones = 2 if visible_len >= 48 else 1
    semantic_tone_count = 0
    recent_tone: Optional[str] = None
    for idx, clause in enumerate(clauses):
        if semantic_tone_count >= max_semantic_tones:
            break
        tone_tag = _detect_tone_tag(_strip_tags(clause), allowed_tags=active_tones)
        if tone_tag and tone_tag != recent_tone:
            clause_prefix_tones[idx] = tone_tag
            semantic_tone_count += 1
            recent_tone = tone_tag

    boundary_effects: Dict[int, str] = {}
    sentence_end_effects: List[str] = []
    max_semantic_effects = 3 if visible_len >= 48 else (2 if visible_len >= 28 else 1)
    semantic_effect_count = 0
    for idx, clause in enumerate(clauses):
        if semantic_effect_count >= max_semantic_effects:
            break
        effect_tag = _detect_effect_tag(_strip_tags(clause), allowed_tags=active_effects)
        if not effect_tag:
            continue
        semantic_effect_count += 1
        if idx < boundary_count:
            boundary_effects.setdefault(idx, effect_tag)
        elif effect_tag not in sentence_end_effects:
            sentence_end_effects.append(effect_tag)

    if boundary_count <= 0:
        rendered_sentence = original
        tone_tag = clause_prefix_tones.get(0)
        if tone_tag:
            rendered_sentence = f"{tone_tag} {rendered_sentence}".strip()
        if sentence_end_effects:
            rendered_sentence = f"{rendered_sentence} {' '.join(sentence_end_effects)}".strip()
        if need_auto_rhythm and "(breath)" in active_effects and "(breath)" not in rendered_sentence.lower():
            insert_at = max(1, len(rendered_sentence) // 2)
            rendered_sentence = f"{rendered_sentence[:insert_at]} (breath) {rendered_sentence[insert_at:]}".strip()
        return _SPACE_PATTERN.sub(" ", rendered_sentence).strip()

    pause_tag = "(breath)"
    allow_pause = "(long-break)" in inline_effect_tags
    allow_breath = "(breath)" in active_effects

    if visible_len >= 72:
        target_slots = 3
    elif visible_len >= 48:
        target_slots = 2
    else:
        target_slots = 1
    target_slots = min(target_slots, boundary_count)

    clause_lengths = [_visible_text_len(clause) for clause in clauses]
    boundary_positions: List[int] = []
    cumulative = 0
    for length in clause_lengths[:-1]:
        cumulative += length
        boundary_positions.append(cumulative)
    total_len = max(1, sum(clause_lengths))

    target_points: List[float] = [0.5 * total_len]
    if target_slots >= 2:
        target_points.append(0.72 * total_len)
    if target_slots >= 3:
        target_points.append(0.86 * total_len)
    target_points = target_points[:target_slots]

    selected_boundaries: List[int] = []
    for target in target_points:
        ranked = sorted(range(boundary_count), key=lambda idx: abs(boundary_positions[idx] - target))
        for idx in ranked:
            if idx in selected_boundaries:
                continue
            selected_boundaries.append(idx)
            break
    selected_boundaries.sort()

    for rank, boundary_idx in enumerate(selected_boundaries):
        if boundary_idx in boundary_effects:
            continue
        if allow_breath:
            boundary_effects[boundary_idx] = "(breath)"
            continue
        if allow_pause:
            boundary_effects[boundary_idx] = pause_tag
            continue

    rendered_parts: List[str] = []
    for idx, clause in enumerate(clauses):
        tone_tag = clause_prefix_tones.get(idx)
        if tone_tag:
            rendered_parts.append(f"{tone_tag} {clause.lstrip()}")
        else:
            rendered_parts.append(clause)
        tag = boundary_effects.get(idx)
        if tag:
            rendered_parts.append(f" {tag} ")

    rendered = "".join(rendered_parts)
    if sentence_end_effects:
        rendered = f"{rendered} {' '.join(sentence_end_effects)}"
    return _SPACE_PATTERN.sub(" ", rendered).strip()


def _build_from_tagged_text(
    tagged_text: str,
    *,
    emotion: Optional[str],
    auto_emotion: bool,
    auto_breaks: bool,
    merged_tones: Sequence[str],
    merged_effects: Sequence[str],
    voice_profile: Optional[dict],
) -> dict:
    sentences = split_sentences(tagged_text)
    if not sentences:
        raise TTSTagError("text 不能为空")

    global_emotion = normalize_emotion_tag(emotion) if emotion else None
    rendered_sentences: List[str] = []
    sentence_emotions: List[str] = []
    for sentence in sentences:
        existing_emotion = _extract_emotion_from_text(sentence)
        effective_emotion = global_emotion or existing_emotion
        if not effective_emotion and auto_emotion:
            effective_emotion = detect_sentence_emotion(sentence)

        normalized = normalize_tts_text(
            sentence,
            emotion=effective_emotion,
            tone_tags=[],
            effect_tags=[],
        )
        rendered_sentences.append(normalized["text"])
        sentence_emotions.append(normalized["emotion"] or "(calm)")

    final_text = " ".join(rendered_sentences)
    inline_tags = _extract_inline_tags(final_text)
    tone_tags = _dedupe([*merged_tones, *inline_tags["tones"]])
    effect_tags = _dedupe([*merged_effects, *inline_tags["effects"]])

    return {
        "text": final_text,
        "tagged_text": final_text,
        "sentence_emotions": sentence_emotions,
        "emotion": global_emotion,
        "tone_tags": tone_tags,
        "effect_tags": effect_tags,
        "auto_emotion": auto_emotion,
        "auto_breaks": auto_breaks,
        "voice_profile": voice_profile,
    }


async def build_expressive_tts_text_async(
    text: str,
    *,
    emotion: Optional[str] = None,
    tone_tags: Optional[Iterable[str]] = None,
    effect_tags: Optional[Iterable[str]] = None,
    auto_emotion: Optional[bool] = None,
    auto_breaks: Optional[bool] = None,
    voice_profile: Optional[dict] = None,
    tag_strategy: str = "llm",
    speech_style: str = "speech",
) -> dict:
    """异步构建带标签文本（支持 LLM 语义标注）。"""
    voice_profile = voice_profile or {}

    profile_tones = normalize_tone_tags(voice_profile.get("tone_tags") or [])
    profile_effects = normalize_effect_tags(voice_profile.get("effect_tags") or [])
    manual_tones = normalize_tone_tags(tone_tags or [])
    manual_effects = normalize_effect_tags(effect_tags or [])
    merged_tones = _dedupe([*profile_tones, *manual_tones])
    merged_effects = _dedupe([*profile_effects, *manual_effects])

    resolved_auto_emotion = bool(
        voice_profile.get("auto_emotion", True) if auto_emotion is None else auto_emotion
    )
    resolved_auto_breaks = bool(
        voice_profile.get("auto_breaks", True) if auto_breaks is None else auto_breaks
    )

    strategy = (tag_strategy or "llm").lower()
    if strategy == "none":
        sanitized = _sanitize_tagged_text(text or "")
        return _build_from_tagged_text(
            sanitized,
            emotion=emotion,
            auto_emotion=resolved_auto_emotion,
            auto_breaks=resolved_auto_breaks,
            merged_tones=merged_tones,
            merged_effects=merged_effects,
            voice_profile=voice_profile,
        )

    if strategy == "llm":
        tagged_text = await generate_tagged_text(
            text,
            speech_style=speech_style,
            preferred_tones=merged_tones,
            preferred_effects=merged_effects,
        )
        if tagged_text:
            sanitized = _sanitize_tagged_text(tagged_text)
            if _normalize_plain_text(sanitized) == _normalize_plain_text(text):
                return _build_from_tagged_text(
                    sanitized,
                    emotion=emotion,
                    auto_emotion=resolved_auto_emotion,
                    auto_breaks=resolved_auto_breaks,
                    merged_tones=merged_tones,
                    merged_effects=merged_effects,
                    voice_profile=voice_profile,
                )

    return build_expressive_tts_text(
        text,
        emotion=emotion,
        tone_tags=tone_tags,
        effect_tags=effect_tags,
        auto_emotion=resolved_auto_emotion,
        auto_breaks=resolved_auto_breaks,
        voice_profile=voice_profile,
    )


def detect_sentence_emotion(sentence: str) -> str:
    content = (sentence or "").strip()
    lowered = content.lower()

    keyword_groups = [
        ("(angry)", ["生气", "愤怒", "离谱", "可恶", "气死", "烦死", "暴怒", "怒"]),
        ("(sad)", ["难过", "伤心", "遗憾", "失落", "心碎", "痛苦", "悲伤"]),
        ("(worried)", ["担心", "害怕", "焦虑", "不安", "忐忑", "怕", "顾虑"]),
        ("(excited)", ["太棒", "绝了", "厉害", "牛", "冲", "wow", "amazing", "great"]),
        ("(happy)", ["开心", "高兴", "幸福", "愉快", "满意", "喜悦"]),
        ("(curious)", ["为什么", "如何", "怎么", "是什么", "吗", "么", "呢", "?", "？"]),
        ("(confident)", ["一定", "必须", "肯定", "稳", "绝对", "放心"]),
        ("(calm)", ["请", "建议", "可以", "我们", "首先", "然后", "最后"]),
    ]

    scores: Dict[str, int] = {}
    for emotion, keywords in keyword_groups:
        score = 0
        for kw in keywords:
            if kw in lowered or kw in content:
                score += 1
        if score > 0:
            scores[emotion] = score

    if "!" in content or "！" in content:
        scores["(excited)"] = scores.get("(excited)", 0) + 1
    if ("?" in content or "？" in content) and "(worried)" not in scores:
        scores["(curious)"] = scores.get("(curious)", 0) + 1

    if not scores:
        return "(calm)"

    # 分值相同时优先情绪更强烈的标签
    priority = ["(angry)", "(sad)", "(worried)", "(excited)", "(happy)", "(curious)", "(confident)", "(calm)"]
    max_score = max(scores.values())
    for tag in priority:
        if scores.get(tag) == max_score:
            return tag
    return "(calm)"


def build_expressive_tts_text(
    text: str,
    *,
    emotion: Optional[str] = None,
    tone_tags: Optional[Iterable[str]] = None,
    effect_tags: Optional[Iterable[str]] = None,
    auto_emotion: Optional[bool] = None,
    auto_breaks: Optional[bool] = None,
    voice_profile: Optional[dict] = None,
) -> dict:
    voice_profile = voice_profile or {}

    profile_tones = normalize_tone_tags(voice_profile.get("tone_tags") or [])
    profile_effects = normalize_effect_tags(voice_profile.get("effect_tags") or [])
    manual_tones = normalize_tone_tags(tone_tags or [])
    manual_effects = normalize_effect_tags(effect_tags or [])

    merged_tones = _dedupe([*profile_tones, *manual_tones])
    merged_effects = _dedupe([*profile_effects, *manual_effects])

    resolved_auto_emotion = bool(
        voice_profile.get("auto_emotion", True) if auto_emotion is None else auto_emotion
    )
    resolved_auto_breaks = bool(
        voice_profile.get("auto_breaks", True) if auto_breaks is None else auto_breaks
    )

    global_emotion = normalize_emotion_tag(emotion) if emotion else None

    inline_effects = [tag for tag in merged_effects if tag in _INLINE_EFFECT_TAGS]
    prefix_effects = [tag for tag in merged_effects if tag not in _INLINE_EFFECT_TAGS]

    sentences = split_sentences(text)
    if not sentences:
        raise TTSTagError("text 不能为空")

    rendered_sentences: List[str] = []
    sentence_emotions: List[str] = []
    for sentence in sentences:
        enhanced_sentence = _inject_intra_sentence_expressions(
            sentence,
            auto_breaks=resolved_auto_breaks,
            inline_effect_tags=inline_effects,
            inline_tone_tags=merged_tones,
        )

        existing_emotion = _extract_emotion_from_text(sentence)
        effective_emotion = global_emotion or existing_emotion
        if not effective_emotion and resolved_auto_emotion:
            effective_emotion = detect_sentence_emotion(sentence)

        normalized = normalize_tts_text(
            enhanced_sentence,
            emotion=effective_emotion,
            tone_tags=merged_tones,
            effect_tags=prefix_effects,
        )
        rendered_sentences.append(normalized["text"])
        sentence_emotions.append(normalized["emotion"] or "(calm)")

    tagged_text = " ".join(rendered_sentences)

    return {
        "text": tagged_text,
        "tagged_text": tagged_text,
        "sentence_emotions": sentence_emotions,
        "emotion": global_emotion,
        "tone_tags": merged_tones,
        "effect_tags": merged_effects,
        "auto_emotion": resolved_auto_emotion,
        "auto_breaks": resolved_auto_breaks,
    }
