# -*- coding: utf-8 -*-
"""
设置/取消管理员权限

用法:
  uv run python scripts/set_admin.py user@example.com
  uv run python scripts/set_admin.py user@example.com --unset
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from db.base import get_async_session


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("email", help="用户邮箱")
    parser.add_argument("--unset", action="store_true", help="取消管理员权限")
    args = parser.parse_args()

    email = (args.email or "").strip().lower()
    if not email:
        raise SystemExit(2)

    is_admin = 0 if args.unset else 1
    async with get_async_session() as session:
        result = await session.execute(
            text("UPDATE users SET is_admin = :is_admin WHERE email = :email"),
            {"is_admin": is_admin, "email": email},
        )
        if (result.rowcount or 0) <= 0:
            print(f"User not found: {email}")
            return 1

    print(f"OK: {email} is_admin={is_admin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

