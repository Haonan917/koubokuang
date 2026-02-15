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
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

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
        record = await self.get_cookie_record(platform)
        if not record or not record.get("cookies"):
            raise CookiesNotConfiguredError(
                f"未找到平台 {platform} 的有效 cookies，请通过 API 添加"
            )
        return str(record["cookies"])

    def _get_env_cookies(self, platform: str) -> Optional[str]:
        normalized = (platform or "").lower().strip()
        alias_map = {
            "xhs": "PLATFORM_COOKIES_XHS",
            "dy": "PLATFORM_COOKIES_DY",
            "bili": "PLATFORM_COOKIES_BILI",
            "bilibili": "PLATFORM_COOKIES_BILI",
            "ks": "PLATFORM_COOKIES_KS",
            "kuaishou": "PLATFORM_COOKIES_KS",
        }
        setting_key = alias_map.get(normalized)
        if not setting_key:
            return None
        value = getattr(settings, setting_key, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    async def get_cookie_record(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        获取可用 cookies 记录（配置优先，池化表次之，旧表兜底）

        Returns:
            {
              "cookies": str,
              "source": "env|pool|legacy",
              "pool_id": int|None
            }
        """
        # 1) 配置文件优先
        env_cookies = self._get_env_cookies(platform)
        if env_cookies:
            return {"cookies": env_cookies, "source": "env", "pool_id": None}

        # 2) 池化表（platform_cookie_pool）
        pool_record = await self._get_pool_cookie(platform)
        if pool_record and pool_record.get("cookies"):
            return {
                "cookies": pool_record["cookies"],
                "source": "pool",
                "pool_id": pool_record["id"],
            }

        # 3) 旧表兜底（platform_cookies）
        legacy_cookies = await self._get_legacy_cookie(platform)
        if legacy_cookies:
            return {"cookies": legacy_cookies, "source": "legacy", "pool_id": None}
        return None

    async def _get_pool_cookie(self, platform: str) -> Optional[Dict[str, Any]]:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    sql = """
                        SELECT id, cookies
                        FROM platform_cookie_pool
                        WHERE platform = %s
                          AND status = 0
                          AND (cooldown_until IS NULL OR cooldown_until <= NOW())
                        ORDER BY priority DESC, fail_count ASC, last_success_at DESC, updated_at DESC
                        LIMIT 1
                    """
                    await cursor.execute(sql, (platform,))
                    return await cursor.fetchone()
        except Exception:
            # 未迁移或查询异常时静默回退到旧表
            return None

    async def _get_legacy_cookie(self, platform: str) -> Optional[str]:
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
                if row and row.get("cookies"):
                    return row["cookies"]
        return None

    async def mark_cookie_success(self, pool_id: Optional[int]) -> None:
        if not pool_id:
            return
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    sql = """
                        UPDATE platform_cookie_pool
                        SET fail_count = 0,
                            cooldown_until = NULL,
                            last_success_at = NOW(),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                    await cursor.execute(sql, (pool_id,))
        except Exception:
            return

    async def mark_cookie_failure(self, pool_id: Optional[int], reason: Optional[str] = None) -> None:
        if not pool_id:
            return
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        "SELECT fail_count FROM platform_cookie_pool WHERE id = %s LIMIT 1",
                        (pool_id,),
                    )
                    row = await cursor.fetchone()
                    if not row:
                        return
                    next_fail = int(row.get("fail_count") or 0) + 1
                    threshold = max(1, int(getattr(settings, "COOKIES_POOL_FAILURE_THRESHOLD", 3)))
                    cooldown_seconds = max(1, int(getattr(settings, "COOKIES_POOL_COOLDOWN_SECONDS", 300)))
                    now = datetime.utcnow()
                    cooldown_until = now + timedelta(seconds=cooldown_seconds)

                    # 达到阈值后置为过期，否则仅进入冷却
                    if next_fail >= threshold:
                        sql = """
                            UPDATE platform_cookie_pool
                            SET fail_count = %s,
                                status = 1,
                                last_failure_at = NOW(),
                                cooldown_until = %s,
                                remark = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """
                        await cursor.execute(
                            sql,
                            (next_fail, cooldown_until, reason if reason else "auto invalid by failures", pool_id),
                        )
                    else:
                        sql = """
                            UPDATE platform_cookie_pool
                            SET fail_count = %s,
                                last_failure_at = NOW(),
                                cooldown_until = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """
                        await cursor.execute(sql, (next_fail, cooldown_until, pool_id))
        except Exception:
            return

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
