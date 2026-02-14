# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/insight_mode_service.py
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
Insight Mode 配置管理服务

提供分析模式的 CRUD 操作，支持动态 System Prompt 管理。
替代硬编码的 MODE_PROMPTS，实现模式的动态配置。
"""
import time
from typing import List, Optional, Dict, Any

import aiomysql

from config import settings
from schemas import (
    InsightModeInfo,
    InsightModeDetail,
    InsightModeCreateRequest,
    InsightModeUpdateRequest,
)


class InsightModeNotFoundError(Exception):
    """Insight Mode 不存在"""
    pass


class InsightModeSystemError(Exception):
    """系统模式不可删除"""
    pass


class InsightModeService:
    """Insight Mode 配置管理服务"""

    # 缓存配置
    _cache: Dict[str, Any] = {}
    _cache_timestamp: float = 0
    _cache_ttl: float = 300  # 5 分钟缓存

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

    def _invalidate_cache(self):
        """使缓存失效"""
        self._cache.clear()
        self._cache_timestamp = 0

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        return (time.time() - self._cache_timestamp) < self._cache_ttl

    async def list_all(self, active_only: bool = False) -> List[InsightModeInfo]:
        """
        列出所有 Insight Mode（不返回 system_prompt）

        Args:
            active_only: 是否只返回启用的模式

        Returns:
            InsightModeInfo 列表
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT
                        mode_key, is_active, sort_order,
                        label_zh, label_en, description_zh, description_en,
                        prefill_zh, prefill_en, icon, color,
                        keywords_zh, keywords_en, is_system, updated_at
                    FROM insight_modes
                """
                if active_only:
                    sql += " WHERE is_active = 1"
                sql += " ORDER BY sort_order ASC, id ASC"

                await cursor.execute(sql)
                rows = await cursor.fetchall()

                return [
                    InsightModeInfo(
                        mode_key=row["mode_key"],
                        is_active=bool(row["is_active"]),
                        sort_order=row["sort_order"] or 0,
                        label_zh=row["label_zh"],
                        label_en=row["label_en"],
                        description_zh=row["description_zh"],
                        description_en=row["description_en"],
                        prefill_zh=row["prefill_zh"],
                        prefill_en=row["prefill_en"],
                        icon=row["icon"] or "smart_toy",
                        color=row["color"] or "cyan",
                        keywords_zh=row["keywords_zh"],
                        keywords_en=row["keywords_en"],
                        is_system=bool(row["is_system"]),
                        updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
                    )
                    for row in rows
                ]

    async def get_mode(self, mode_key: str) -> Optional[InsightModeDetail]:
        """
        获取指定模式的详情（含 system_prompt）

        Args:
            mode_key: 模式标识

        Returns:
            InsightModeDetail 或 None
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT * FROM insight_modes WHERE mode_key = %s"
                await cursor.execute(sql, (mode_key,))
                row = await cursor.fetchone()

                if not row:
                    return None

                return InsightModeDetail(
                    mode_key=row["mode_key"],
                    is_active=bool(row["is_active"]),
                    sort_order=row["sort_order"] or 0,
                    label_zh=row["label_zh"],
                    label_en=row["label_en"],
                    description_zh=row["description_zh"],
                    description_en=row["description_en"],
                    prefill_zh=row["prefill_zh"],
                    prefill_en=row["prefill_en"],
                    icon=row["icon"] or "smart_toy",
                    color=row["color"] or "cyan",
                    keywords_zh=row["keywords_zh"],
                    keywords_en=row["keywords_en"],
                    is_system=bool(row["is_system"]),
                    system_prompt=row["system_prompt"],
                    updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
                )

    async def get_mode_prompt(self, mode_key: str) -> Optional[str]:
        """
        获取指定模式的 System Prompt（供 Agent 使用，带缓存）

        Args:
            mode_key: 模式标识

        Returns:
            system_prompt 字符串或 None
        """
        # 检查缓存
        cache_key = f"prompt:{mode_key}"
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]

        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT system_prompt FROM insight_modes WHERE mode_key = %s AND is_active = 1"
                await cursor.execute(sql, (mode_key,))
                row = await cursor.fetchone()

                prompt = row["system_prompt"] if row else None

                # 更新缓存
                if prompt:
                    self._cache[cache_key] = prompt
                    self._cache_timestamp = time.time()

                return prompt

    async def get_all_mode_prompts(self) -> Dict[str, str]:
        """
        获取所有启用模式的 System Prompt 映射（带缓存）

        Returns:
            {mode_key: system_prompt} 字典
        """
        cache_key = "all_prompts"
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]

        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT mode_key, system_prompt FROM insight_modes WHERE is_active = 1"
                await cursor.execute(sql)
                rows = await cursor.fetchall()

                prompts = {row["mode_key"]: row["system_prompt"] for row in rows}

                # 更新缓存
                self._cache[cache_key] = prompts
                self._cache_timestamp = time.time()

                return prompts

    async def get_intent_keywords(self) -> Dict[str, Dict[str, List[str]]]:
        """
        获取意图识别关键词映射（带缓存）

        Returns:
            {mode_key: {"zh": [...], "en": [...]}} 字典
        """
        cache_key = "intent_keywords"
        if self._is_cache_valid() and cache_key in self._cache:
            return self._cache[cache_key]

        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT mode_key, keywords_zh, keywords_en FROM insight_modes WHERE is_active = 1"
                await cursor.execute(sql)
                rows = await cursor.fetchall()

                keywords = {}
                for row in rows:
                    mode_key = row["mode_key"]
                    keywords[mode_key] = {
                        "zh": [k.strip() for k in (row["keywords_zh"] or "").split(",") if k.strip()],
                        "en": [k.strip() for k in (row["keywords_en"] or "").split(",") if k.strip()],
                    }

                # 更新缓存
                self._cache[cache_key] = keywords
                self._cache_timestamp = time.time()

                return keywords

    async def create_mode(self, request: InsightModeCreateRequest) -> None:
        """
        创建新的 Insight Mode

        Args:
            request: 创建请求
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 获取最大 sort_order
                await cursor.execute("SELECT MAX(sort_order) as max_order FROM insight_modes")
                result = await cursor.fetchone()
                next_order = (result[0] or 0) + 1

                sql = """
                    INSERT INTO insight_modes (
                        mode_key, is_active, sort_order,
                        label_zh, label_en, description_zh, description_en,
                        prefill_zh, prefill_en, icon, color,
                        keywords_zh, keywords_en, system_prompt, is_system
                    ) VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
                """
                await cursor.execute(sql, (
                    request.mode_key,
                    next_order,
                    request.label_zh,
                    request.label_en,
                    request.description_zh,
                    request.description_en,
                    request.prefill_zh,
                    request.prefill_en,
                    request.icon,
                    request.color,
                    request.keywords_zh,
                    request.keywords_en,
                    request.system_prompt,
                ))

        self._invalidate_cache()

    async def update_mode(self, mode_key: str, request: InsightModeUpdateRequest) -> bool:
        """
        更新 Insight Mode

        Args:
            mode_key: 模式标识
            request: 更新请求

        Returns:
            是否更新成功
        """
        pool = await self._get_pool()

        # 构建动态更新 SQL
        update_fields = []
        values = []

        if request.label_zh is not None:
            update_fields.append("label_zh = %s")
            values.append(request.label_zh)

        if request.label_en is not None:
            update_fields.append("label_en = %s")
            values.append(request.label_en)

        if request.description_zh is not None:
            update_fields.append("description_zh = %s")
            values.append(request.description_zh if request.description_zh else None)

        if request.description_en is not None:
            update_fields.append("description_en = %s")
            values.append(request.description_en if request.description_en else None)

        if request.prefill_zh is not None:
            update_fields.append("prefill_zh = %s")
            values.append(request.prefill_zh if request.prefill_zh else None)

        if request.prefill_en is not None:
            update_fields.append("prefill_en = %s")
            values.append(request.prefill_en if request.prefill_en else None)

        if request.icon is not None:
            update_fields.append("icon = %s")
            values.append(request.icon)

        if request.color is not None:
            update_fields.append("color = %s")
            values.append(request.color)

        if request.keywords_zh is not None:
            update_fields.append("keywords_zh = %s")
            values.append(request.keywords_zh if request.keywords_zh else None)

        if request.keywords_en is not None:
            update_fields.append("keywords_en = %s")
            values.append(request.keywords_en if request.keywords_en else None)

        if request.system_prompt is not None:
            update_fields.append("system_prompt = %s")
            values.append(request.system_prompt)

        if not update_fields:
            return False

        values.append(mode_key)

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = f"UPDATE insight_modes SET {', '.join(update_fields)} WHERE mode_key = %s"
                await cursor.execute(sql, values)
                affected = cursor.rowcount
                if affected > 0:
                    success = True
                else:
                    # MySQL 返回 0 可能是「数据未变化」，但记录仍存在
                    await cursor.execute(
                        "SELECT 1 FROM insight_modes WHERE mode_key = %s",
                        (mode_key,)
                    )
                    success = bool(await cursor.fetchone())

        if success and affected > 0:
            self._invalidate_cache()

        return success

    async def delete_mode(self, mode_key: str) -> bool:
        """
        删除 Insight Mode（系统内置模式不可删除）

        Args:
            mode_key: 模式标识

        Returns:
            是否删除成功

        Raises:
            InsightModeSystemError: 系统模式不可删除
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 检查是否为系统模式
                await cursor.execute(
                    "SELECT is_system FROM insight_modes WHERE mode_key = %s",
                    (mode_key,)
                )
                row = await cursor.fetchone()

                if not row:
                    return False

                if row["is_system"]:
                    raise InsightModeSystemError(f"系统模式 '{mode_key}' 不可删除")

                # 执行删除
                await cursor.execute(
                    "DELETE FROM insight_modes WHERE mode_key = %s",
                    (mode_key,)
                )
                success = cursor.rowcount > 0

        if success:
            self._invalidate_cache()

        return success

    async def toggle_active(self, mode_key: str) -> bool:
        """
        切换模式的启用状态

        Args:
            mode_key: 模式标识

        Returns:
            是否切换成功
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = "UPDATE insight_modes SET is_active = NOT is_active WHERE mode_key = %s"
                await cursor.execute(sql, (mode_key,))
                success = cursor.rowcount > 0

        if success:
            self._invalidate_cache()

        return success

    async def update_sort_order(self, mode_keys: List[str]) -> bool:
        """
        更新模式排序

        Args:
            mode_keys: 按顺序排列的 mode_key 列表

        Returns:
            是否更新成功
        """
        if not mode_keys:
            return False

        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for idx, mode_key in enumerate(mode_keys, start=1):
                    await cursor.execute(
                        "UPDATE insight_modes SET sort_order = %s WHERE mode_key = %s",
                        (idx, mode_key)
                    )

        self._invalidate_cache()
        return True

    async def initialize_default_modes(self) -> None:
        """
        检查默认模式是否已初始化

        此方法在应用启动时调用，用于验证数据库迁移是否正确执行。
        实际的数据初始化由迁移系统 (V005__insight_modes.sql) 完成。

        如果检测到表不存在或为空，会抛出异常提示检查迁移状态。
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # 检查系统模式数量
                    await cursor.execute("SELECT COUNT(*) FROM insight_modes WHERE is_system = 1")
                    result = await cursor.fetchone()
                    system_count = result[0] if result else 0

                    if system_count < 4:
                        from utils.logger import logger
                        logger.warning(
                            f"Only {system_count} system modes found. "
                            f"Expected 4. Check if migrations ran correctly."
                        )
                except Exception as e:
                    # 表可能不存在，迁移可能未运行
                    from utils.logger import logger
                    logger.warning(f"insight_modes table check failed: {e}")

        self._invalidate_cache()


# 创建全局服务实例
insight_mode_service = InsightModeService()
