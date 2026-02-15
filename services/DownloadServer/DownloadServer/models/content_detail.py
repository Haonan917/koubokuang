from typing import List, Optional, Dict

from pydantic import BaseModel, Field

from models.base_model import ContentTypeEnum, PlatformEnum


class AuthorInfo(BaseModel):
    """
    作者信息模型
    """

    user_id: str = Field(default="", title="作者ID", description="作者用户ID")
    sec_uid: str = Field(
        default="", title="加密用户ID", description="抖音特有，用于生成主页链接"
    )
    nickname: str = Field(default="", title="作者昵称", description="作者昵称")
    avatar: str = Field(default="", title="作者头像", description="作者头像URL")
    profile_url: str = Field(default="", title="作者主页", description="作者主页链接")


class InteractionInfo(BaseModel):
    """
    互动数据模型
    """

    liked_count: str = Field(default="", title="点赞数", description="点赞数")
    collected_count: str = Field(
        default="", title="收藏数", description="收藏数 (B站、快手无此字段)"
    )
    comment_count: str = Field(
        default="", title="评论数", description="评论数 (快手无此字段)"
    )
    share_count: str = Field(
        default="", title="分享数", description="分享数 (B站、快手无此字段)"
    )
    play_count: str = Field(
        default="", title="播放数", description="播放数 (B站、快手有)"
    )
    danmaku_count: str = Field(
        default="", title="弹幕数", description="弹幕数 (B站特有)"
    )


class Content(BaseModel):
    """
    内容
    """

    id: str = Field(title="内容ID", description="内容ID")
    url: str = Field(title="内容URL", description="内容URL")
    title: str = Field(title="内容标题", description="内容标题")
    desc: str = Field(default="", title="内容描述", description="内容描述/正文")
    content_type: ContentTypeEnum = Field(title="内容类型", description="内容类型")
    cover_url: str = Field(title="封面URL", description="封面URL")
    image_urls: Optional[List[str]] = Field(
        title="图片URL列表", description="图片URL列表"
    )
    video_download_url: str = Field(title="视频下载URL", description="视频下载URL")
    extria_info: Optional[Dict] = Field(
        title="额外信息", default=None, description="存放视频额外的信息"
    )
    author: Optional[AuthorInfo] = Field(
        title="作者信息", default=None, description="作者信息"
    )
    interaction: Optional[InteractionInfo] = Field(
        title="互动数据", default=None, description="互动数据"
    )


class ContentDetailRequest(BaseModel):
    """
    内容详情请求
    """

    platform: PlatformEnum = Field(..., title="平台", description="平台")
    content_url: str = Field(..., title="内容URL", description="内容URL")
    cookies: Optional[str] = Field(
        default=None, title="登录成功后的cookies", description="(deprecated) cookies 将从 DB 账号池自动选择"
    )


class ContentDetailResponse(BaseModel):
    """
    内容详情响应
    """

    content: Content = Field(..., title="内容", description="内容")
