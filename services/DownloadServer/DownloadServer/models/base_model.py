# -*- coding: utf-8 -*-

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class PlatformEnum(Enum):
    XHS = "xhs"
    DOUYIN = "dy"
    KUAISHOU = "ks"
    BILIBILI = "bili"


class ContentTypeEnum(Enum):
    VIDEO = "video"
    NOTE = "note"


class OkResponseModel(BaseModel):
    biz_code: int = 0
    msg: str = "OK!"
    isok: bool = True
    data: Optional[Any] = None


class ErrorResponseModel(BaseModel):
    biz_code: int
    msg: str
    isok: bool = False
    extra: Optional[Any] = None
