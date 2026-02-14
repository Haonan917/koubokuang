# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/llm_config_service.py
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
LLM 配置管理服务 (简化版)

提供 LLM 配置的 CRUD 操作，使用 remix_agent 数据库的 llm_configs 表。
支持: OpenAI-compatible (Kimi/MiniMax/GPT), Anthropic, DeepSeek, Ollama
"""
from typing import List, Optional, Dict, Any

import aiomysql

from config import settings
from schemas import LLMConfigInfo, LLMConfigCreateRequest, LLMConfigUpdateRequest


class LLMConfigNotFoundError(Exception):
    """LLM 配置不存在"""
    pass


class LLMConfigService:
    """LLM 配置管理服务"""

    def __init__(self):
        self._pool: Optional[aiomysql.Pool] = None

    async def _get_pool(self) -> aiomysql.Pool:
        """获取 Agent 数据库连接池"""
        if self._pool is None:
            self._pool = await aiomysql.create_pool(
                host=settings.AGENT_DB_HOST or "localhost",
                port=settings.AGENT_DB_PORT or 3306,
                user=settings.AGENT_DB_USER or "root",
                password=settings.AGENT_DB_PASSWORD or "",
                db=settings.AGENT_DB_NAME,
                charset="utf8mb4",
                autocommit=True,
                minsize=1,
                maxsize=5,
            )
        return self._pool

    async def close(self):
        """关闭数据库连接池"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def list_all(self) -> List[LLMConfigInfo]:
        """
        列出所有 LLM 配置（不返回 API Key 明文）

        Returns:
            LLMConfigInfo 列表
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT
                        config_name, provider, is_active,
                        api_key IS NOT NULL AND api_key != '' as has_api_key,
                        base_url, model_name,
                        enable_thinking, thinking_budget_tokens, reasoning_effort,
                        support_multimodal, description, updated_at
                    FROM llm_configs
                    ORDER BY is_active DESC, updated_at DESC
                """
                await cursor.execute(sql)
                rows = await cursor.fetchall()

                return [
                    LLMConfigInfo(
                        config_name=row["config_name"],
                        provider=row["provider"],
                        is_active=bool(row["is_active"]),
                        has_api_key=bool(row["has_api_key"]),
                        base_url=row["base_url"],
                        model_name=row["model_name"],
                        enable_thinking=bool(row["enable_thinking"]),
                        thinking_budget_tokens=row["thinking_budget_tokens"] or 4096,
                        reasoning_effort=row["reasoning_effort"] or "high",
                        support_multimodal=bool(row["support_multimodal"]),
                        description=row["description"],
                        updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
                    )
                    for row in rows
                ]

    async def get_active_config_name(self) -> Optional[str]:
        """获取当前激活的配置名称"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT config_name FROM llm_configs WHERE is_active = 1 LIMIT 1"
                await cursor.execute(sql)
                row = await cursor.fetchone()
                return row["config_name"] if row else None

    async def get_config(self, config_name: str, include_api_key: bool = False) -> Optional[Dict[str, Any]]:
        """
        获取指定配置的完整信息

        Args:
            config_name: 配置名称
            include_api_key: 是否包含 API Key（用于实际调用 LLM）

        Returns:
            配置字典或 None
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if include_api_key:
                    sql = "SELECT * FROM llm_configs WHERE config_name = %s"
                else:
                    sql = """
                        SELECT
                            config_name, provider, is_active,
                            api_key IS NOT NULL AND api_key != '' as has_api_key,
                            base_url, model_name,
                            enable_thinking, thinking_budget_tokens, reasoning_effort,
                            support_multimodal, description, updated_at
                        FROM llm_configs WHERE config_name = %s
                    """
                await cursor.execute(sql, (config_name,))
                return await cursor.fetchone()

    async def create_config(self, request: LLMConfigCreateRequest) -> bool:
        """
        创建新的 LLM 配置

        如果当前没有任何激活的配置，会自动将新配置设为激活状态。

        Args:
            request: 配置创建请求

        Returns:
            是否自动激活了该配置
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = """
                    INSERT INTO llm_configs (
                        config_name, provider, api_key, base_url, model_name,
                        enable_thinking, thinking_budget_tokens, reasoning_effort,
                        support_multimodal, description
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                await cursor.execute(sql, (
                    request.config_name,
                    request.provider.value,
                    request.api_key,
                    request.base_url,
                    request.model_name,
                    1 if request.enable_thinking else 0,
                    request.thinking_budget_tokens,
                    request.reasoning_effort,
                    1 if request.support_multimodal else 0,
                    request.description,
                ))

                # 如果没有任何激活配置，自动激活刚创建的配置
                await cursor.execute("SELECT COUNT(*) FROM llm_configs WHERE is_active = 1")
                (active_count,) = await cursor.fetchone()
                if active_count == 0:
                    await cursor.execute(
                        "UPDATE llm_configs SET is_active = 1 WHERE config_name = %s",
                        (request.config_name,),
                    )
                    return True
                return False

    async def update_config(self, config_name: str, request: LLMConfigUpdateRequest) -> bool:
        """
        更新 LLM 配置

        Args:
            config_name: 配置名称
            request: 更新请求

        Returns:
            是否更新成功
        """
        pool = await self._get_pool()

        # 构建动态更新 SQL
        update_fields = []
        values = []

        if request.provider is not None:
            update_fields.append("provider = %s")
            values.append(request.provider.value)

        if request.api_key is not None:
            update_fields.append("api_key = %s")
            values.append(request.api_key if request.api_key else None)

        if request.base_url is not None:
            update_fields.append("base_url = %s")
            values.append(request.base_url if request.base_url else None)

        if request.model_name is not None:
            update_fields.append("model_name = %s")
            values.append(request.model_name)

        if request.enable_thinking is not None:
            update_fields.append("enable_thinking = %s")
            values.append(1 if request.enable_thinking else 0)

        if request.thinking_budget_tokens is not None:
            update_fields.append("thinking_budget_tokens = %s")
            values.append(request.thinking_budget_tokens)

        if request.reasoning_effort is not None:
            update_fields.append("reasoning_effort = %s")
            values.append(request.reasoning_effort)

        if request.support_multimodal is not None:
            update_fields.append("support_multimodal = %s")
            values.append(1 if request.support_multimodal else 0)

        if request.description is not None:
            update_fields.append("description = %s")
            values.append(request.description if request.description else None)

        if not update_fields:
            return False

        values.append(config_name)

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = f"UPDATE llm_configs SET {', '.join(update_fields)} WHERE config_name = %s"
                await cursor.execute(sql, values)
                return cursor.rowcount > 0

    async def delete_config(self, config_name: str) -> bool:
        """
        删除 LLM 配置

        Args:
            config_name: 配置名称

        Returns:
            是否删除成功
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = "DELETE FROM llm_configs WHERE config_name = %s"
                await cursor.execute(sql, (config_name,))
                return cursor.rowcount > 0

    async def set_active_config(self, config_name: str) -> bool:
        """
        设置激活的配置

        Args:
            config_name: 配置名称

        Returns:
            是否设置成功
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 先取消所有激活状态
                await cursor.execute("UPDATE llm_configs SET is_active = 0")
                # 设置指定配置为激活
                sql = "UPDATE llm_configs SET is_active = 1 WHERE config_name = %s"
                await cursor.execute(sql, (config_name,))
                return cursor.rowcount > 0

    async def get_active_config_for_llm(self) -> Optional[Dict[str, Any]]:
        """
        获取当前激活配置的完整信息（包含 API Key，用于 LLM 调用）

        Returns:
            配置字典或 None
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT *
                    FROM llm_configs
                    WHERE is_active = 1
                    LIMIT 1
                """
                await cursor.execute(sql)
                return await cursor.fetchone()


# 创建全局服务实例
llm_config_service = LLMConfigService()
