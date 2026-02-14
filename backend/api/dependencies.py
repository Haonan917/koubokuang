# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/api/dependencies.py
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
FastAPI 依赖注入 - 认证相关

提供:
- get_current_user: 从 JWT Token 获取当前用户
- get_current_user_optional: 可选认证（未登录返回 None）
- require_verified_user: 要求邮箱已验证
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import User, UserStatus, auth_service


# HTTP Bearer Token 提取器
bearer_scheme = HTTPBearer(auto_error=False)


async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Optional[str]:
    """从 Authorization 头提取 Token"""
    if credentials:
        return credentials.credentials
    return None


async def get_current_user(
    token: Optional[str] = Depends(get_token_from_header),
) -> User:
    """
    获取当前用户（必须已登录）

    Usage:
        @router.get("/me")
        async def get_me(user: User = Depends(get_current_user)):
            return user
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = auth_service.verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status == UserStatus.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(get_token_from_header),
) -> Optional[User]:
    """
    获取当前用户（可选，未登录返回 None）

    Usage:
        @router.get("/data")
        async def get_data(user: Optional[User] = Depends(get_current_user_optional)):
            if user:
                # 已登录用户
                ...
            else:
                # 未登录用户
                ...
    """
    if not token:
        return None

    user_id = auth_service.verify_access_token(token)
    if not user_id:
        return None

    user = await auth_service.get_user_by_id(user_id)
    if not user or user.status == UserStatus.DISABLED:
        return None

    return user


async def require_verified_user(
    user: User = Depends(get_current_user),
) -> User:
    """
    要求邮箱已验证的用户

    Usage:
        @router.post("/sensitive-action")
        async def sensitive_action(user: User = Depends(require_verified_user)):
            ...
    """
    if user.status == UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先验证邮箱",
        )
    return user


def get_client_ip(request: Request) -> str:
    """获取客户端 IP"""
    # 检查代理头
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # 直接连接
    if request.client:
        return request.client.host

    return "unknown"


def get_user_agent(request: Request) -> str:
    """获取用户代理"""
    return request.headers.get("User-Agent", "unknown")[:255]
