# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/config/brand_logos.py
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
Brand Logo Configuration
品牌 Logo 配置定义
"""

from typing import List, Literal
from pydantic import BaseModel


class BrandInfo(BaseModel):
    """品牌信息模型"""

    key: str  # 品牌唯一标识（文件名）
    search_query: str  # Google Images 搜索关键词
    category: Literal["platform", "llm_provider"]  # 品牌分类
    display_name: str  # 显示名称


# ========== 平台品牌（4个） ==========
PLATFORM_BRANDS: List[BrandInfo] = [
    BrandInfo(
        key="xhs",
        search_query="小红书 xiaohongshu logo official transparent",
        category="platform",
        display_name="小红书"
    ),
    BrandInfo(
        key="dy",
        search_query="抖音 douyin logo official transparent",
        category="platform",
        display_name="抖音"
    ),
    BrandInfo(
        key="bilibili",
        search_query="bilibili logo official transparent",
        category="platform",
        display_name="哔哩哔哩"
    ),
    BrandInfo(
        key="ks",
        search_query="快手 kuaishou logo official transparent",
        category="platform",
        display_name="快手"
    ),
]


# ========== LLM 提供商品牌（3个） ==========
LLM_PROVIDER_BRANDS: List[BrandInfo] = [
    BrandInfo(
        key="openai",
        search_query="openai logo official transparent",
        category="llm_provider",
        display_name="OpenAI"
    ),
    BrandInfo(
        key="anthropic",
        search_query="anthropic logo official transparent",
        category="llm_provider",
        display_name="Anthropic"
    ),
    BrandInfo(
        key="deepseek",
        search_query="deepseek ai logo official transparent",
        category="llm_provider",
        display_name="DeepSeek"
    ),
]


# ========== 合并所有品牌 ==========
ALL_BRANDS: List[BrandInfo] = PLATFORM_BRANDS + LLM_PROVIDER_BRANDS


# ========== 辅助函数 ==========
def get_brand_by_key(key: str) -> BrandInfo | None:
    """根据 key 获取品牌信息"""
    for brand in ALL_BRANDS:
        if brand.key == key:
            return brand
    return None


def get_brands_by_category(category: Literal["platform", "llm_provider"]) -> List[BrandInfo]:
    """根据分类获取品牌列表"""
    return [brand for brand in ALL_BRANDS if brand.category == category]
