# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/oauth_client.py
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
OAuth 客户端 - GitHub 和 Google OAuth 2.0 实现

提供:
- 生成授权 URL
- 用授权码换取 Access Token
- 获取用户信息
"""
import secrets
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

import httpx

from config import settings
from utils.logger import logger


@dataclass
class OAuthUserInfo:
    """OAuth 用户信息"""
    provider: str
    provider_user_id: str
    email: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    access_token: str
    refresh_token: Optional[str]
    raw_data: dict


class OAuthError(Exception):
    """OAuth 错误"""
    pass


class GitHubOAuthClient:
    """GitHub OAuth 客户端"""

    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_API_URL = "https://api.github.com/user"
    EMAIL_API_URL = "https://api.github.com/user/emails"

    def __init__(self):
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        self.callback_url = settings.GITHUB_CALLBACK_URL

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.client_id and self.client_secret)

    def get_authorize_url(self, state: str = None) -> tuple[str, str]:
        """
        生成授权 URL

        Returns:
            (authorize_url, state)
        """
        if not self.is_configured():
            raise OAuthError("GitHub OAuth 未配置")

        state = state or secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "scope": "read:user user:email",
            "state": state,
        }

        url = f"{self.AUTHORIZE_URL}?{urlencode(params)}"
        return url, state

    async def exchange_code(self, code: str) -> str:
        """
        用授权码换取 Access Token

        Returns:
            access_token
        """
        if not self.is_configured():
            raise OAuthError("GitHub OAuth 未配置")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.callback_url,
                },
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                logger.error(f"GitHub token exchange failed: {response.text}")
                raise OAuthError("获取 Access Token 失败")

            data = response.json()

            if "error" in data:
                logger.error(f"GitHub OAuth error: {data}")
                raise OAuthError(data.get("error_description", "OAuth 错误"))

            return data["access_token"]

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """获取用户信息"""
        async with httpx.AsyncClient() as client:
            # 获取基本用户信息
            response = await client.get(
                self.USER_API_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )

            if response.status_code != 200:
                logger.error(f"GitHub user API failed: {response.text}")
                raise OAuthError("获取用户信息失败")

            user_data = response.json()

            # 获取邮箱（可能需要单独请求）
            email = user_data.get("email")
            if not email:
                email_response = await client.get(
                    self.EMAIL_API_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                if email_response.status_code == 200:
                    emails = email_response.json()
                    # 优先使用主邮箱
                    for e in emails:
                        if e.get("primary") and e.get("verified"):
                            email = e["email"]
                            break
                    # 如果没有主邮箱，使用第一个已验证的
                    if not email:
                        for e in emails:
                            if e.get("verified"):
                                email = e["email"]
                                break

            return OAuthUserInfo(
                provider="github",
                provider_user_id=str(user_data["id"]),
                email=email,
                display_name=user_data.get("name") or user_data.get("login"),
                avatar_url=user_data.get("avatar_url"),
                access_token=access_token,
                refresh_token=None,  # GitHub 不返回 refresh token
                raw_data=user_data,
            )


class GoogleOAuthClient:
    """Google OAuth 客户端"""

    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_API_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.callback_url = settings.GOOGLE_CALLBACK_URL

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.client_id and self.client_secret)

    def get_authorize_url(self, state: str = None) -> tuple[str, str]:
        """
        生成授权 URL

        Returns:
            (authorize_url, state)
        """
        if not self.is_configured():
            raise OAuthError("Google OAuth 未配置")

        state = state or secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",  # 获取 refresh token
            "prompt": "consent",  # 每次都显示同意页面以获取 refresh token
        }

        url = f"{self.AUTHORIZE_URL}?{urlencode(params)}"
        return url, state

    async def exchange_code(self, code: str) -> tuple[str, Optional[str]]:
        """
        用授权码换取 Access Token

        Returns:
            (access_token, refresh_token)
        """
        if not self.is_configured():
            raise OAuthError("Google OAuth 未配置")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.callback_url,
                    "grant_type": "authorization_code",
                },
            )

            if response.status_code != 200:
                logger.error(f"Google token exchange failed: {response.text}")
                raise OAuthError("获取 Access Token 失败")

            data = response.json()

            if "error" in data:
                logger.error(f"Google OAuth error: {data}")
                raise OAuthError(data.get("error_description", "OAuth 错误"))

            return data["access_token"], data.get("refresh_token")

    async def get_user_info(self, access_token: str, refresh_token: str = None) -> OAuthUserInfo:
        """获取用户信息"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USER_API_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                logger.error(f"Google user API failed: {response.text}")
                raise OAuthError("获取用户信息失败")

            user_data = response.json()

            return OAuthUserInfo(
                provider="google",
                provider_user_id=user_data["id"],
                email=user_data.get("email"),
                display_name=user_data.get("name"),
                avatar_url=user_data.get("picture"),
                access_token=access_token,
                refresh_token=refresh_token,
                raw_data=user_data,
            )


# 单例
github_oauth = GitHubOAuthClient()
google_oauth = GoogleOAuthClient()


def get_oauth_client(provider: str):
    """获取 OAuth 客户端"""
    if provider == "github":
        return github_oauth
    elif provider == "google":
        return google_oauth
    else:
        raise OAuthError(f"不支持的 OAuth 提供商: {provider}")
