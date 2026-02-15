# -*- coding: utf-8 -*-
import re
from typing import Dict, List

import httpx
from pydantic import BaseModel, Field

import config
from pkg.proxy import IpCache, IpInfoModel, ProxyProvider
from pkg.proxy.types import ProviderNameEnum
from pkg.tools import utils

DELTA_EXPIRED_SECOND = 5


class KuaidailiProxyModel(BaseModel):
    ip: str = Field("ip")
    port: int = Field("port")
    expire_ts: int = Field("expire ts")


def parse_kuaidaili_proxy(proxy_info: str) -> KuaidailiProxyModel:
    pattern = r"(\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5}),(\d+)"
    match = re.search(pattern, proxy_info)
    if not match:
        raise ValueError("invalid kuaidaili proxy info")
    return KuaidailiProxyModel(
        ip=match.group(1),
        port=int(match.group(2)),
        expire_ts=int(match.group(3)),
    )


class KuaiDaiLiProxy(ProxyProvider):
    def __init__(
        self, kdl_user_name: str, kdl_user_pwd: str, kdl_secret_id: str, kdl_signature: str
    ):
        self.kdl_user_name = kdl_user_name
        self.kdl_user_pwd = kdl_user_pwd
        self.api_base = "https://dps.kdlapi.com/"
        self.secret_id = kdl_secret_id
        self.signature = kdl_signature
        self.ip_cache = IpCache()
        self.proxy_brand_name = ProviderNameEnum.KUAI_DAILI_PROVIDER.value
        self.params = {
            "secret_id": self.secret_id,
            "signature": self.signature,
            "pt": 1,
            "format": "json",
            "sep": 1,
            "f_et": 1,
        }

    async def get_proxies(self, num: int) -> List[IpInfoModel]:
        if not all([self.kdl_user_name, self.kdl_user_pwd, self.secret_id, self.signature]):
            raise RuntimeError("kuaidaili credentials missing, please configure KDL_* env vars")

        uri = "/api/getdps/"
        ip_cache_list = self.ip_cache.load_all_ip(proxy_brand_name=self.proxy_brand_name)
        if len(ip_cache_list) >= num:
            return ip_cache_list[:num]

        need_get_count = num - len(ip_cache_list)
        self.params.update({"num": need_get_count})

        ip_infos: List[IpInfoModel] = []
        async with httpx.AsyncClient() as client:
            response = await client.get(self.api_base + uri, params=self.params)
            if response.status_code != 200:
                raise RuntimeError(
                    f"get ip error from provider, status={response.status_code}, body={response.text}"
                )

            ip_response: Dict = response.json()
            if ip_response.get("code") != 0:
                raise RuntimeError(
                    f"get ip error from provider, code={ip_response.get('code')}, msg={ip_response.get('msg')}"
                )

            proxy_list: List[str] = ip_response.get("data", {}).get("proxy_list", [])
            for proxy in proxy_list:
                proxy_model = parse_kuaidaili_proxy(proxy)
                ip_info_model = IpInfoModel(
                    ip=proxy_model.ip,
                    port=proxy_model.port,
                    user=self.kdl_user_name,
                    password=self.kdl_user_pwd,
                    expired_time_ts=proxy_model.expire_ts + utils.get_unix_timestamp() - DELTA_EXPIRED_SECOND,
                )
                ip_key = f"{self.proxy_brand_name}_{ip_info_model.ip}_{ip_info_model.port}"
                self.ip_cache.set_ip(
                    ip_key,
                    ip_info_model.model_dump_json(),
                    ex=max(1, proxy_model.expire_ts - DELTA_EXPIRED_SECOND),
                )
                ip_infos.append(ip_info_model)

        return ip_cache_list + ip_infos

    def mark_ip_invalid(self, ip_info: IpInfoModel) -> None:
        ip_key = f"{self.proxy_brand_name}_{ip_info.ip}_{ip_info.port}"
        self.ip_cache.delete_ip(ip_key)


def new_kuai_daili_proxy() -> KuaiDaiLiProxy:
    return KuaiDaiLiProxy(
        kdl_secret_id=config.KDL_SECERT_ID,
        kdl_signature=config.KDL_SIGNATURE,
        kdl_user_name=config.KDL_USER_NAME,
        kdl_user_pwd=config.KDL_USER_PWD,
    )
