# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/config/settings.py
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
全局配置管理 - 使用 Pydantic Settings 管理所有配置项。

支持从环境变量和 .env 文件读取配置。
"""
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取项目根目录的绝对路径 (config/settings.py -> config/ -> backend/ -> project root)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()


class Settings(BaseSettings):
    """Content Remix Agent 配置"""

    # ========== LLM 配置 ==========
    LLM_PROVIDER: str = "openai"  # ollama / openai / anthropic / deepseek
    # 锁定 LLM 配置：禁用前端与数据库配置，仅允许内置/环境配置
    LLM_CONFIG_LOCKED: bool = True
    # 允许用户在对话框选择的模型列表（OpenRouter/OpenAI-compatible）
    LLM_ALLOWED_MODELS: List[str] = [
        "z-ai/glm-5",
        "openai/gpt-5.2",
        "minimax/minimax-m2.5",
        "google/gemini-3-flash-preview",
        "deepseek/deepseek-v3.2",
    ]

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_NAME: str = "qwen3:4b"

    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_BASE_URL: Optional[str] = None
    ANTHROPIC_MODEL_NAME: str = "claude-3-5-sonnet-20241022"

    # OpenAI-compatible
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MODEL_NAME: Optional[str] = None

    # DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL_NAME: str = "deepseek-chat"

    # ========== Thinking/Reasoning 配置 ==========
    ENABLE_THINKING: bool = True  # 是否启用 thinking/reasoning
    THINKING_BUDGET_TOKENS: int = 4096  # Anthropic thinking token 预算
    REASONING_EFFORT: str = "high"  # OpenAI GPT-5 推理强度 (none/low/medium/high/xhigh)
    MINIMAX_MAX_TOKENS: int = 8192  # MiniMax completion 上限（避免长输出被过早截断）

    # ========== 多模态 ==========
    MULTIMODAL_ENABLED: bool = False
    MULTIMODAL_PROVIDER: str = "openai"
    MULTIMODAL_MODEL_NAME: str = "gpt-4o"

    # ========== 多模态图片配置 ==========
    MULTIMODAL_MAX_IMAGES: int = 5           # 最多嵌入图片数量
    MULTIMODAL_MAX_IMAGE_SIZE: int = 2097152 # 单张图片最大 2MB
    MULTIMODAL_COMPRESS_IMAGES: bool = True  # 自动压缩大图
    MULTIMODAL_MAX_DIMENSION: int = 1920     # 压缩后最大边长（像素）

    # ========== DownloadServer API ==========
    DOWNLOAD_SERVER_BASE: str = "http://localhost:8205"
    DOWNLOAD_SERVER_TIMEOUT: int = 60

    # ========== Cookies 管控 ==========
    # 锁定平台 Cookies 配置（仅管理员/内部维护）
    COOKIES_MANAGED_BY_ADMIN: bool = True
    # 平台 Cookies（配置文件优先，数据库兜底）
    PLATFORM_COOKIES_XHS: Optional[str] = None
    PLATFORM_COOKIES_DY: Optional[str] = None
    PLATFORM_COOKIES_BILI: Optional[str] = None
    PLATFORM_COOKIES_KS: Optional[str] = None
    # Cookies 池自动切换策略
    COOKIES_POOL_FAILURE_THRESHOLD: int = 3
    COOKIES_POOL_COOLDOWN_SECONDS: int = 300

    # ========== Crawler DB（media_crawler_pro）==========
    # 用于爬虫服务的数据落库与 cookies 账号池管理
    CRAWLER_DB_HOST: Optional[str] = None
    CRAWLER_DB_PORT: Optional[int] = None
    CRAWLER_DB_USER: Optional[str] = None
    CRAWLER_DB_PASSWORD: Optional[str] = None
    CRAWLER_DB_NAME: str = "media_crawler_pro"

    # ========== Voicv API (Voice Cloning) ==========
    VOICV_BASE_URL: str = "https://api.voicv.com/v1"
    VOICV_API_KEY: Optional[str] = None
    VOICV_TIMEOUT: int = 60
    VOICE_CLONE_DOWNLOAD_TIMEOUT: int = 120
    VOICE_CLONE_MAX_AUDIO_BYTES: int = 10 * 1024 * 1024
    VOICE_CLONE_MAX_SOURCE_BYTES: int = 300 * 1024 * 1024
    VOICE_SOURCE_DEFAULT_CLIP_SECONDS: int = 30
    TTS_AUDIO_SPEED: float = 0.85

    # ========== Sync.so API (Lipsync) ==========
    SYNCSO_BASE_URL: str = "https://api.sync.so/v2"
    SYNCSO_API_KEY: Optional[str] = None
    SYNCSO_TIMEOUT: int = 180

    # ========== Media AI Uploads ==========
    MEDIA_UPLOAD_DIR: str = "./data/assets/uploads"


    # ========== 视频处理 ==========
    VIDEO_TEMP_DIR: str = "./temp/videos"
    VIDEO_DOWNLOAD_TIMEOUT: int = 120
    AUDIO_SAMPLE_RATE: int = 16000

    # ========== ASR 配置 ==========
    # 后端选择: funasr (本地模型) / bcut (B站必剪云端API)
    ASR_BACKEND: str = "bcut"

    # FunASR 本地模型配置
    ASR_MODEL: str = "paraformer-zh"      # 主识别模型
    ASR_VAD_MODEL: str = "fsmn-vad"       # VAD 模型
    ASR_PUNC_MODEL: str = "ct-punc-c"     # 标点模型
    ASR_DEVICE: str = "cpu"               # cuda:0 / cpu / mps
    # Bcut API 配置
    BCUT_POLL_INTERVAL: float = 1.0       # 轮询间隔(秒)
    BCUT_MAX_RETRIES: int = 500           # 最大轮询次数

    # 字幕切分参数
    SEG_MAX_CHARS: int = 20               # 每段最大字符数
    SEG_MAX_SECONDS: float = 6.0          # 每段最大时长(秒)
    SEG_MIN_SECONDS: float = 0.5          # 每段最小时长(秒)
    SEG_GAP_SPLIT: float = 0.6            # 静音间隔阈值(秒)

    # 缓存目录
    ASR_CACHE_DIR: str = "./temp/asr"     # 音频预处理缓存

    # ========== 资源存储 ==========
    # 内置静态资源（fonts, logos）
    STATIC_ASSETS_DIR: str = "./assets"
    # 用户生成资源（封面、视频）
    ASSETS_DIR: str = "./data/assets"      # 用户资源目录（Docker 挂载）
    ASSETS_URL_PREFIX: str = "/media"      # 用户资源 URL 前缀
    DOWNLOAD_COVER: bool = True            # 是否下载封面图
    PERSIST_VIDEO: bool = True             # 是否持久化视频

    # ========== Logo Assets ==========
    LOGO_DIR: str = "./assets/logos"       # Logo 存储目录
    LOGO_TARGET_SIZE: int = 128            # Logo 目标尺寸（像素）
    LOGO_MAX_FILE_SIZE: int = 500_000      # 最大文件大小（500KB）

    # ========== API 服务 ==========
    CORS_ORIGINS: List[str] = [
        "http://localhost:5373",
    ]

    # ========== 日志 ==========
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "pretty"  # pretty / json（生产环境建议 json）

    # ========== LLM 调试配置 ==========
    LLM_DEBUG_LOGGING: bool = False  # 是否启用详细的 LLM 调用日志（请求/响应/token统计）
    LLM_FORCE_DISABLE_REASONING: bool = False  # 强制禁用 reasoning 参数（当 API 不支持时）

    # ========== 开发调试 ==========
    USE_MOCK: bool = False

    # ========== Agent 配置 ==========
    # Agent 最大迭代次数
    AGENT_MAX_ITERATIONS: int = 10

    # Agent 超时时间（秒）
    AGENT_TIMEOUT: int = 300

    # ========== Context 压缩配置 ==========
    # 是否启用自动 context 压缩
    CONTEXT_COMPRESSION_ENABLED: bool = True
    # 触发压缩的阈值（占 context window 的比例，0.85 表示 85%）
    # 主流大模型 context window 已达 128K-200K，设置较高阈值充分利用
    CONTEXT_COMPRESSION_THRESHOLD: float = 0.85
    # 压缩后保留的最近消息对数（1对 = 1个 HumanMessage + 1个 AIMessage）
    CONTEXT_KEEP_RECENT_PAIRS: int = 3
    # 默认 context window 大小（当模型未在 MODEL_CONTEXT_WINDOWS 中配置时使用）
    DEFAULT_CONTEXT_WINDOW: int = 32000
    # 各模型的 context window 配置
    MODEL_CONTEXT_WINDOWS: dict = {
        # Anthropic Claude
        "claude-3-5-sonnet": 200000,
        "claude-sonnet-4": 200000,
        "claude-opus-4": 200000,
        "claude-3-haiku": 200000,
        # OpenAI
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4-turbo": 128000,
        "gpt-5": 256000,
        # DeepSeek
        "deepseek-chat": 64000,
        "deepseek-reasoner": 64000,
        # MiniMax
        "MiniMax-M2": 131072,
        "MiniMax-M1": 131072,
        "MiniMax-M2.1-lightning": 131072,
        # Qwen (Ollama)
        "qwen3:4b": 8192,
        "qwen2.5:7b": 32000,
        "qwen2.5:14b": 32000,
        # Other Ollama models
        "llama3.1:8b": 128000,
        "gemma2:9b": 8192,
    }

    # ========== 标题生成配置 ==========
    # 是否启用智能标题生成
    ENABLE_TITLE_GENERATION: bool = True
    # 标题最大长度
    TITLE_MAX_LENGTH: int = 30

    # ========== Agent Memory 配置 ==========
    # 存储后端选择: memory / mysql / postgres
    MEMORY_BACKEND: str = "memory"

    # MySQL Agent 专用数据库配置 (独立于业务数据库 DB_*)
    AGENT_DB_HOST: Optional[str] = None      # 默认: localhost
    AGENT_DB_PORT: Optional[int] = None      # 默认: 3306
    AGENT_DB_USER: Optional[str] = None      # 默认: root
    AGENT_DB_PASSWORD: Optional[str] = None  # 可选
    AGENT_DB_NAME: str = "remix_agent"       # Agent 专用数据库

    # PostgreSQL Memory (会话持久化，兼容旧配置)
    # 格式: postgresql://user:password@host:port/database
    POSTGRES_URI: Optional[str] = None

    # ========== JWT 认证配置 ==========
    JWT_SECRET_KEY: str = ""  # 必需，用于签名 JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Access Token 有效期 30 分钟
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # Refresh Token 有效期 30 天

    # ========== Admin / 管理后台 ==========
    # 管理后台能力依赖 users.is_admin；首次初始化可用脚本设置
    ADMIN_TOKEN: Optional[str] = None  # 可选：额外的管理访问口令（X-Admin-Token）

    # ========== Bootstrap Admin（开发环境）==========
    # 仅用于快速搭建本地/测试环境，生产环境建议关闭
    BOOTSTRAP_ADMIN_ENABLED: bool = False
    BOOTSTRAP_ADMIN_USERNAME: str = "admin"
    BOOTSTRAP_ADMIN_PASSWORD: str = "123456"
    BOOTSTRAP_ADMIN_EMAIL_DOMAIN: str = "example.com"
    BOOTSTRAP_ADMIN_FORCE_PASSWORD: bool = True

    # ========== Usage & Cost 统计 ==========
    USAGE_LOGGING_ENABLED: bool = True
    API_REQUEST_LOGGING_ENABLED: bool = True
    API_LOG_EXCLUDE_PATH_PREFIXES: List[str] = ["/assets", "/media", "/docs", "/openapi.json", "/favicon.ico"]

    # 模型定价：用于“估算费用”（非账单）
    # 格式示例：
    # {
    #   "openai/gpt-5.2": {"input_per_1m": 5.0, "output_per_1m": 15.0},
    #   "deepseek/deepseek-v3.2": {"input_per_1m": 0.2, "output_per_1m": 0.8}
    # }
    MODEL_PRICING_USD_PER_1M: Dict[str, Dict[str, float]] = {}

    # ========== GitHub OAuth ==========
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_CALLBACK_URL: str = "http://localhost:5373/auth/callback/github"

    # ========== Google OAuth ==========
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_CALLBACK_URL: str = "http://localhost:5373/auth/callback/google"

    # ========== 邮件服务 (SMTP) ==========
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "Remix AI Studio"
    SMTP_USE_TLS: bool = True

    # ========== 前端 URL (用于邮件链接) ==========
    FRONTEND_URL: str = "http://localhost:5373"

    model_config = SettingsConfigDict(
        env_file=(
            str(_PROJECT_ROOT / "config" / "backend.env"),
            str(_PROJECT_ROOT / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略 .env 中未定义的配置项
    )


settings = Settings()
