# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/link_parser.py
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
链接解析器 - 识别社交媒体平台和提取内容ID

支持平台:
- 小红书 (xhs)
- 抖音 (dy)
- B站 (bilibili)
- 快手 (ks)
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from urllib.parse import urlparse


class Platform(str, Enum):
    """支持的平台"""
    XHS = "xhs"
    DOUYIN = "dy"
    BILIBILI = "bilibili"
    KUAISHOU = "ks"


@dataclass
class ParsedLink:
    """解析结果"""
    platform: Platform      # 平台类型
    content_id: str        # 内容ID（短链接可能为空）
    original_url: str      # 原始URL
    is_short_link: bool    # 是否为短链接


# 域名到平台的映射
PLATFORM_DOMAINS: dict[str, Platform] = {
    "xhslink.com": Platform.XHS,
    "xiaohongshu.com": Platform.XHS,
    "v.douyin.com": Platform.DOUYIN,
    "douyin.com": Platform.DOUYIN,
    "b23.tv": Platform.BILIBILI,
    "bilibili.com": Platform.BILIBILI,
    "v.kuaishou.com": Platform.KUAISHOU,
    "kuaishou.com": Platform.KUAISHOU,
}

# 短链接域名
SHORT_LINK_DOMAINS = {
    "xhslink.com",
    "v.douyin.com",
    "b23.tv",
    "v.kuaishou.com",
}

# 各平台的内容ID提取正则
CONTENT_ID_PATTERNS: dict[Platform, list[str]] = {
    Platform.XHS: [
        r"/explore/([a-zA-Z0-9]+)",
        r"/discovery/item/([a-zA-Z0-9]+)",
    ],
    Platform.DOUYIN: [
        r"/video/(\d+)",
        r"/note/(\d+)",
    ],
    Platform.BILIBILI: [
        r"/(BV[a-zA-Z0-9]+)",
        r"/video/(BV[a-zA-Z0-9]+)",
    ],
    Platform.KUAISHOU: [
        r"/short-video/([a-zA-Z0-9_-]+)",
    ],
}


class LinkParser:
    """链接解析器"""

    def parse(self, url: str) -> Optional[ParsedLink]:
        """
        解析链接

        Args:
            url: 用户输入的链接

        Returns:
            ParsedLink 或 None（无法识别时）
        """
        # 空URL检查
        if not url or not url.strip():
            return None

        # URL 规范化
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # 解析URL获取域名
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return None
        except Exception:
            return None

        # 移除 www. 前缀进行匹配
        hostname_clean = hostname.lstrip("www.")

        # 识别平台
        platform = None
        matched_domain = None
        for domain, plat in PLATFORM_DOMAINS.items():
            if hostname_clean == domain or hostname_clean.endswith("." + domain):
                platform = plat
                matched_domain = domain
                break

        if platform is None:
            return None

        # 判断是否为短链接
        is_short_link = matched_domain in SHORT_LINK_DOMAINS

        # 提取内容ID
        content_id = ""
        if not is_short_link:
            patterns = CONTENT_ID_PATTERNS.get(platform, [])
            path = parsed.path
            for pattern in patterns:
                match = re.search(pattern, path)
                if match:
                    content_id = match.group(1)
                    break

        return ParsedLink(
            platform=platform,
            content_id=content_id,
            original_url=url,
            is_short_link=is_short_link,
        )


def parse_link(url: str) -> Optional[ParsedLink]:
    """解析链接的便捷函数"""
    return LinkParser().parse(url)
