# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/api/routes/cookies.py
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
平台 Cookies 管理 API

提供 Cookies 的 CRUD 操作端点。
"""
from fastapi import APIRouter, HTTPException

from config import settings
from schemas import CookiesUpdateRequest, CookiesListResponse, CookiesInfo, CookiesDetail
from services.cookies_service import cookies_service

router = APIRouter()


def _ensure_cookies_manageable():
    if getattr(settings, "COOKIES_MANAGED_BY_ADMIN", False):
        raise HTTPException(status_code=403, detail="平台 Cookies 已锁定，当前部署不允许用户配置")


@router.get("", response_model=CookiesListResponse)
async def list_cookies():
    """
    获取所有平台 cookies 列表

    返回所有已配置的平台 cookies 信息（不含 cookies 明文）。
    """
    _ensure_cookies_manageable()
    items = await cookies_service.list_all()
    return CookiesListResponse(items=items)


@router.get("/{platform}", response_model=CookiesDetail)
async def get_cookies(platform: str):
    """
    获取指定平台 cookies 详情（含 cookies 明文，用于编辑）

    Args:
        platform: 平台标识 (xhs/dy/bili/ks)

    Returns:
        CookiesDetail (含 cookies 明文)
    """
    _ensure_cookies_manageable()
    detail = await cookies_service.get_detail(platform)
    if not detail:
        raise HTTPException(status_code=404, detail=f"平台 {platform} 未配置 cookies")
    return detail


@router.put("/{platform}")
async def set_cookies(platform: str, request: CookiesUpdateRequest):
    """
    新增/更新平台 cookies

    Args:
        platform: 平台标识 (xhs/dy/bili/ks)
        request: CookiesUpdateRequest

    Returns:
        操作结果
    """
    _ensure_cookies_manageable()
    valid_platforms = {"xhs", "dy", "bili", "ks"}
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"无效的平台标识，支持: {', '.join(valid_platforms)}"
        )

    await cookies_service.set_cookies(
        platform=platform,
        cookies=request.cookies,
        remark=request.remark,
    )

    return {"success": True, "message": f"平台 {platform} cookies 已更新"}


@router.delete("/{platform}")
async def delete_cookies(platform: str):
    """
    删除平台 cookies

    Args:
        platform: 平台标识 (xhs/dy/bili/ks)

    Returns:
        操作结果
    """
    _ensure_cookies_manageable()
    deleted = await cookies_service.delete_cookies(platform)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"平台 {platform} 未配置 cookies")

    return {"success": True, "message": f"平台 {platform} cookies 已删除"}
