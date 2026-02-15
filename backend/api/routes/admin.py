# -*- coding: utf-8 -*-
"""
Admin 管理接口（仅管理员）

能力：
- Cookies 池管理（多账号轮换/失效处理）
- 用户管理（禁用/管理员）
- 用量统计（token/费用估算、API 请求计数）
"""

from __future__ import annotations

from typing import Optional, List, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import require_admin
from services.auth_service import User
from services.usage_service import usage_service
from services.admin.crawler_cookies_account_admin_service import crawler_cookies_account_admin_service
from services.admin.user_admin_service import user_admin_service


router = APIRouter()


# =========================
# Cookies Pool
# =========================

class CookiePoolItem(BaseModel):
    id: int
    platform_name: str
    account_name: str
    status: int
    invalid_timestamp: int = 0
    create_time: Optional[str] = None
    update_time: Optional[str] = None


class CookiePoolCreateRequest(BaseModel):
    platform_name: str = Field(..., description="xhs/dy/bili/ks")
    account_name: str = Field("", description="账号标识（可选）")
    cookies: str = Field(..., min_length=5)


class CookiePoolUpdateRequest(BaseModel):
    cookies: Optional[str] = None
    status: Optional[int] = Field(None, description="0=有效, -1=无效")
    account_name: Optional[str] = None


@router.get("/cookies/pool", response_model=List[CookiePoolItem])
async def list_cookie_pool(
    platform: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_admin),
):
    return await crawler_cookies_account_admin_service.list(platform=platform, limit=limit, offset=offset)


@router.post("/cookies/pool", response_model=Dict[str, Any])
async def create_cookie_pool_item(
    req: CookiePoolCreateRequest,
    _: User = Depends(require_admin),
):
    item_id = await crawler_cookies_account_admin_service.create(
        platform_name=req.platform_name,
        account_name=req.account_name,
        cookies=req.cookies,
    )
    return {"id": item_id}


@router.patch("/cookies/pool/{item_id}", response_model=Dict[str, Any])
async def update_cookie_pool_item(
    item_id: int,
    req: CookiePoolUpdateRequest,
    _: User = Depends(require_admin),
):
    ok = await crawler_cookies_account_admin_service.update(
        account_id=item_id,
        cookies=req.cookies,
        status=req.status,
        account_name=req.account_name,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="cookie pool item not found")
    return {"ok": True}


@router.delete("/cookies/pool/{item_id}", response_model=Dict[str, Any])
async def delete_cookie_pool_item(
    item_id: int,
    _: User = Depends(require_admin),
):
    ok = await crawler_cookies_account_admin_service.delete(account_id=item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="cookie pool item not found")
    return {"ok": True}


# =========================
# Users
# =========================

class AdminUserItem(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None
    status: int
    is_admin: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AdminUserUpdateRequest(BaseModel):
    status: Optional[int] = Field(None, description="0=待验证, 1=正常, 2=禁用")
    is_admin: Optional[int] = Field(None, description="0/1")


@router.get("/users", response_model=List[AdminUserItem])
async def list_users(
    q: Optional[str] = Query(None, description="email/display_name 模糊搜索"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_admin),
):
    return await user_admin_service.list(q=q, limit=limit, offset=offset)


@router.patch("/users/{user_id}", response_model=Dict[str, Any])
async def update_user(
    user_id: str,
    req: AdminUserUpdateRequest,
    _: User = Depends(require_admin),
):
    ok = await user_admin_service.update(user_id=user_id, status=req.status, is_admin=req.is_admin)
    if not ok:
        raise HTTPException(status_code=404, detail="user not found")
    return {"ok": True}


# =========================
# Usage
# =========================

@router.get("/usage/llm/summary", response_model=List[Dict[str, Any]])
async def llm_usage_summary(
    days: int = Query(7, ge=1, le=365),
    model: Optional[str] = Query(None),
    _: User = Depends(require_admin),
):
    return await usage_service.get_llm_usage_summary(days=days, model=model)
