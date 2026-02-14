# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/i18n/middleware.py
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
FastAPI middleware for i18n language detection.

Reads Accept-Language header and sets the language for the request context.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .translator import set_language, DEFAULT_LANGUAGE


class LanguageMiddleware(BaseHTTPMiddleware):
    """
    Middleware that sets the request language from Accept-Language header.

    Usage:
        app.add_middleware(LanguageMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        # Get Accept-Language header
        accept_language = request.headers.get('Accept-Language', DEFAULT_LANGUAGE)

        # Parse and set language (simple parsing, takes first language)
        # Accept-Language format: en-US,en;q=0.9,zh-CN;q=0.8
        lang = accept_language.split(',')[0].split('-')[0].strip()

        set_language(lang)

        response = await call_next(request)
        return response
