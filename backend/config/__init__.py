# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/config/__init__.py
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
Configuration package
配置包

导出:
- settings: 全局配置实例
- Settings: 配置类
- brand_logos: 品牌 Logo 配置
"""
from config.settings import Settings, settings
from config.brand_logos import (
    BrandInfo,
    PLATFORM_BRANDS,
    LLM_PROVIDER_BRANDS,
    ALL_BRANDS,
    get_brand_by_key,
    get_brands_by_category,
)

__all__ = [
    # Settings
    "Settings",
    "settings",
    # Brand logos
    "BrandInfo",
    "PLATFORM_BRANDS",
    "LLM_PROVIDER_BRANDS",
    "ALL_BRANDS",
    "get_brand_by_key",
    "get_brands_by_category",
]
