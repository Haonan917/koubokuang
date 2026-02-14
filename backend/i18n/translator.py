# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/i18n/translator.py
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
Translation utility for Content Remix Agent.

Uses ContextVar to maintain request-scoped language setting.
English is the default language.
"""
import json
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, Optional

# Request-scoped language setting
_current_language: ContextVar[str] = ContextVar('current_language', default='en')

# Supported languages
SUPPORTED_LANGUAGES = {'en', 'zh'}
DEFAULT_LANGUAGE = 'en'

# Load translations
_translations: Dict[str, Dict[str, Any]] = {}


def _load_translations():
    """Load all translation files on module init."""
    global _translations
    translations_dir = Path(__file__).parent / 'translations'

    for lang in SUPPORTED_LANGUAGES:
        lang_file = translations_dir / f'{lang}.json'
        if lang_file.exists():
            with open(lang_file, 'r', encoding='utf-8') as f:
                _translations[lang] = json.load(f)
        else:
            _translations[lang] = {}


# Load translations on module import
_load_translations()


def set_language(lang: str) -> None:
    """
    Set the current language for this request context.

    Args:
        lang: Language code ('en' or 'zh')
    """
    # Normalize language code
    if lang.startswith('zh'):
        lang = 'zh'
    elif lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    _current_language.set(lang)


def get_language() -> str:
    """Get the current language for this request context."""
    return _current_language.get()


def _get_nested(data: Dict, key: str, default: Any = None) -> Any:
    """Get nested dictionary value using dot notation."""
    keys = key.split('.')
    value = data

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value


def t(key: str, **kwargs) -> str:
    """
    Translate a key to the current language.

    Args:
        key: Translation key using dot notation (e.g., 'errors.urlEmpty')
        **kwargs: Interpolation variables (e.g., count=5)

    Returns:
        Translated string, or the key itself if not found

    Example:
        t('errors.urlEmpty')  # -> "URL cannot be empty"
        t('progress.downloadComplete', size="12.5")  # -> "Download complete: 12.5 MB"
    """
    lang = get_language()

    # Try current language first
    text = _get_nested(_translations.get(lang, {}), key)

    # Fall back to default language
    if text is None and lang != DEFAULT_LANGUAGE:
        text = _get_nested(_translations.get(DEFAULT_LANGUAGE, {}), key)

    # Return key if no translation found
    if text is None:
        return key

    # Interpolate variables (simple {{key}} replacement)
    if kwargs:
        for var_key, var_value in kwargs.items():
            text = text.replace(f'{{{{{var_key}}}}}', str(var_value))

    return text


def reload_translations():
    """Reload all translation files (useful for development)."""
    _load_translations()
