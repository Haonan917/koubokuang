# -*- coding: utf-8 -*-
"""
Crawler content cache (MySQL)

Purpose:
- Store normalized ContentDetailResponse payload in `media_crawler_pro` DB.
- Avoid re-crawling the same content_id for the same platform.

This is intentionally decoupled from the platform-specific tables in MediaCrawlerPro-Python.
"""

from __future__ import annotations

import json
from typing import Optional

import aiomysql

import config
from pkg.tools import utils


def _platform_key(platform) -> str:
    try:
        return str(getattr(platform, "value", None) or platform)
    except Exception:
        return str(platform)


def _dump_model(obj) -> dict:
    # pydantic v1: dict(); v2: model_dump()
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return dict(obj)


class CrawlerCache:
    def __init__(self) -> None:
        self._pool: Optional[aiomysql.Pool] = None
        self._initialized: bool = False

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

    async def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            self._initialized = False

    async def ensure_schema(self) -> None:
        if not config.CRAWLER_CACHE_ENABLED:
            return
        if self._initialized:
            return
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS crawler_content_cache (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        platform VARCHAR(20) NOT NULL,
                        content_id VARCHAR(128) NOT NULL,
                        content_url TEXT DEFAULT NULL,
                        payload_json LONGTEXT NOT NULL,
                        fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uk_platform_content (platform, content_id),
                        INDEX idx_platform_updated (platform, updated_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Content detail cache for DownloadServer';
                    """
                )
        self._initialized = True

    async def get_cached_payload(self, platform, content_id: str) -> Optional[dict]:
        if not config.CRAWLER_CACHE_ENABLED:
            return None
        await self.ensure_schema()
        pool = await self._get_pool()
        platform_str = _platform_key(platform)
        max_age = int(getattr(config, "CRAWLER_CACHE_MAX_AGE_SECONDS", 86400) or 86400)
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT payload_json
                    FROM crawler_content_cache
                    WHERE platform = %s
                      AND content_id = %s
                      AND TIMESTAMPDIFF(SECOND, updated_at, NOW()) <= %s
                    LIMIT 1
                    """,
                    (platform_str, content_id, max_age),
                )
                row = await cur.fetchone()
                if not row:
                    return None
                try:
                    return json.loads(row["payload_json"])
                except Exception:
                    return None

    async def upsert_payload(self, platform, content_id: str, content_url: str, payload_obj) -> None:
        if not config.CRAWLER_CACHE_ENABLED:
            return
        await self.ensure_schema()
        pool = await self._get_pool()
        platform_str = _platform_key(platform)
        try:
            payload_json = json.dumps(_dump_model(payload_obj), ensure_ascii=False)
        except Exception:
            return
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO crawler_content_cache (platform, content_id, content_url, payload_json, fetched_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        content_url = VALUES(content_url),
                        payload_json = VALUES(payload_json),
                        fetched_at = VALUES(fetched_at),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (platform_str, content_id, content_url, payload_json),
                )

    async def safe_initialize(self) -> None:
        if not config.CRAWLER_CACHE_ENABLED:
            utils.logger.info("[CrawlerCache] disabled by config")
            return
        try:
            await self.ensure_schema()
            utils.logger.info(
                f"[CrawlerCache] enabled: db={config.CRAWLER_DB_NAME}, max_age={config.CRAWLER_CACHE_MAX_AGE_SECONDS}s"
            )
        except Exception as e:
            utils.logger.warning(f"[CrawlerCache] init failed, cache disabled: {e}")


crawler_cache = CrawlerCache()
