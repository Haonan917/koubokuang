# -*- coding: utf-8 -*-
from typing import Optional

from abs.abs_api_client import AbstractApiClient
from models.base_model import PlatformEnum
from pkg.media_platform_api.media_platform_api import \
    create_media_platform_client
import config as app_config
from pkg.cookies_pool import cookies_account_pool


class BaseLogic:
    def __init__(self, platform: PlatformEnum, cookies: str = ""):
        """
        base logic constructor

        Args:
            platform: platform enum
            cookies: cookies
        """
        self.platform = platform
        self.cookies = cookies
        self.api_client: Optional[AbstractApiClient] = None
        self._cookies_account_id: Optional[int] = None

    async def async_initialize(self, **kwargs):
        """
        async initialize

        Returns:

        """
        # Determine cookies source
        cookies = self.cookies or ""
        if app_config.FORCE_COOKIES_FROM_DB or not cookies:
            account = await cookies_account_pool.get_one(self.platform)
            if not account:
                raise RuntimeError(f"no cookies account available for platform={self.platform.value}")
            cookies = account.cookies
            self._cookies_account_id = account.id

        max_tries = max(1, int(getattr(app_config, "COOKIES_POOL_MAX_TRIES", 3)))
        last_err: Optional[Exception] = None
        for _ in range(max_tries):
            self.api_client = await create_media_platform_client(
                self.platform, cookies, **kwargs
            )
            if not getattr(app_config, "CHECK_COOKIES_ON_INIT", True):
                self.cookies = cookies
                return
            try:
                ok = await self.api_client.pong()
            except Exception as e:
                ok = False
                last_err = e
            if ok:
                self.cookies = cookies
                return

            # invalid cookie -> mark and retry with another one
            if self._cookies_account_id:
                await cookies_account_pool.mark_invalid(
                    self._cookies_account_id,
                    reason=f"pong invalid: {last_err}" if last_err else "pong invalid",
                )
            account = await cookies_account_pool.get_one(self.platform)
            if not account:
                break
            cookies = account.cookies
            self._cookies_account_id = account.id

        raise RuntimeError(f"no valid cookies for platform={self.platform.value}")

    async def check_cookies(self) -> bool:
        """
        check cookies is valid

        Returns:
            bool: is valid
        """
        return await self.api_client.pong()
