# -*- coding: utf-8 -*-
"""
MySQL-backed cookies account pool (MediaCrawlerPro schema)

Table: media_crawler_pro.crawler_cookies_account
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List

import aiomysql

import config
from pkg.tools import utils


def _platform_key(platform) -> str:
    try:
        return str(getattr(platform, "value", None) or platform)
    except Exception:
        return str(platform)


@dataclass
class CookiesAccount:
    id: int
    platform_name: str
    account_name: str
    cookies: str
    status: int
    invalid_timestamp: int


class CookiesAccountPool:
    def __init__(self) -> None:
        self._pool: Optional[aiomysql.Pool] = None

    async def _get_pool(self) -> aiomysql.Pool:
        if self._pool is None:
            self._pool = await aiomysql.create_pool(
                host=config.CRAWLER_DB_HOST,
                port=config.CRAWLER_DB_PORT,
                user=config.CRAWLER_DB_USER,
                password=config.CRAWLER_DB_PASSWORD,
                db=config.CRAWLER_DB_NAME,
                autocommit=True,
                charset="utf8mb4",
                minsize=1,
                maxsize=5,
            )
        return self._pool

    async def ensure_schema(self) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS crawler_cookies_account (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增ID',
                        account_name VARCHAR(64) NOT NULL DEFAULT '' COMMENT '账号名称',
                        platform_name VARCHAR(64) NOT NULL DEFAULT '' COMMENT '平台名称 (xhs | dy | ks | wb | bili | tieba)',
                        cookies TEXT COMMENT '对应自媒体平台登录成功后的cookies',
                        create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '该条记录的创建时间',
                        update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '该条记录的更新时间',
                        invalid_timestamp BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '账号失效时间戳',
                        status TINYINT NOT NULL DEFAULT 0 COMMENT '账号状态枚举值(0：有效，-1：无效)',
                        PRIMARY KEY (id),
                        KEY idx_crawler_cookies_account_01(update_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='爬虫采集账号表（cookies）';
                    """
                )

    async def get_one(self, platform) -> Optional[CookiesAccount]:
        await self.ensure_schema()
        pool = await self._get_pool()
        platform_name = _platform_key(platform)
        now_ts = int(time.time())
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT id, platform_name, account_name, cookies, status, invalid_timestamp
                    FROM crawler_cookies_account
                    WHERE platform_name = %s
                      AND status = 0
                      AND (invalid_timestamp = 0 OR invalid_timestamp > %s)
                      AND cookies IS NOT NULL
                      AND LENGTH(cookies) > 0
                    ORDER BY update_time DESC, id DESC
                    LIMIT 1
                    """,
                    (platform_name, now_ts),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                return CookiesAccount(
                    id=int(row["id"]),
                    platform_name=str(row.get("platform_name") or platform_name),
                    account_name=str(row.get("account_name") or ""),
                    cookies=str(row.get("cookies") or ""),
                    status=int(row.get("status") or 0),
                    invalid_timestamp=int(row.get("invalid_timestamp") or 0),
                )

    async def mark_invalid(self, account_id: int, reason: str = "") -> None:
        await self.ensure_schema()
        pool = await self._get_pool()
        now_ts = int(time.time())
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE crawler_cookies_account
                    SET status = -1,
                        invalid_timestamp = %s,
                        update_time = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (now_ts, int(account_id)),
                )
        if reason:
            utils.logger.warning(f"[CookiesAccountPool] mark invalid id={account_id}, reason={reason[:200]}")

    async def list_accounts(self, platform: Optional[str] = None, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        await self.ensure_schema()
        pool = await self._get_pool()
        where = ["1=1"]
        args: List[Any] = []
        if platform:
            where.append("platform_name = %s")
            args.append(platform)
        where_sql = " AND ".join(where)
        args.extend([int(limit), int(offset)])
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    f"""
                    SELECT id, account_name, platform_name, status, invalid_timestamp, update_time, create_time
                    FROM crawler_cookies_account
                    WHERE {where_sql}
                    ORDER BY update_time DESC, id DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(args),
                )
                rows = await cur.fetchall()
                return [dict(r) for r in (rows or [])]

    async def create_account(self, platform_name: str, account_name: str, cookies: str) -> int:
        await self.ensure_schema()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO crawler_cookies_account (account_name, platform_name, cookies, status, invalid_timestamp)
                    VALUES (%s, %s, %s, 0, 0)
                    """,
                    (account_name or "", platform_name, cookies),
                )
                return int(cur.lastrowid)

    async def update_account(self, account_id: int, *, cookies: Optional[str] = None, status: Optional[int] = None, account_name: Optional[str] = None) -> bool:
        await self.ensure_schema()
        pool = await self._get_pool()
        fields = []
        args: List[Any] = []
        if cookies is not None:
            fields.append("cookies = %s")
            args.append(cookies)
        if status is not None:
            fields.append("status = %s")
            args.append(int(status))
        if account_name is not None:
            fields.append("account_name = %s")
            args.append(account_name)
        if not fields:
            return True
        args.append(int(account_id))
        sql = f"UPDATE crawler_cookies_account SET {', '.join(fields)}, update_time = CURRENT_TIMESTAMP WHERE id = %s"
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, tuple(args))
                return (cur.rowcount or 0) > 0

    async def delete_account(self, account_id: int) -> bool:
        await self.ensure_schema()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM crawler_cookies_account WHERE id = %s", (int(account_id),))
                return (cur.rowcount or 0) > 0


cookies_account_pool = CookiesAccountPool()
