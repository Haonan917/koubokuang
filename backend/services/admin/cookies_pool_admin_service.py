# -*- coding: utf-8 -*-
"""
platform_cookie_pool 管理服务（管理员）
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any

from sqlalchemy import text

from db.base import get_async_session


class CookiesPoolAdminService:
    async def list(
        self,
        platform: Optional[str] = None,
        status: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        where = ["1=1"]
        params: Dict[str, Any] = {"limit": int(limit), "offset": int(offset)}
        if platform:
            where.append("platform = :platform")
            params["platform"] = platform
        if status is not None:
            where.append("status = :status")
            params["status"] = int(status)

        sql = f"""
            SELECT
              id, platform, status, priority, fail_count,
              cooldown_until, last_success_at, last_failure_at,
              remark, created_at, updated_at
            FROM platform_cookie_pool
            WHERE {" AND ".join(where)}
            ORDER BY platform ASC, priority DESC, updated_at DESC
            LIMIT :limit OFFSET :offset
        """
        async with get_async_session() as session:
            result = await session.execute(text(sql), params)
            return [dict(r) for r in result.mappings().all()]

    async def create(self, platform: str, cookies: str, priority: int = 0, remark: Optional[str] = None) -> int:
        async with get_async_session() as session:
            result = await session.execute(
                text(
                    """
                    INSERT INTO platform_cookie_pool (platform, cookies, status, priority, remark)
                    VALUES (:platform, :cookies, 0, :priority, :remark)
                    """
                ),
                {
                    "platform": platform,
                    "cookies": cookies,
                    "priority": int(priority),
                    "remark": remark,
                },
            )
            # SQLAlchemy async Result does not always expose lastrowid; use SELECT LAST_INSERT_ID()
            last = await session.execute(text("SELECT LAST_INSERT_ID() AS id"))
            return int(last.mappings().fetchone()["id"])

    async def update(
        self,
        item_id: int,
        cookies: Optional[str] = None,
        status: Optional[int] = None,
        priority: Optional[int] = None,
        remark: Optional[str] = None,
        reset_failures: bool = False,
    ) -> bool:
        fields = []
        params: Dict[str, Any] = {"id": int(item_id)}
        if cookies is not None:
            fields.append("cookies = :cookies")
            params["cookies"] = cookies
        if status is not None:
            fields.append("status = :status")
            params["status"] = int(status)
        if priority is not None:
            fields.append("priority = :priority")
            params["priority"] = int(priority)
        if remark is not None:
            fields.append("remark = :remark")
            params["remark"] = remark
        if reset_failures:
            fields.append("fail_count = 0")
            fields.append("cooldown_until = NULL")

        if not fields:
            return True

        sql = f"UPDATE platform_cookie_pool SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
        async with get_async_session() as session:
            result = await session.execute(text(sql), params)
            return (result.rowcount or 0) > 0

    async def delete(self, item_id: int) -> bool:
        async with get_async_session() as session:
            result = await session.execute(
                text("DELETE FROM platform_cookie_pool WHERE id = :id"),
                {"id": int(item_id)},
            )
            return (result.rowcount or 0) > 0


cookies_pool_admin_service = CookiesPoolAdminService()

