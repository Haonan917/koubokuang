# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/cookies_service.py
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
平台 Cookies 管理服务

提供 Cookies 的 CRUD 操作，使用 remix_agent 数据库的 platform_cookies 表。
"""
from typing import List, Optional

import aiomysql

from config import settings
from schemas import CookiesInfo, CookiesDetail


class CookiesNotConfiguredError(Exception):
    """Cookies 未配置或已失效"""
    pass


class CookiesService:
    """平台 Cookies 管理服务"""

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

    async def get_cookies(self, platform: str) -> str:
        """
        获取指定平台的有效 cookies

        Args:
            platform: 平台标识 (xhs/dy/bilibili/ks)

        Returns:
            cookies 字符串

        Raises:
            CookiesNotConfiguredError: 未找到有效的 cookies
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT cookies
                    FROM platform_cookies
                    WHERE platform = %s AND status = 0
                    LIMIT 1
                """
                await cursor.execute(sql, (platform,))
                row = await cursor.fetchone()

                if not row or not row.get("cookies"):
                    raise CookiesNotConfiguredError(
                        f"未找到平台 {platform} 的有效 cookies，请通过 API 添加"
                    )

                return row["cookies"]

    async def get_detail(self, platform: str) -> Optional[CookiesDetail]:
        """
        获取指定平台的 cookies 详情（含 cookies 明文）

        Args:
            platform: 平台标识 (xhs/dy/bili/ks)

        Returns:
            CookiesDetail 或 None
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT platform, cookies, status, remark, updated_at
                    FROM platform_cookies
                    WHERE platform = %s
                    LIMIT 1
                """
                await cursor.execute(sql, (platform,))
                row = await cursor.fetchone()

                if not row:
                    return None

                return CookiesDetail(
                    platform=row["platform"],
                    cookies=row["cookies"] or "",
                    status=row["status"],
                    remark=row["remark"],
                    updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
                )

    async def set_cookies(
        self, platform: str, cookies: str, remark: Optional[str] = None
    ) -> None:
        """
        设置平台 cookies (upsert)

        Args:
            platform: 平台标识
            cookies: Cookie 字符串
            remark: 备注
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = """
                    INSERT INTO platform_cookies (platform, cookies, status, remark)
                    VALUES (%s, %s, 0, %s)
                    ON DUPLICATE KEY UPDATE
                        cookies = VALUES(cookies),
                        status = 0,
                        remark = VALUES(remark),
                        updated_at = CURRENT_TIMESTAMP
                """
                await cursor.execute(sql, (platform, cookies, remark))

    async def list_all(self) -> List[CookiesInfo]:
        """
        列出所有平台 cookies（不返回 cookies 明文）

        Returns:
            CookiesInfo 列表
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT platform, status, remark, updated_at
                    FROM platform_cookies
                    ORDER BY updated_at DESC
                """
                await cursor.execute(sql)
                rows = await cursor.fetchall()

                return [
                    CookiesInfo(
                        platform=row["platform"],
                        status=row["status"],
                        remark=row["remark"],
                        updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
                    )
                    for row in rows
                ]

    async def delete_cookies(self, platform: str) -> bool:
        """
        删除指定平台 cookies

        Args:
            platform: 平台标识

        Returns:
            是否删除成功（True 表示找到并删除了记录）
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = "DELETE FROM platform_cookies WHERE platform = %s"
                await cursor.execute(sql, (platform,))
                return cursor.rowcount > 0

    async def update_status(self, platform: str, status: int) -> bool:
        """
        更新 cookies 状态

        Args:
            platform: 平台标识
            status: 状态 (0=有效, 1=过期, 2=禁用)

        Returns:
            是否更新成功
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = """
                    UPDATE platform_cookies
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE platform = %s
                """
                await cursor.execute(sql, (status, platform))
                return cursor.rowcount > 0


# 创建全局服务实例
cookies_service = CookiesService()
