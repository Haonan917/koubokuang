# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/tests/test_api.py
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
API 路由测试 - TDD
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_returns_ok(self, client):
        """测试健康检查返回 ok"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestModesEndpoint:
    """二创模式端点测试"""

    def test_modes_returns_list(self, client):
        """测试获取模式列表"""
        response = client.get("/api/v1/remix/modes")
        assert response.status_code == 200
        data = response.json()
        assert "modes" in data
        assert len(data["modes"]) == 4

    def test_modes_have_required_fields(self, client):
        """测试模式有必要字段"""
        response = client.get("/api/v1/remix/modes")
        data = response.json()

        for mode in data["modes"]:
            assert "value" in mode
            assert "label" in mode
            assert "description" in mode

    def test_modes_include_all_types(self, client):
        """测试包含所有模式类型"""
        response = client.get("/api/v1/remix/modes")
        data = response.json()

        values = [m["value"] for m in data["modes"]]
        assert "imitate" in values
        assert "rewrite" in values
        assert "summarize" in values
        assert "analyze" in values


class TestAnalyzeEndpoint:
    """分析端点测试"""

    def test_analyze_empty_url_returns_400(self, client):
        """测试空 URL 返回 400"""
        response = client.post(
            "/api/v1/remix/analyze",
            json={"url": ""}
        )
        assert response.status_code == 400

    def test_analyze_invalid_url_returns_400(self, client):
        """测试无效 URL 格式返回 400"""
        response = client.post(
            "/api/v1/remix/analyze",
            json={"url": "not-a-valid-url"}
        )
        assert response.status_code == 400


class TestChatEndpoint:
    """对话端点测试"""

    def test_chat_empty_message_returns_400(self, client):
        """测试空消息返回 400"""
        response = client.post(
            "/api/v1/remix/chat",
            json={"message": ""}
        )
        assert response.status_code == 400
