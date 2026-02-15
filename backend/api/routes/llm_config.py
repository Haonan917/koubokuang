# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/api/routes/llm_config.py
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
LLM 配置管理 API (简化版)

提供 LLM 配置的 CRUD 操作端点。
支持: OpenAI-compatible (Kimi/MiniMax/GPT), Anthropic, DeepSeek, Ollama
"""
from fastapi import APIRouter, HTTPException
from aiomysql import IntegrityError

from config import settings
from llm_provider import is_llm_configured
from schemas import (
    LLMConfigCreateRequest,
    LLMConfigUpdateRequest,
    LLMConfigInfo,
    LLMConfigListResponse,
)
from services.llm_config_service import llm_config_service

router = APIRouter()


def _ensure_llm_config_unlocked():
    if getattr(settings, "LLM_CONFIG_LOCKED", False):
        raise HTTPException(status_code=403, detail="LLM 配置已锁定，当前部署不允许用户配置")


@router.get("/status")
async def get_llm_config_status():
    """
    检查 LLM 配置状态

    返回是否有激活的 LLM 配置，用于前端在聊天前检查。
    """
    if getattr(settings, "LLM_CONFIG_LOCKED", False):
        return {
            "configured": is_llm_configured(),
            "active_config": None,
        }

    active_config = await llm_config_service.get_active_config_name()
    return {
        "configured": active_config is not None,
        "active_config": active_config,
    }


@router.get("", response_model=LLMConfigListResponse)
async def list_llm_configs():
    """
    获取所有 LLM 配置列表

    返回所有已配置的 LLM 信息（不含 API Key 明文）。
    """
    _ensure_llm_config_unlocked()
    items = await llm_config_service.list_all()
    active_config = await llm_config_service.get_active_config_name()
    return LLMConfigListResponse(items=items, active_config=active_config)


@router.get("/templates/list")
async def get_provider_templates():
    """
    获取各提供商的预设模板

    返回常用的 LLM 配置模板供用户参考。
    """
    _ensure_llm_config_unlocked()
    templates = {
        "openai": [
            {
                "name": "GPT-4o",
                "base_url": "https://api.openai.com/v1",
                "model_name": "gpt-4o",
                "description": "OpenAI GPT-4o 多模态模型",
                "support_multimodal": True,
            },
            {
                "name": "Kimi K2",
                "base_url": "https://api.moonshot.cn/v1",
                "model_name": "kimi-k2-thinking",
                "description": "月之暗面 Kimi K2 推理模型",
                "enable_thinking": True,
                "support_multimodal": False,
            },
            {
                "name": "MiniMax M2.1",
                "base_url": "https://api.minimaxi.com/v1",
                "model_name": "MiniMax-M2.1-lightning",
                "description": "MiniMax M2.1 高速模型",
                "enable_thinking": True,
                "support_multimodal": False,
            },
        ],
        "anthropic": [
            {
                "name": "Claude Sonnet 4.5",
                "base_url": "https://api.anthropic.com",
                "model_name": "claude-sonnet-4-5-20250929",
                "description": "Anthropic Claude Sonnet 4.5",
                "enable_thinking": True,
                "thinking_budget_tokens": 4096,
                "support_multimodal": True,
            },
            {
                "name": "Claude Opus 4.5",
                "base_url": "https://api.anthropic.com",
                "model_name": "claude-opus-4-5-20251101",
                "description": "Anthropic Claude Opus 4.5",
                "enable_thinking": True,
                "thinking_budget_tokens": 8192,
                "support_multimodal": True,
            },
        ],
        "deepseek": [
            {
                "name": "DeepSeek Reasoner",
                "base_url": "https://api.deepseek.com",
                "model_name": "deepseek-reasoner",
                "description": "DeepSeek 推理模型",
                "enable_thinking": True,
                "support_multimodal": False,
            },
            {
                "name": "DeepSeek Chat",
                "base_url": "https://api.deepseek.com",
                "model_name": "deepseek-chat",
                "description": "DeepSeek 对话模型",
                "support_multimodal": False,
            },
        ],
        "ollama": [
            {
                "name": "Qwen3 4B",
                "base_url": "http://localhost:11434",
                "model_name": "qwen3:4b",
                "description": "本地 Qwen3 4B 模型",
                "support_multimodal": False,
            },
            {
                "name": "Llava",
                "base_url": "http://localhost:11434",
                "model_name": "llava",
                "description": "本地 Llava 多模态模型",
                "support_multimodal": True,
            },
        ],
    }

    return {"templates": templates}


@router.get("/{config_name}", response_model=LLMConfigInfo)
async def get_llm_config(config_name: str):
    """
    获取指定 LLM 配置信息

    Args:
        config_name: 配置名称

    Returns:
        LLMConfigInfo (不含 API Key 明文)
    """
    _ensure_llm_config_unlocked()
    row = await llm_config_service.get_config(config_name, include_api_key=False)

    if not row:
        raise HTTPException(status_code=404, detail=f"配置 {config_name} 不存在")

    return LLMConfigInfo(
        config_name=row["config_name"],
        provider=row["provider"],
        is_active=bool(row.get("is_active", 0)),
        has_api_key=bool(row.get("has_api_key", 0)),
        base_url=row.get("base_url"),
        model_name=row["model_name"],
        enable_thinking=bool(row.get("enable_thinking", 0)),
        thinking_budget_tokens=row.get("thinking_budget_tokens", 4096),
        reasoning_effort=row.get("reasoning_effort", "high"),
        support_multimodal=bool(row.get("support_multimodal", 0)),
        description=row.get("description"),
        updated_at=row["updated_at"].isoformat() if row.get("updated_at") else "",
    )


@router.post("")
async def create_llm_config(request: LLMConfigCreateRequest):
    """
    创建新的 LLM 配置

    Args:
        request: LLMConfigCreateRequest

    Returns:
        操作结果
    """
    _ensure_llm_config_unlocked()
    try:
        auto_activated = await llm_config_service.create_config(request)
        message = f"配置 {request.config_name} 已创建"
        if auto_activated:
            message += "并自动激活"
        return {"success": True, "message": message, "auto_activated": auto_activated}
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail=f"配置名称 {request.config_name} 已存在"
        )


@router.put("/{config_name}")
async def update_llm_config(config_name: str, request: LLMConfigUpdateRequest):
    """
    更新 LLM 配置

    Args:
        config_name: 配置名称
        request: LLMConfigUpdateRequest

    Returns:
        操作结果
    """
    _ensure_llm_config_unlocked()
    # 检查配置是否存在
    existing = await llm_config_service.get_config(config_name)
    if not existing:
        raise HTTPException(status_code=404, detail=f"配置 {config_name} 不存在")

    updated = await llm_config_service.update_config(config_name, request)

    if not updated:
        return {"success": False, "message": "没有需要更新的字段"}

    return {"success": True, "message": f"配置 {config_name} 已更新"}


@router.delete("/{config_name}")
async def delete_llm_config(config_name: str):
    """
    删除 LLM 配置

    Args:
        config_name: 配置名称

    Returns:
        操作结果
    """
    _ensure_llm_config_unlocked()
    deleted = await llm_config_service.delete_config(config_name)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"配置 {config_name} 不存在")

    return {"success": True, "message": f"配置 {config_name} 已删除"}


@router.post("/{config_name}/activate")
async def activate_llm_config(config_name: str):
    """
    激活指定的 LLM 配置

    将指定配置设为当前激活配置，其他配置自动取消激活。

    Args:
        config_name: 配置名称

    Returns:
        操作结果
    """
    _ensure_llm_config_unlocked()
    # 检查配置是否存在
    existing = await llm_config_service.get_config(config_name)
    if not existing:
        raise HTTPException(status_code=404, detail=f"配置 {config_name} 不存在")

    await llm_config_service.set_active_config(config_name)

    return {"success": True, "message": f"已激活配置 {config_name}"}
