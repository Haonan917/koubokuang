# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/run_api_server.py
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

"""启动 API 服务器"""
import os

import uvicorn

from utils.logger import setup_logging_intercept

if __name__ == "__main__":
    # 在启动 uvicorn 之前设置日志拦截，统一日志格式
    setup_logging_intercept()

    # 生产环境禁用 reload，开发环境启用
    # 通过环境变量 RELOAD=true 或 ENV=development 控制
    reload_enabled = os.getenv("RELOAD", "").lower() == "true" or os.getenv("ENV", "").lower() == "development"

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=reload_enabled,
        log_config=None,  # 禁用 uvicorn 默认日志配置，使用我们的拦截器
    )
