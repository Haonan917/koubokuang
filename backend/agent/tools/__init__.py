# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/agent/tools/__init__.py
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
Agent Tools 模块

提供 RemixAgent 可调用的工具集合。

简化架构：只保留数据获取工具
Agent 完成数据获取后，直接输出 Markdown 格式的分析和灵感。
"""

from agent.tools.link_parser_tool import parse_link
from agent.tools.fetch_content_tool import fetch_content
from agent.tools.video_processor_tool import process_video
from agent.tools.voice_clone_tool import voice_clone
from agent.tools.text_to_speech_tool import text_to_speech
from agent.tools.lipsync_generate_tool import lipsync_generate

__all__ = [
    "parse_link",     # 解析链接
    "fetch_content",  # 获取内容
    "process_video",  # 处理视频
    "voice_clone",    # 语音克隆
    "text_to_speech", # 文本转语音
    "lipsync_generate",  # 唇形同步
]
