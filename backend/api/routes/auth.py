# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/api/routes/auth.py
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
认证 API 路由

端点:
- POST /register - 邮箱注册
- POST /login - 邮箱登录
- POST /logout - 登出
- POST /refresh - 刷新 Token
- GET /me - 获取当前用户
- GET /oauth/{provider}/authorize - OAuth 授权 URL
- POST /oauth/{provider}/callback - OAuth 回调
- POST /verify-email - 验证邮箱
- POST /forgot-password - 请求重置密码
- POST /reset-password - 重置密码
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from api.dependencies import (
    get_client_ip,
    get_current_user,
    get_current_user_optional,
    get_user_agent,
)
from services.auth_service import (
    LoginRequest,
    RegisterRequest,
    User,
    UserStatus,
    auth_service,
)
from services.email_service import email_service
from services.oauth_client import OAuthError, get_oauth_client
from utils.logger import logger


router = APIRouter()


# ========== 请求/响应模型 ==========

class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: "UserResponse"


class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    email: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    status: int
    email_verified: bool
    is_admin: int = 0

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return cls(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            status=user.status,
            email_verified=user.email_verified_at is not None,
            is_admin=int(getattr(user, "is_admin", 0) or 0),
        )


class RefreshRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str


class OAuthCallbackRequest(BaseModel):
    """OAuth 回调请求"""
    code: str
    state: Optional[str] = None


class VerifyEmailRequest(BaseModel):
    """验证邮箱请求"""
    token: str


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    token: str
    new_password: str


class OAuthProviderStatus(BaseModel):
    """OAuth 提供商状态"""
    github: bool
    google: bool


# ========== 注册/登录 ==========

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, req: Request):
    """
    邮箱注册

    注册成功后返回 Token，同时发送验证邮件。
    """
    try:
        user, token_pair = await auth_service.register(request)

        # 创建验证令牌并发送邮件
        verification_token = await auth_service.create_verification_token(
            user.user_id, "email_verify", expires_hours=24
        )
        await email_service.send_verification_email(
            user.email, verification_token, user.display_name
        )

        logger.info(f"User registered: {user.email}")

        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in,
            user=UserResponse.from_user(user),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, req: Request):
    """邮箱登录"""
    try:
        user, token_pair = await auth_service.login(request)

        # 保存 refresh token 时记录设备信息
        ip = get_client_ip(req)
        device = get_user_agent(req)

        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in,
            user=UserResponse.from_user(user),
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout")
async def logout(request: RefreshRequest):
    """登出（撤销 Refresh Token）"""
    await auth_service.logout(request.refresh_token)
    return {"success": True}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """刷新 Token"""
    token_pair = await auth_service.refresh_tokens(request.refresh_token)

    if not token_pair:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token 无效或已过期",
        )

    # 获取用户信息
    user_id = auth_service.verify_access_token(token_pair.access_token)
    user = await auth_service.get_user_by_id(user_id)

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_in=token_pair.expires_in,
        user=UserResponse.from_user(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse.from_user(user)


# ========== OAuth ==========

@router.get("/oauth/providers", response_model=OAuthProviderStatus)
async def get_oauth_providers():
    """获取可用的 OAuth 提供商"""
    from services.oauth_client import github_oauth, google_oauth

    return OAuthProviderStatus(
        github=github_oauth.is_configured(),
        google=google_oauth.is_configured(),
    )


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(provider: str):
    """
    获取 OAuth 授权 URL

    前端重定向到返回的 URL 进行授权
    """
    try:
        client = get_oauth_client(provider)
        url, state = client.get_authorize_url()

        # 存储 state 到数据库（防 CSRF，支持重启和多进程）
        await auth_service.save_oauth_state(state, provider)
        logger.info(f"[OAuth] authorize: provider={provider}, state={state[:16]}...")

        return {"authorize_url": url, "state": state}

    except OAuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/oauth/{provider}/callback", response_model=TokenResponse)
async def oauth_callback(provider: str, request: OAuthCallbackRequest, req: Request):
    """
    OAuth 回调

    用授权码换取用户信息并登录/注册
    """
    # 验证 state（防 CSRF，从数据库读取）
    if request.state:
        stored_provider = await auth_service.consume_oauth_state(request.state)
        logger.info(f"[OAuth] callback: provider={provider}, stored_provider={stored_provider}")
        if stored_provider != provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的 state 参数",
            )

    try:
        client = get_oauth_client(provider)

        # 换取 access token
        if provider == "github":
            access_token = await client.exchange_code(request.code)
            user_info = await client.get_user_info(access_token)
        else:  # google
            access_token, refresh_token = await client.exchange_code(request.code)
            user_info = await client.get_user_info(access_token, refresh_token)

        # 登录或注册
        user, token_pair, is_new = await auth_service.oauth_login_or_register(
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
            email=user_info.email,
            display_name=user_info.display_name,
            avatar_url=user_info.avatar_url,
            access_token=user_info.access_token,
            refresh_token=user_info.refresh_token,
            raw_data=user_info.raw_data,
        )

        # 新用户发送欢迎邮件
        if is_new and user_info.email:
            await email_service.send_welcome_email(user_info.email, user_info.display_name)

        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in,
            user=UserResponse.from_user(user),
        )

    except OAuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ========== 邮箱验证 ==========

@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest):
    """验证邮箱"""
    user_id = await auth_service.verify_token(request.token, "email_verify")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证链接无效或已过期",
        )

    # 更新用户状态
    from datetime import datetime, timezone
    user = await auth_service.update_user(
        user_id,
        status=UserStatus.ACTIVE,
        email_verified_at=datetime.now(timezone.utc),
    )

    if user:
        # 发送欢迎邮件
        await email_service.send_welcome_email(user.email, user.display_name)

    return {"success": True, "message": "邮箱验证成功"}


@router.post("/resend-verification")
async def resend_verification(user: User = Depends(get_current_user)):
    """重新发送验证邮件"""
    if user.email_verified_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已验证",
        )

    # 创建新的验证令牌
    token = await auth_service.create_verification_token(
        user.user_id, "email_verify", expires_hours=24
    )

    # 发送验证邮件
    await email_service.send_verification_email(user.email, token, user.display_name)

    return {"success": True, "message": "验证邮件已发送"}


# ========== 密码重置 ==========

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """请求重置密码"""
    # 查找用户
    user_data = await auth_service.get_user_by_email(request.email)

    # 即使用户不存在也返回成功（防止邮箱探测）
    if not user_data:
        return {"success": True, "message": "如果邮箱存在，重置链接已发送"}

    # OAuth 用户没有密码
    if not user_data.get("password_hash"):
        return {"success": True, "message": "如果邮箱存在，重置链接已发送"}

    # 创建重置令牌（1 小时有效）
    token = await auth_service.create_verification_token(
        user_data["user_id"], "password_reset", expires_hours=1
    )

    # 发送重置邮件
    await email_service.send_password_reset_email(
        request.email, token, user_data.get("display_name")
    )

    return {"success": True, "message": "如果邮箱存在，重置链接已发送"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """重置密码"""
    # 验证令牌
    user_id = await auth_service.verify_token(request.token, "password_reset")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置链接无效或已过期",
        )

    # 密码强度验证
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度至少为 6 位",
        )

    # 更新密码
    success = await auth_service.update_password(user_id, request.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码更新失败",
        )

    # 撤销所有 refresh token（强制重新登录）
    await auth_service.revoke_all_user_tokens(user_id)

    return {"success": True, "message": "密码重置成功，请重新登录"}
