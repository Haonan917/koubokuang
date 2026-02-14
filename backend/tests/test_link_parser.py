# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/tests/test_link_parser.py
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
链接解析器测试 - TDD

测试覆盖:
- 小红书长链接/短链接
- 抖音长链接/短链接
- B站长链接/短链接
- 快手长链接/短链接
- 无效链接处理
- URL格式处理（无协议前缀）
"""
import pytest

from services.link_parser import LinkParser, Platform, ParsedLink, parse_link


class TestLinkParser:
    """链接解析器测试类"""

    def setup_method(self):
        """每个测试方法前初始化解析器"""
        self.parser = LinkParser()

    # ========== 小红书测试 ==========

    def test_xhs_explore_long_link(self):
        """测试小红书 explore 长链接"""
        url = "https://www.xiaohongshu.com/explore/abc123def456"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.XHS
        assert result.content_id == "abc123def456"
        assert result.is_short_link is False
        assert result.original_url == url

    def test_xhs_discovery_long_link(self):
        """测试小红书 discovery 长链接"""
        url = "https://www.xiaohongshu.com/discovery/item/xyz789abc"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.XHS
        assert result.content_id == "xyz789abc"
        assert result.is_short_link is False

    def test_xhs_short_link(self):
        """测试小红书短链接"""
        url = "https://xhslink.com/xyz789"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.XHS
        assert result.is_short_link is True
        # 短链接可能无法直接提取ID
        assert result.content_id == "" or result.content_id is not None

    # ========== 抖音测试 ==========

    def test_douyin_video_long_link(self):
        """测试抖音视频长链接"""
        url = "https://www.douyin.com/video/7123456789012345678"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.DOUYIN
        assert result.content_id == "7123456789012345678"
        assert result.is_short_link is False

    def test_douyin_note_long_link(self):
        """测试抖音图文笔记长链接"""
        url = "https://www.douyin.com/note/7123456789012345678"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.DOUYIN
        assert result.content_id == "7123456789012345678"
        assert result.is_short_link is False

    def test_douyin_short_link(self):
        """测试抖音短链接"""
        url = "https://v.douyin.com/abc123xyz"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.DOUYIN
        assert result.is_short_link is True

    # ========== B站测试 ==========

    def test_bilibili_bv_long_link(self):
        """测试B站 BV号 长链接"""
        url = "https://www.bilibili.com/video/BV1xx411c7mD"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.BILIBILI
        assert result.content_id == "BV1xx411c7mD"
        assert result.is_short_link is False

    def test_bilibili_bv_with_params(self):
        """测试B站带参数的长链接"""
        url = "https://www.bilibili.com/video/BV1xx411c7mD?p=1&vd_source=xxx"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.BILIBILI
        assert result.content_id == "BV1xx411c7mD"

    def test_bilibili_short_link(self):
        """测试B站短链接"""
        url = "https://b23.tv/abc123"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.BILIBILI
        assert result.is_short_link is True

    # ========== 快手测试 ==========

    def test_kuaishou_short_video_long_link(self):
        """测试快手短视频长链接"""
        url = "https://www.kuaishou.com/short-video/abc123xyz789"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.KUAISHOU
        assert result.content_id == "abc123xyz789"
        assert result.is_short_link is False

    def test_kuaishou_short_link(self):
        """测试快手短链接"""
        url = "https://v.kuaishou.com/xyz789"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.KUAISHOU
        assert result.is_short_link is True

    # ========== 边界情况测试 ==========

    def test_invalid_link_returns_none(self):
        """测试无效链接返回 None"""
        url = "https://www.google.com"
        result = self.parser.parse(url)

        assert result is None

    def test_url_without_protocol(self):
        """测试没有协议前缀的URL"""
        url = "www.douyin.com/video/123456789"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.DOUYIN

    def test_url_with_http_protocol(self):
        """测试 http 协议的URL"""
        url = "http://www.bilibili.com/video/BV1abc123xyz"
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.BILIBILI

    def test_url_with_whitespace(self):
        """测试带有空白字符的URL"""
        url = "  https://www.douyin.com/video/123456789  "
        result = self.parser.parse(url)

        assert result is not None
        assert result.platform == Platform.DOUYIN

    def test_empty_url_returns_none(self):
        """测试空URL返回 None"""
        result = self.parser.parse("")
        assert result is None

        result = self.parser.parse("   ")
        assert result is None


class TestParseFunction:
    """测试便捷函数"""

    def test_parse_link_function(self):
        """测试 parse_link 便捷函数"""
        result = parse_link("https://www.douyin.com/video/123456789")

        assert result is not None
        assert result.platform == Platform.DOUYIN
        assert result.content_id == "123456789"
