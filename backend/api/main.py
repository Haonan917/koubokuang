# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/api/main.py
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

"""FastAPI 应用入口"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from api.routes import health, remix, cookies, llm_config, insight_modes, auth, media_ai, admin
from agent.memory import memory_manager
from i18n import LanguageMiddleware
from utils.logger import logger, setup_logging_intercept

# 设置日志拦截，将 uvicorn 日志统一为 Loguru 格式
setup_logging_intercept()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期 (异步)

    启动时:
    - 运行数据库迁移
    - 检测 DownloadServer 服务可用性
    - 初始化记忆存储 (Checkpointer + Store)
    - 预加载 ASR 模型 (faster-whisper)

    关闭时:
    - 清理记忆存储资源 (关闭数据库连接)
    """
    logger.info("Starting Content Remix Agent API...")

    # 运行数据库迁移 (自动执行未完成的迁移)
    from services.migration_service import migration_service
    try:
        migration_count = await migration_service.run_migrations()
        if migration_count > 0:
            logger.info(f"Database migrations completed: {migration_count} migration(s) executed")
        else:
            logger.info("Database schema is up to date")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        logger.error("请检查数据库连接配置和迁移文件")
        raise SystemExit(1)
    finally:
        await migration_service.close()

    # Bootstrap（可选）：创建默认管理员账号
    from services.bootstrap_service import bootstrap_service
    await bootstrap_service.bootstrap_default_admin()

    # 检测 DownloadServer 可用性
    from services.download_server_client import download_server_client, DownloadServerError
    try:
        await download_server_client.ping()
        logger.info(f"DownloadServer 连接成功: {settings.DOWNLOAD_SERVER_BASE}")
    except DownloadServerError as e:
        logger.error(f"DownloadServer 不可用: {e}")
        logger.error("请先启动 DownloadServer 服务后再启动本服务")
        raise SystemExit(1)

    # 创建资源目录（用于存储封面、视频等）
    assets_dir = Path(settings.ASSETS_DIR)
    assets_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Assets directory: {assets_dir.resolve()}")

    # 启动时：异步初始化记忆存储
    await memory_manager.initialize()
    logger.info("Memory manager initialized")

    # 检查并预加载 Insight Mode prompts
    from services.insight_mode_service import insight_mode_service
    try:
        # 验证系统模式已初始化（由迁移系统完成）
        await insight_mode_service.initialize_default_modes()

        # 预加载 mode prompts 到缓存
        from agent.prompts import _preload_mode_prompts
        await _preload_mode_prompts()
        logger.info("Mode prompts preloaded")
    except Exception as e:
        logger.warning(f"Failed to preload insight modes: {e}")

    # 预加载 ASR 模型（在线程池中运行，避免阻塞事件循环）
    from services.asr_service import ASRService
    asr_service = ASRService()
    await asyncio.to_thread(asr_service.preload)

    yield

    # 关闭时：异步清理记忆存储资源
    logger.info("Shutting down Content Remix Agent API...")
    await memory_manager.cleanup()
    logger.info("Memory manager cleaned up")


app = FastAPI(
    title="Content Remix Agent",
    version="0.1.0",
    description="AI-powered content remix assistant for social media platforms",
    lifespan=lifespan,
)

# API 使用日志（请求维度）
from api.middleware.usage_logging import api_usage_middleware
app.middleware("http")(api_usage_middleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# i18n 语言中间件
app.add_middleware(LanguageMiddleware)

# 注册路由
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(remix.router, prefix="/api/v1/remix", tags=["remix"])
app.include_router(media_ai.router, prefix="/api/v1/media-ai", tags=["media-ai"])
app.include_router(cookies.router, prefix="/api/v1/cookies", tags=["cookies"])
app.include_router(llm_config.router, prefix="/api/v1/llm-config", tags=["llm-config"])
app.include_router(insight_modes.router, prefix="/api/v1/insight-modes", tags=["insight-modes"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

# 挂载静态文件服务
# 1. 内置静态资源（fonts, logos）- 不被 Docker 挂载覆盖
_static_assets_dir = Path(settings.STATIC_ASSETS_DIR)
if _static_assets_dir.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_static_assets_dir)),
        name="static_assets"
    )

# 2. 用户生成资源（封面、视频）- Docker 挂载持久化
_user_assets_dir = Path(settings.ASSETS_DIR)
_user_assets_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.ASSETS_URL_PREFIX,  # /media
    StaticFiles(directory=str(_user_assets_dir)),
    name="user_assets"
)
