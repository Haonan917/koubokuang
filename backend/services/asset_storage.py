# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/asset_storage.py
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
资源存储服务 - 管理本地资源的下载和存储

功能:
- 下载封面图到本地
- 管理视频持久化（从临时目录移动）
- 生成 Markdown 元数据文件
- 提供本地资源 URL 映射
"""
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from config import settings
from utils.logger import logger


class AssetStorageError(Exception):
    """资源存储错误"""
    pass


class AssetStorageService:
    """资源存储服务"""

    def __init__(self):
        self.assets_dir = Path(settings.ASSETS_DIR)
        self.url_prefix = settings.ASSETS_URL_PREFIX

    def get_content_dir(self, platform: str, content_id: str) -> Path:
        """
        获取内容资源目录

        Args:
            platform: 平台标识 (xhs/dy/bilibili/ks)
            content_id: 内容 ID

        Returns:
            资源目录路径: assets/{platform}/{content_id}/
        """
        return self.assets_dir / platform / content_id

    def get_local_url(self, platform: str, content_id: str, filename: str) -> str:
        """
        生成本地资源 URL

        Args:
            platform: 平台标识
            content_id: 内容 ID
            filename: 文件名

        Returns:
            本地 URL: /assets/{platform}/{content_id}/{filename}
        """
        return f"{self.url_prefix}/{platform}/{content_id}/{filename}"

    def check_exists(self, platform: str, content_id: str, filename: str) -> bool:
        """检查资源是否已存在"""
        file_path = self.get_content_dir(platform, content_id) / filename
        return file_path.exists()

    def _get_image_extension(self, url: str, content_type: str = "") -> str:
        """根据 URL 和 Content-Type 确定图片扩展名"""
        # 从 URL 路径提取扩展名
        url_path = urlparse(url).path
        for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            if url_path.lower().endswith(ext):
                return ext

        # 从 Content-Type 推断
        if "jpeg" in content_type or "jpg" in content_type:
            return ".jpg"
        elif "png" in content_type:
            return ".png"
        elif "gif" in content_type:
            return ".gif"
        elif "webp" in content_type:
            return ".webp"

        # 默认 jpg
        return ".jpg"

    def _get_headers(self, url: str) -> dict:
        """根据 URL 获取请求头"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        # B站封面需要 Referer
        if "bilibili" in url or "hdslb" in url:
            headers["Referer"] = "https://www.bilibili.com/"

        # 抖音封面
        if "douyinpic" in url or "bytedance" in url:
            headers["Referer"] = "https://www.douyin.com/"

        # 小红书封面
        if "xhscdn" in url or "xiaohongshu" in url:
            headers["Referer"] = "https://www.xiaohongshu.com/"

        # 快手封面
        if "kuaishou" in url or "kwcdn" in url:
            headers["Referer"] = "https://www.kuaishou.com/"

        return headers

    async def download_cover(
        self,
        cover_url: str,
        platform: str,
        content_id: str,
        timeout: int = 30
    ) -> str:
        """
        下载封面图

        Args:
            cover_url: 封面图 URL
            platform: 平台标识
            content_id: 内容 ID
            timeout: 下载超时时间（秒）

        Returns:
            本地 URL 路径: /assets/{platform}/{content_id}/cover.jpg

        Raises:
            AssetStorageError: 下载失败
        """
        if not cover_url:
            raise AssetStorageError("封面 URL 为空")

        # 创建目录
        content_dir = self.get_content_dir(platform, content_id)
        content_dir.mkdir(parents=True, exist_ok=True)

        headers = self._get_headers(cover_url)

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(cover_url, headers=headers)
                response.raise_for_status()

                # 确定文件扩展名
                content_type = response.headers.get("content-type", "")
                ext = self._get_image_extension(cover_url, content_type)
                filename = f"cover{ext}"
                cover_path = content_dir / filename

                # 保存文件
                with open(cover_path, "wb") as f:
                    f.write(response.content)

                logger.info(f"Cover downloaded: {cover_path} ({len(response.content)} bytes)")

                return self.get_local_url(platform, content_id, filename)

        except httpx.TimeoutException:
            raise AssetStorageError("封面下载超时")
        except httpx.HTTPStatusError as e:
            raise AssetStorageError(f"封面下载失败: HTTP {e.response.status_code}")
        except Exception as e:
            raise AssetStorageError(f"封面下载失败: {str(e)}")

    async def persist_video(
        self,
        temp_video_path: str,
        platform: str,
        content_id: str
    ) -> str:
        """
        持久化视频（从临时目录移动到资源目录）

        Args:
            temp_video_path: 临时视频文件路径
            platform: 平台标识
            content_id: 内容 ID

        Returns:
            本地 URL 路径: /assets/{platform}/{content_id}/video.mp4

        Raises:
            AssetStorageError: 移动失败
        """
        if not temp_video_path:
            raise AssetStorageError("临时视频路径为空")

        temp_path = Path(temp_video_path)
        if not temp_path.exists():
            raise AssetStorageError(f"临时视频文件不存在: {temp_video_path}")

        # 创建目录
        content_dir = self.get_content_dir(platform, content_id)
        content_dir.mkdir(parents=True, exist_ok=True)

        # 保留原始扩展名
        ext = temp_path.suffix or ".mp4"
        filename = f"video{ext}"
        target_path = content_dir / filename

        try:
            # 移动文件（比复制快，且释放临时空间）
            shutil.move(str(temp_path), str(target_path))
            logger.info(f"Video persisted: {target_path}")

            return self.get_local_url(platform, content_id, filename)

        except Exception as e:
            raise AssetStorageError(f"视频持久化失败: {str(e)}")

    def generate_metadata(
        self,
        platform: str,
        content_id: str,
        title: str,
        desc: str = "",
        author_name: str = "",
        author_id: str = "",
        publish_time: Optional[int] = None,
        duration: Optional[int] = None,
        content_type: str = "video",
        tags: Optional[list] = None,
        transcript: Optional[str] = None,
        # 互动数据
        like_count: int = 0,
        comment_count: int = 0,
        share_count: int = 0,
        collect_count: int = 0,
        view_count: int = 0,
        danmaku_count: int = 0,
        # 媒体资源 URL
        cover_url: str = "",
        video_url: str = "",
        audio_url: str = "",  # B站单独提供音频流
        image_urls: Optional[list] = None,
        # 本地资源 URL
        local_cover_url: str = "",
        local_video_url: str = "",
        **extra
    ) -> str:
        """
        生成 Markdown 元数据文件（带 YAML frontmatter）

        Args:
            platform: 平台标识
            content_id: 内容 ID
            title: 标题
            desc: 描述
            author_name: 作者名
            author_id: 作者 ID
            publish_time: 发布时间（毫秒时间戳）
            duration: 视频时长（秒）
            content_type: 内容类型 (video/image/mixed)
            tags: 标签列表
            transcript: 转录文本
            like_count: 点赞数
            comment_count: 评论数
            share_count: 分享数
            collect_count: 收藏数
            view_count: 播放量
            danmaku_count: 弹幕数（B站）
            cover_url: 原始封面 URL
            video_url: 原始视频 URL
            image_urls: 原始图片 URL 列表
            local_cover_url: 本地封面 URL
            local_video_url: 本地视频 URL
            **extra: 其他元数据

        Returns:
            本地 URL 路径: /assets/{platform}/{content_id}/metadata.md
        """
        # 创建目录
        content_dir = self.get_content_dir(platform, content_id)
        content_dir.mkdir(parents=True, exist_ok=True)

        # 平台名称映射
        platform_names = {
            "xhs": "小红书",
            "dy": "抖音",
            "bilibili": "B站",
            "ks": "快手",
        }
        platform_name = platform_names.get(platform, platform)

        # 格式化发布时间
        publish_time_str = ""
        publish_time_iso = ""
        if publish_time:
            try:
                dt = datetime.fromtimestamp(publish_time / 1000)
                publish_time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                publish_time_iso = dt.isoformat()
            except (ValueError, OSError):
                publish_time_str = str(publish_time)
                publish_time_iso = str(publish_time)

        # 格式化时长
        duration_str = ""
        if duration:
            mins = duration // 60
            secs = duration % 60
            duration_str = f"{mins}分{secs}秒" if mins > 0 else f"{secs}秒"

        # 构建 YAML frontmatter
        yaml_lines = ["---"]

        # 基本信息
        yaml_lines.append(f'title: "{self._escape_yaml_string(title or "无标题")}"')
        yaml_lines.append(f"content_id: \"{content_id}\"")
        yaml_lines.append(f"platform: {platform}")
        yaml_lines.append(f"platform_name: {platform_name}")
        yaml_lines.append(f"content_type: {content_type}")

        # 作者信息
        if author_name:
            yaml_lines.append(f'author: "{self._escape_yaml_string(author_name)}"')
        if author_id:
            yaml_lines.append(f'author_id: "{author_id}"')

        # 时间和时长
        if publish_time_iso:
            yaml_lines.append(f"publish_time: {publish_time_iso}")
        if duration:
            yaml_lines.append(f"duration: {duration}")
            yaml_lines.append(f"duration_text: \"{duration_str}\"")

        # 标签
        if tags:
            yaml_lines.append("tags:")
            for tag in tags:
                yaml_lines.append(f'  - "{self._escape_yaml_string(tag)}"')

        # 互动数据
        yaml_lines.append("stats:")
        if view_count:
            yaml_lines.append(f"  views: {view_count}")
        yaml_lines.append(f"  likes: {like_count}")
        yaml_lines.append(f"  comments: {comment_count}")
        yaml_lines.append(f"  shares: {share_count}")
        yaml_lines.append(f"  collects: {collect_count}")
        if danmaku_count:
            yaml_lines.append(f"  danmaku: {danmaku_count}")

        # 媒体资源 URL
        yaml_lines.append("media:")
        if cover_url:
            yaml_lines.append(f'  cover_url: "{cover_url}"')
        if video_url:
            yaml_lines.append(f'  video_url: "{video_url}"')
        if audio_url:
            yaml_lines.append(f'  audio_url: "{audio_url}"')
        if image_urls:
            yaml_lines.append("  image_urls:")
            for img_url in image_urls:
                yaml_lines.append(f'    - "{img_url}"')

        # 本地资源 URL
        yaml_lines.append("local:")
        if local_cover_url:
            yaml_lines.append(f'  cover: "{local_cover_url}"')
        if local_video_url:
            yaml_lines.append(f'  video: "{local_video_url}"')

        # 记录保存时间
        yaml_lines.append(f"saved_at: {datetime.now().isoformat()}")

        yaml_lines.append("---")
        yaml_lines.append("")

        # 构建 Markdown 正文
        md_lines = [
            f"# {title or '无标题'}",
            "",
        ]

        # 描述
        if desc:
            md_lines.extend([
                "## 描述",
                "",
                desc,
                "",
            ])

        # 转录文本
        if transcript:
            md_lines.extend([
                "## 转录文本",
                "",
                transcript,
                "",
            ])

        # 合并 YAML 和 Markdown
        content = "\n".join(yaml_lines) + "\n".join(md_lines)

        # 写入文件
        filename = "metadata.md"
        metadata_path = content_dir / filename

        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Metadata generated: {metadata_path}")

        return self.get_local_url(platform, content_id, filename)

    def _escape_yaml_string(self, s: str) -> str:
        """转义 YAML 字符串中的特殊字符"""
        if not s:
            return ""
        # 转义双引号和反斜杠
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def cleanup_content(self, platform: str, content_id: str) -> None:
        """清理指定内容的所有资源"""
        content_dir = self.get_content_dir(platform, content_id)
        if content_dir.exists():
            shutil.rmtree(content_dir)
            logger.info(f"Content assets cleaned: {content_dir}")
