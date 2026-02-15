# -*- coding: utf-8 -*-
import asyncio
import random
from typing import Dict, List

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

import config
from pkg.proxy.providers import new_kuai_daili_proxy
from pkg.tools import utils
from pkg.httpx_compat import new_async_client

from .base_proxy import ProxyProvider
from .types import IpInfoModel, ProviderNameEnum


class ProxyIpPool:
    def __init__(self, ip_pool_count: int, enable_validate_ip: bool, ip_provider: ProxyProvider) -> None:
        self.valid_ip_url = "https://echo.apifox.cn/"
        self.ip_pool_count = ip_pool_count
        self.enable_validate_ip = enable_validate_ip
        self.proxy_list: List[IpInfoModel] = []
        self.ip_provider: ProxyProvider = ip_provider
        self._lock = asyncio.Lock()

    async def load_proxies(self) -> None:
        self.proxy_list = await self.ip_provider.get_proxies(self.ip_pool_count)

    async def _is_valid_proxy(self, proxy: IpInfoModel) -> bool:
        utils.logger.info(f"[ProxyIpPool._is_valid_proxy] testing {proxy.ip}:{proxy.port}")
        try:
            async with new_async_client(proxy=proxy.format_httpx_proxy()) as client:
                response = await client.get(self.valid_ip_url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            utils.logger.info(f"[ProxyIpPool._is_valid_proxy] invalid proxy {proxy.ip}:{proxy.port}, err={e}")
            return False

    async def mark_ip_invalid(self, proxy: IpInfoModel):
        utils.logger.info(f"[ProxyIpPool.mark_ip_invalid] mark {proxy.ip}:{proxy.port} invalid")
        self.ip_provider.mark_ip_invalid(proxy)
        self.proxy_list = [
            p for p in self.proxy_list
            if not (
                p.ip == proxy.ip
                and p.port == proxy.port
                and p.protocol == proxy.protocol
                and p.user == proxy.user
                and p.password == proxy.password
            )
        ]

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_proxy(self) -> IpInfoModel:
        async with self._lock:
            if len(self.proxy_list) == 0:
                await self._reload_proxies()

            proxy = random.choice(self.proxy_list)
            self.proxy_list.remove(proxy)

        if self.enable_validate_ip and not await self._is_valid_proxy(proxy):
            await self.mark_ip_invalid(proxy)
            raise RuntimeError("proxy invalid, retrying")
        return proxy

    async def _reload_proxies(self):
        self.proxy_list = []
        await self.load_proxies()


IpProxyProvider: Dict[str, ProxyProvider] = {
    ProviderNameEnum.KUAI_DAILI_PROVIDER.value: new_kuai_daili_proxy()
}


async def create_ip_pool(
    ip_pool_count: int,
    enable_validate_ip: bool,
    ip_provider=config.IP_PROXY_PROVIDER_NAME,
) -> ProxyIpPool:
    provider = IpProxyProvider.get(ip_provider)
    if provider is None:
        raise ValueError(f"unsupported ip provider: {ip_provider}")
    pool = ProxyIpPool(
        ip_pool_count=ip_pool_count,
        enable_validate_ip=enable_validate_ip,
        ip_provider=provider,
    )
    await pool.load_proxies()
    return pool
