# -*- coding: utf-8 -*-
import os


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


# 是否开启 IP 代理
ENABLE_IP_PROXY = _as_bool(os.getenv("ENABLE_IP_PROXY", "false"), default=False)

# 代理IP池数量
IP_PROXY_POOL_COUNT = int(os.getenv("IP_PROXY_POOL_COUNT", 4))

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = os.getenv("IP_PROXY_PROVIDER_NAME", "kuaidaili")

# 快代理配置
KDL_SECERT_ID = os.getenv("KDL_SECERT_ID", "")
KDL_SIGNATURE = os.getenv("KDL_SIGNATURE", "")
KDL_USER_NAME = os.getenv("KDL_USER_NAME", "")
KDL_USER_PWD = os.getenv("KDL_USER_PWD", "")
