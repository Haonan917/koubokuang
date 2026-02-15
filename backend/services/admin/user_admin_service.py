# -*- coding: utf-8 -*-
"""
用户管理服务（管理员）
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any

from sqlalchemy import text

from db.base import get_async_session


class UserAdminService:
    async def list(self, q: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        where = ["1=1"]
        params: Dict[str, Any] = {"limit": int(limit), "offset": int(offset)}
        if q:
            where.append("(email LIKE :q OR display_name LIKE :q)")
            params["q"] = f"%{q}%"

        sql = f"""
            SELECT user_id, email, display_name, status, COALESCE(is_admin, 0) AS is_admin, created_at, updated_at
            FROM users
            WHERE {" AND ".join(where)}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """
        async with get_async_session() as session:
            result = await session.execute(text(sql), params)
            return [dict(r) for r in result.mappings().all()]

    async def update(self, user_id: str, status: Optional[int] = None, is_admin: Optional[int] = None) -> bool:
        fields = []
        params: Dict[str, Any] = {"user_id": user_id}
        if status is not None:
            fields.append("status = :status")
            params["status"] = int(status)
        if is_admin is not None:
            fields.append("is_admin = :is_admin")
            params["is_admin"] = int(is_admin)

        if not fields:
            return True

        sql = f"UPDATE users SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP(6) WHERE user_id = :user_id"
        async with get_async_session() as session:
            result = await session.execute(text(sql), params)
            return (result.rowcount or 0) > 0


user_admin_service = UserAdminService()

