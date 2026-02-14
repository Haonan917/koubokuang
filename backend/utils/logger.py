# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/utils/logger.py
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
日志配置模块 - 使用 Loguru 进行日志管理

支持两种日志格式:
- pretty: 彩色格式化输出（开发环境）
- json: 结构化 JSON 输出（生产环境）
"""
import sys
import json
import logging

from loguru import logger


class InterceptHandler(logging.Handler):
    """拦截标准 logging 日志，重定向到 Loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        # 获取对应的 Loguru 级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 使用 patch 覆盖 loguru record 的位置信息
        # 这样 {name}:{function}:{line} 会显示原始 logger 的位置
        def patcher(loguru_record):
            loguru_record["name"] = record.name
            loguru_record["function"] = record.funcName
            loguru_record["line"] = record.lineno

        logger.patch(patcher).opt(exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging_intercept(loggers: list[str] = None, level: int = logging.DEBUG):
    """
    设置日志拦截，将指定的标准 logging logger 重定向到 Loguru

    Args:
        loggers: 要拦截的 logger 名称列表，默认拦截 uvicorn 相关日志
        level: 日志级别，默认 DEBUG（让 Loguru 决定过滤）
    """
    if loggers is None:
        loggers = ["uvicorn", "uvicorn.error", "uvicorn.access"]

    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.setLevel(level)
        logging_logger.propagate = False

# 延迟导入 config，避免循环依赖
def _get_config():
    try:
        from config import settings
        return settings
    except ImportError:
        # 如果 config 未初始化，使用默认值
        class DefaultSettings:
            LOG_LEVEL = "INFO"
            LOG_FORMAT = "pretty"
        return DefaultSettings()


# 移除默认的 handler
logger.remove()

# 获取配置
settings = _get_config()
log_format = getattr(settings, "LOG_FORMAT", "pretty")
log_level = getattr(settings, "LOG_LEVEL", "INFO")

if log_format == "json":
    # JSON 格式（生产环境）
    def json_formatter(record):
        """格式化日志为 JSON"""
        log_entry = {
            "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S"),
            "level": record["level"].name,
            "location": f"{record['file'].name}:{record['function']}:{record['line']}",
            "message": record["message"],
        }

        # 添加 extra 字段
        if record.get("extra"):
            # 过滤掉 loguru 内部字段
            extra = {k: v for k, v in record["extra"].items()
                    if not k.startswith("_")}
            if extra:
                log_entry["extra"] = extra

        # 添加异常信息
        if record.get("exception"):
            log_entry["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
            }

        return json.dumps(log_entry, ensure_ascii=False)

    logger.add(
        sys.stdout,
        format=json_formatter,
        level=log_level,
    )
else:
    # Pretty 格式（开发环境）- 简洁清晰，不处理 extra 字段避免格式化错误
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
        backtrace=True,   # 显示完整堆栈
        diagnose=False,   # 显示变量值（True=带竖线和变量值，False=标准格式）
    )

__all__ = ["logger", "setup_logging_intercept"]
