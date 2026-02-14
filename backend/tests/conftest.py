# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/tests/conftest.py
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
Pytest 配置和 fixtures
"""
import pytest


@pytest.fixture
def sample_urls():
    """测试用的各平台链接样例"""
    return {
        "xhs_long": "https://www.xiaohongshu.com/explore/abc123def",
        "xhs_short": "https://xhslink.com/xyz789",
        "douyin_long": "https://www.douyin.com/video/7123456789012345678",
        "douyin_short": "https://v.douyin.com/abc123",
        "bilibili_long": "https://www.bilibili.com/video/BV1xx411c7mD",
        "bilibili_short": "https://b23.tv/abc123",
        "kuaishou_long": "https://www.kuaishou.com/short-video/abc123xyz",
        "kuaishou_short": "https://v.kuaishou.com/xyz789",
        "invalid": "https://www.google.com",
    }
