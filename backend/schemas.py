# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/schemas.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""
数据模型定义 - Pydantic Schemas

包含:
- 平台和内容类型枚举
- 爬虫响应模型
- 分析结果模型
- 灵感生成模型
- 完整学习结果模型
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ========== 枚举类型 ==========

class Platform(str, Enum):
    """支持的平台"""
    XHS = "xhs"
    DOUYIN = "dy"
    BILIBILI = "bilibili"
    KUAISHOU = "ks"


class ContentType(str, Enum):
    """内容类型"""
    VIDEO = "video"
    IMAGE = "image"
    MIXED = "mixed"


class InsightMode(str, Enum):
    """灵感学习模式"""
    SUMMARIZE = "summarize"       # 精华提炼
    ANALYZE = "analyze"           # 深度拆解
    TEMPLATE = "template"         # 模板学习 (原 imitate)
    STYLE_EXPLORE = "style_explore"  # 风格探索 (原 rewrite)


# ========== 链接解析模型 ==========

class ParsedLinkInfo(BaseModel):
    """链接解析结果"""
    platform: str        # 平台标识 (xhs/dy/bilibili/ks)
    content_id: str      # 内容 ID
    original_url: str    # 原始链接
    is_short_link: bool = False  # 是否为短链接


# ========== 爬虫响应模型 ==========

class ContentParseResponse(BaseModel):
    """内容解析响应 - MediaCrawlerPro API 返回"""
    platform: Platform
    content_id: str
    content_type: ContentType

    # 基本信息
    title: str = ""
    desc: str = ""
    author_id: str = ""
    author_name: str = ""
    author_avatar: str = ""

    # 媒体资源（远程 URL）
    cover_url: str = ""
    video_url: Optional[str] = None      # 视频下载链接（可能不含音频，如B站）
    audio_url: Optional[str] = None      # 音频下载链接（用于 ASR，B站单独提供）
    image_urls: List[str] = Field(default_factory=list)

    # 本地资源路径（用于前端展示，避免跨域）
    local_cover_url: Optional[str] = None   # /assets/{platform}/{content_id}/cover.jpg
    local_video_url: Optional[str] = None   # /assets/{platform}/{content_id}/video.mp4

    # 互动数据
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    collect_count: int = 0
    view_count: int = 0      # 播放量（视频特有）
    danmaku_count: int = 0   # 弹幕数（B站特有）

    # 元数据
    duration: int = 0        # 视频时长（秒）
    publish_time: int = 0    # 毫秒时间戳
    tags: List[str] = Field(default_factory=list)


# ========== 分析结果模型 ==========

class ContentStructure(BaseModel):
    """内容结构"""
    section: str           # 段落名称
    time_range: Optional[str] = None  # 时间范围（视频）
    description: str       # 内容描述
    technique: Optional[str] = None   # 使用的技巧


class ViralElement(BaseModel):
    """爆款元素"""
    element: str          # 元素名称
    present: bool         # 是否存在
    description: str = ""  # 具体说明


class ContentAnalysisResult(BaseModel):
    """内容分析结果"""
    summary: str                         # 内容摘要
    structures: List[ContentStructure] = Field(default_factory=list)  # 结构拆解
    viral_elements: List[ViralElement] = Field(default_factory=list)  # 爆款元素
    takeaways: List[str] = Field(default_factory=list)  # 可借鉴点
    target_audience: str = ""            # 目标受众
    style_tags: List[str] = Field(default_factory=list)  # 风格标签


# ========== 灵感生成模型 ==========

class TitleSuggestion(BaseModel):
    """标题灵感"""
    style: str   # 类型（数字型/悬念型/痛点型等）
    title: str   # 标题内容


class HookSuggestion(BaseModel):
    """开头灵感"""
    style: str    # 类型（反问式/故事式/数据式等）
    content: str  # 钩子内容


class CopywritingResult(BaseModel):
    """创意灵感结果"""
    mode: InsightMode = InsightMode.ANALYZE
    titles: List[TitleSuggestion] = Field(default_factory=list)    # 标题灵感
    hooks: List[HookSuggestion] = Field(default_factory=list)      # 开头灵感
    framework: str = ""                    # 结构框架
    inspiration: str = ""                  # 创意灵感 (原 full_copy)


# ========== ASR 模型 ==========

class Segment(BaseModel):
    """语音分段"""
    start: float  # 开始时间（秒）
    end: float    # 结束时间（秒）
    text: str     # 文本内容


class TranscriptResult(BaseModel):
    """转录结果"""
    text: str              # 完整文本
    segments: List[Segment] = Field(default_factory=list)  # 分段信息
    content_id: Optional[str] = Field(None, description="关联的内容ID（用于缓存验证）")


# ========== 完整结果模型 ==========

class RemixResult(BaseModel):
    """完整学习结果"""
    content_info: ContentParseResponse
    transcript: Optional[str] = None
    analysis: Optional[ContentAnalysisResult] = None
    copywriting: Optional[CopywritingResult] = None  # 创意灵感
    process_time_ms: int = 0


# ========== 对话模型 ==========

class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # "user" 或 "assistant"
    content: str


# ========== Cookies 管理模型 ==========

class CookiesUpdateRequest(BaseModel):
    """Cookies 更新请求"""
    cookies: str = Field(..., description="Cookie 字符串")
    remark: Optional[str] = Field(None, description="备注")


class CookiesInfo(BaseModel):
    """Cookies 信息（不含 cookies 明文）"""
    platform: str = Field(..., description="平台标识: xhs/dy/bili/ks")
    status: int = Field(..., description="状态: 0=有效, 1=过期, 2=禁用")
    remark: Optional[str] = Field(None, description="备注")
    updated_at: str = Field(..., description="更新时间 (ISO 格式)")


class CookiesDetail(BaseModel):
    """Cookies 详情（含 cookies 明文，仅用于编辑）"""
    platform: str = Field(..., description="平台标识: xhs/dy/bili/ks")
    cookies: str = Field(..., description="Cookie 字符串")
    status: int = Field(..., description="状态: 0=有效, 1=过期, 2=禁用")
    remark: Optional[str] = Field(None, description="备注")
    updated_at: str = Field(..., description="更新时间 (ISO 格式)")


class CookiesListResponse(BaseModel):
    """Cookies 列表响应"""
    items: List[CookiesInfo] = Field(default_factory=list)


# ========== LLM 配置管理模型 (简化版) ==========

class LLMProvider(str, Enum):
    """LLM 提供商"""
    OPENAI = "openai"           # OpenAI 兼容 API (包含 Kimi, MiniMax 等)
    ANTHROPIC = "anthropic"     # Anthropic Claude
    DEEPSEEK = "deepseek"       # DeepSeek
    OLLAMA = "ollama"           # 本地 Ollama


class LLMConfigCreateRequest(BaseModel):
    """LLM 配置创建请求"""
    config_name: str = Field(..., description="配置名称", min_length=1, max_length=50)
    provider: LLMProvider = Field(..., description="提供商")

    # 核心配置
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, description="API 基础 URL")
    model_name: str = Field(..., description="模型名称")

    # 思考/推理配置 (仅部分模型需要)
    enable_thinking: bool = Field(False, description="启用思考模式")
    thinking_budget_tokens: int = Field(4096, ge=1024, le=32000, description="Anthropic 思考预算")
    reasoning_effort: str = Field("high", description="OpenAI 推理强度 (none/low/medium/high/xhigh)")

    # 多模态配置
    support_multimodal: bool = Field(False, description="是否支持多模态（图片理解）")

    # 元数据
    description: Optional[str] = Field(None, max_length=255, description="配置描述")


class LLMConfigUpdateRequest(BaseModel):
    """LLM 配置更新请求（部分字段可选）"""
    provider: Optional[LLMProvider] = Field(None, description="提供商")

    # 核心配置
    api_key: Optional[str] = Field(None, description="API Key (空字符串清除)")
    base_url: Optional[str] = Field(None, description="API 基础 URL")
    model_name: Optional[str] = Field(None, description="模型名称")

    # 思考/推理配置
    enable_thinking: Optional[bool] = Field(None, description="启用思考模式")
    thinking_budget_tokens: Optional[int] = Field(None, ge=1024, le=32000, description="Anthropic 思考预算")
    reasoning_effort: Optional[str] = Field(None, description="OpenAI 推理强度")

    # 多模态配置
    support_multimodal: Optional[bool] = Field(None, description="是否支持多模态")

    # 元数据
    description: Optional[str] = Field(None, max_length=255, description="配置描述")


class LLMConfigInfo(BaseModel):
    """LLM 配置信息（不含 API Key 明文）"""
    config_name: str = Field(..., description="配置名称")
    provider: str = Field(..., description="提供商")
    is_active: bool = Field(False, description="是否为当前激活配置")

    # 核心配置（脱敏显示）
    has_api_key: bool = Field(False, description="是否已配置 API Key")
    base_url: Optional[str] = Field(None, description="API 基础 URL")
    model_name: str = Field(..., description="模型名称")

    # 思考/推理配置
    enable_thinking: bool = Field(False, description="启用思考模式")
    thinking_budget_tokens: int = Field(4096, description="Anthropic 思考预算")
    reasoning_effort: str = Field("high", description="OpenAI 推理强度")

    # 多模态配置
    support_multimodal: bool = Field(False, description="是否支持多模态")

    # 元数据
    description: Optional[str] = Field(None, description="配置描述")
    updated_at: str = Field(..., description="更新时间 (ISO 格式)")


class LLMConfigListResponse(BaseModel):
    """LLM 配置列表响应"""
    items: List[LLMConfigInfo] = Field(default_factory=list)
    active_config: Optional[str] = Field(None, description="当前激活的配置名称")


# ========== Insight Mode 配置管理模型 ==========

class InsightModeCreateRequest(BaseModel):
    """Insight Mode 创建请求"""
    mode_key: str = Field(..., description="模式标识", min_length=1, max_length=50)

    # 显示信息
    label_zh: str = Field(..., description="中文名称", min_length=1, max_length=100)
    label_en: str = Field(..., description="英文名称", min_length=1, max_length=100)
    description_zh: Optional[str] = Field(None, max_length=500, description="中文描述")
    description_en: Optional[str] = Field(None, max_length=500, description="英文描述")
    prefill_zh: Optional[str] = Field(None, max_length=200, description="中文输入预填充")
    prefill_en: Optional[str] = Field(None, max_length=200, description="英文输入预填充")

    # 视觉配置
    icon: str = Field(default="smart_toy", max_length=50, description="Material Symbols 图标名")
    color: str = Field(default="cyan", max_length=20, description="颜色主题 (cyan/orange/pink/purple)")

    # 意图识别关键词
    keywords_zh: Optional[str] = Field(None, description="中文关键词 (逗号分隔)")
    keywords_en: Optional[str] = Field(None, description="英文关键词 (逗号分隔)")

    # System Prompt
    system_prompt: str = Field(..., description="模式专属提示词")


class InsightModeUpdateRequest(BaseModel):
    """Insight Mode 更新请求（所有字段可选）"""
    # 显示信息
    label_zh: Optional[str] = Field(None, max_length=100, description="中文名称")
    label_en: Optional[str] = Field(None, max_length=100, description="英文名称")
    description_zh: Optional[str] = Field(None, max_length=500, description="中文描述")
    description_en: Optional[str] = Field(None, max_length=500, description="英文描述")
    prefill_zh: Optional[str] = Field(None, max_length=200, description="中文输入预填充")
    prefill_en: Optional[str] = Field(None, max_length=200, description="英文输入预填充")

    # 视觉配置
    icon: Optional[str] = Field(None, max_length=50, description="Material Symbols 图标名")
    color: Optional[str] = Field(None, max_length=20, description="颜色主题")

    # 意图识别关键词
    keywords_zh: Optional[str] = Field(None, description="中文关键词 (逗号分隔)")
    keywords_en: Optional[str] = Field(None, description="英文关键词 (逗号分隔)")

    # System Prompt
    system_prompt: Optional[str] = Field(None, description="模式专属提示词")


class InsightModeInfo(BaseModel):
    """Insight Mode 列表项（不含 system_prompt）"""
    mode_key: str = Field(..., description="模式标识")
    is_active: bool = Field(True, description="是否启用")
    sort_order: int = Field(0, description="显示排序")

    # 显示信息
    label_zh: str = Field(..., description="中文名称")
    label_en: str = Field(..., description="英文名称")
    description_zh: Optional[str] = Field(None, description="中文描述")
    description_en: Optional[str] = Field(None, description="英文描述")
    prefill_zh: Optional[str] = Field(None, description="中文输入预填充")
    prefill_en: Optional[str] = Field(None, description="英文输入预填充")

    # 视觉配置
    icon: str = Field(default="smart_toy", description="图标名")
    color: str = Field(default="cyan", description="颜色主题")

    # 意图识别关键词
    keywords_zh: Optional[str] = Field(None, description="中文关键词")
    keywords_en: Optional[str] = Field(None, description="英文关键词")

    # 系统标记
    is_system: bool = Field(False, description="是否系统内置（不可删除）")

    # 时间戳
    updated_at: str = Field(..., description="更新时间 (ISO 格式)")


class InsightModeDetail(InsightModeInfo):
    """Insight Mode 详情（含 system_prompt）"""
    system_prompt: str = Field(..., description="模式专属提示词")


class InsightModeListResponse(BaseModel):
    """Insight Mode 列表响应"""
    items: List[InsightModeInfo] = Field(default_factory=list)


class InsightModeReorderRequest(BaseModel):
    """Insight Mode 排序请求"""
    mode_keys: List[str] = Field(..., description="按顺序排列的 mode_key 列表")
