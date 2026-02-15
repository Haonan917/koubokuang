# -*- coding: utf-8 -*-
import json
from abc import ABC, abstractmethod
from typing import List

import config
from pkg.cache.abs_cache import AbstractCache
from pkg.cache.cache_factory import CacheFactory
from pkg.proxy.types import IpInfoModel
from pkg.tools import utils


class ProxyProvider(ABC):
    @abstractmethod
    async def get_proxies(self, num: int) -> List[IpInfoModel]:
        pass

    @abstractmethod
    def mark_ip_invalid(self, ip: IpInfoModel) -> None:
        pass


class IpCache:
    def __init__(self):
        self.cache_client: AbstractCache = CacheFactory.create_cache(
            cache_type=config.USE_CACHE_TYPE
        )

    def set_ip(self, ip_key: str, ip_value_info: str, ex: int):
        self.cache_client.set(key=ip_key, value=ip_value_info, expire_time=ex)

    def delete_ip(self, ip_key: str):
        self.cache_client.delete(ip_key)

    def load_all_ip(self, proxy_brand_name: str) -> List[IpInfoModel]:
        all_ip_list: List[IpInfoModel] = []
        all_ip_keys: List[str] = self.cache_client.keys(pattern=f"{proxy_brand_name}_*")
        try:
            for ip_key in all_ip_keys:
                ip_value = self.cache_client.get(ip_key)
                if not ip_value:
                    continue
                ip_info_model = IpInfoModel(**json.loads(ip_value))
                ttl = self.cache_client.ttl(ip_key)
                if ttl > 0:
                    ip_info_model.expired_time_ts = utils.get_unix_timestamp() + ttl
                    all_ip_list.append(ip_info_model)
        except Exception as e:
            utils.logger.error(f"[IpCache.load_all_ip] get ip err from cache: {e}")
            raise
        return all_ip_list
