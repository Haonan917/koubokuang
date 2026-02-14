# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/api/routes/insight_modes.py
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
Insight Mode 配置管理 API

提供分析模式的 CRUD 接口，支持动态管理 System Prompt Mode。

端点:
- GET    /api/v1/insight-modes          - 获取模式列表
- GET    /api/v1/insight-modes/{key}    - 获取模式详情
- POST   /api/v1/insight-modes          - 创建模式
- PUT    /api/v1/insight-modes/{key}    - 更新模式
- DELETE /api/v1/insight-modes/{key}    - 删除模式
- POST   /api/v1/insight-modes/{key}/toggle   - 切换启用状态
- POST   /api/v1/insight-modes/reorder  - 更新排序
"""

from fastapi import APIRouter, HTTPException, Query

from schemas import (
    InsightModeCreateRequest,
    InsightModeUpdateRequest,
    InsightModeListResponse,
    InsightModeDetail,
    InsightModeReorderRequest,
)
from services.insight_mode_service import (
    insight_mode_service,
    InsightModeNotFoundError,
    InsightModeSystemError,
)
from i18n import t

router = APIRouter()


@router.get("", response_model=InsightModeListResponse)
async def list_insight_modes(
    active_only: bool = Query(False, description="是否只返回启用的模式")
):
    """
    获取所有 Insight Mode 列表

    Args:
        active_only: 是否只返回启用的模式

    Returns:
        InsightModeListResponse
    """
    modes = await insight_mode_service.list_all(active_only=active_only)
    return InsightModeListResponse(items=modes)


@router.get("/{mode_key}", response_model=InsightModeDetail)
async def get_insight_mode(mode_key: str):
    """
    获取指定 Insight Mode 的详情（含 system_prompt）

    Args:
        mode_key: 模式标识

    Returns:
        InsightModeDetail
    """
    mode = await insight_mode_service.get_mode(mode_key)
    if not mode:
        raise HTTPException(status_code=404, detail=f"Mode '{mode_key}' not found")
    return mode


@router.post("")
async def create_insight_mode(request: InsightModeCreateRequest):
    """
    创建新的 Insight Mode

    Args:
        request: 创建请求

    Returns:
        创建成功消息
    """
    try:
        await insight_mode_service.create_mode(request)
        return {"success": True, "mode_key": request.mode_key}
    except Exception as e:
        if "Duplicate entry" in str(e):
            raise HTTPException(
                status_code=400,
                detail=f"Mode '{request.mode_key}' already exists"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{mode_key}")
async def update_insight_mode(mode_key: str, request: InsightModeUpdateRequest):
    """
    更新 Insight Mode

    Args:
        mode_key: 模式标识
        request: 更新请求

    Returns:
        更新成功消息
    """
    success = await insight_mode_service.update_mode(mode_key, request)
    if not success:
        raise HTTPException(status_code=404, detail=f"Mode '{mode_key}' not found")
    return {"success": True, "mode_key": mode_key}


@router.delete("/{mode_key}")
async def delete_insight_mode(mode_key: str):
    """
    删除 Insight Mode（系统模式不可删除）

    Args:
        mode_key: 模式标识

    Returns:
        删除成功消息
    """
    try:
        success = await insight_mode_service.delete_mode(mode_key)
        if not success:
            raise HTTPException(status_code=404, detail=f"Mode '{mode_key}' not found")
        return {"success": True, "mode_key": mode_key}
    except InsightModeSystemError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{mode_key}/toggle")
async def toggle_insight_mode(mode_key: str):
    """
    切换 Insight Mode 的启用状态

    Args:
        mode_key: 模式标识

    Returns:
        切换成功消息
    """
    success = await insight_mode_service.toggle_active(mode_key)
    if not success:
        raise HTTPException(status_code=404, detail=f"Mode '{mode_key}' not found")

    # 获取更新后的状态
    mode = await insight_mode_service.get_mode(mode_key)
    return {
        "success": True,
        "mode_key": mode_key,
        "is_active": mode.is_active if mode else False
    }


@router.post("/reorder")
async def reorder_insight_modes(request: InsightModeReorderRequest):
    """
    更新 Insight Mode 排序

    Args:
        request: 排序请求（包含按顺序排列的 mode_key 列表）

    Returns:
        排序成功消息
    """
    if not request.mode_keys:
        raise HTTPException(status_code=400, detail="mode_keys cannot be empty")

    success = await insight_mode_service.update_sort_order(request.mode_keys)
    return {"success": success}
