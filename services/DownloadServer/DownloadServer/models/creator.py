# -*- coding: utf-8 -*-
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from models.base_model import PlatformEnum
from models.content_detail import Content


class CreatorQueryRequest(BaseModel):
    """
    查询创作者主页请求
    """

    platform: PlatformEnum = Field(..., title="平台", description="平台")
    creator_url: str = Field(..., title="链接", description="链接")
    cookies: str = Field(
        ..., title="登录成功后的cookies", description="登录成功后的cookies"
    )
    creator_id: Optional[str] = Field(
        default="", title="创作者ID", description="创作者ID"
    )


class CreatorQueryResponse(BaseModel):
    """
    查询创作者主页响应
    """

    nickname: str = Field(..., title="昵称", description="昵称")
    avatar: str = Field(default="", title="头像", description="头像")
    description: str = Field(default="", title="描述", description="描述")
    user_id: str = Field(default="", title="用户ID", description="用户ID")
    follower_count: str = Field(default="", title="粉丝数", description="粉丝数")
    following_count: str = Field(default="", title="关注数", description="关注数")
    content_count: str = Field(default="", title="作品数", description="作品数")


class CreatorContentListRequest(BaseModel):
    """
    查询创作者内容列表请求
    """

    platform: PlatformEnum = Field(..., title="平台", description="平台")
    creator_id: str = Field(..., title="创作者ID", description="创作者ID")
    cursor: str = Field(default="", title="分页查询游标", description="分页查询游标")
    cookies: str = Field(
        ..., title="登录成功后的cookies", description="登录成功后的cookies"
    )


class CreatorContentListResponse(BaseModel):
    """
    创作者内容列表响应
    """

    contents: List[Content] = Field(..., title="内容列表", description="内容列表")
    has_more: bool = Field(..., title="是否还有更多", description="是否还有更多")
    next_cursor: str = Field(default="", title="下一页游标", description="下一页游标")
