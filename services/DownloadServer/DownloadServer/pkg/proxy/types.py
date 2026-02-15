# -*- coding: utf-8 -*-
import time
from enum import Enum

from pydantic import BaseModel, Field


class ProviderNameEnum(Enum):
    KUAI_DAILI_PROVIDER: str = "kuaidaili"


class IpInfoModel(BaseModel):
    ip: str = Field(title="ip")
    port: int = Field(title="port")
    user: str = Field(title="proxy user")
    protocol: str = Field(default="https://", title="proxy protocol")
    password: str = Field(title="proxy password")
    expired_time_ts: int = Field(title="expired timestamp (seconds)")

    def format_httpx_proxy(self) -> str:
        return f"http://{self.user}:{self.password}@{self.ip}:{self.port}"

    @property
    def is_expired(self) -> bool:
        return self.expired_time_ts < int(time.time())
