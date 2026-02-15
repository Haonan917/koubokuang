# -*- coding: utf-8 -*-
"""
启动期引导服务（Bootstrap）

当前用途：
- 可选地创建/更新默认管理员账号（开发环境）
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from config import settings
from db.base import get_async_session
from services.auth_service import auth_service, UserStatus
from utils.logger import logger


def _build_admin_email() -> str:
    username = (getattr(settings, "BOOTSTRAP_ADMIN_USERNAME", None) or "admin").strip()
    domain = (getattr(settings, "BOOTSTRAP_ADMIN_EMAIL_DOMAIN", None) or "local").strip().lstrip("@")
    if "@" in username:
        return username.lower()
    return f"{username}@{domain}".lower()


class BootstrapService:
    async def bootstrap_default_admin(self) -> None:
        if not getattr(settings, "BOOTSTRAP_ADMIN_ENABLED", False):
            return

        email = _build_admin_email()
        # 兼容历史默认域名 "local"（无 TLD，可能无法通过 EmailStr 校验）
        username = (getattr(settings, "BOOTSTRAP_ADMIN_USERNAME", None) or "admin").strip()
        legacy_email_candidates = []
        if "@" not in username:
          legacy_email_candidates.append(f"{username}@local".lower())
          legacy_email_candidates.append(f"{username}@local.test".lower())
        password = getattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", None) or "123456"
        force_password = bool(getattr(settings, "BOOTSTRAP_ADMIN_FORCE_PASSWORD", True))

        try:
            # 如果存在 legacy_email 且新 email 不存在，则迁移 email（避免管理员登不进去）
            for legacy_email in legacy_email_candidates:
                if legacy_email == email:
                    continue
                legacy = await auth_service.get_user_by_email(legacy_email)
                current = await auth_service.get_user_by_email(email)
                if legacy and not current:
                    async with get_async_session() as session:
                        await session.execute(
                            text("UPDATE users SET email = :new_email WHERE email = :old_email"),
                            {"new_email": email, "old_email": legacy_email},
                        )
                    logger.info(f"[Bootstrap] migrated legacy admin email: {legacy_email} -> {email}")
                    break

            user_row = await auth_service.get_user_by_email(email)
            if not user_row:
                user = await auth_service.create_user(
                    email=email,
                    password=password,
                    display_name="admin",
                    status=UserStatus.ACTIVE,
                    email_verified=True,
                )
                user_id = user.user_id
                logger.info(f"[Bootstrap] default admin created: {email}")
            else:
                user_id = str(user_row.get("user_id"))
                if force_password:
                    await auth_service.update_password(user_id, password)
                logger.info(f"[Bootstrap] default admin exists: {email} (updated={force_password})")

            # Ensure admin flag + active status + verified
            now = datetime.now(timezone.utc)
            async with get_async_session() as session:
                await session.execute(
                    text(
                        """
                        UPDATE users
                        SET is_admin = 1,
                            status = :status,
                            email_verified_at = COALESCE(email_verified_at, :now)
                        WHERE user_id = :user_id
                        """
                    ),
                    {"status": UserStatus.ACTIVE, "now": now, "user_id": user_id},
                )
        except Exception as e:
            # 不阻塞主流程：bootstrap 失败只记日志
            logger.warning(f"[Bootstrap] bootstrap_default_admin failed: {e}")


bootstrap_service = BootstrapService()
