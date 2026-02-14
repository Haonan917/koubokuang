# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/image_utils.py
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
图片处理工具 - 多模态功能支持

功能:
- 批量下载图片到本地
- 检测图片格式（通过文件头）
- Base64 编码图片
- 大图压缩处理
"""
import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from config import settings
from utils.logger import logger


class ImageProcessError(Exception):
    """图片处理错误"""
    pass


@dataclass
class ProcessedImage:
    """处理后的图片信息"""
    base64_data: str       # Base64 编码数据
    mime_type: str         # MIME 类型 (image/jpeg, image/png, image/webp)
    original_url: str      # 原始 URL
    local_path: str        # 本地路径
    file_size: int         # 文件大小（字节）


# 图片文件头魔数映射
IMAGE_SIGNATURES = {
    b'\xFF\xD8\xFF': ('image/jpeg', '.jpg'),
    b'\x89PNG\r\n\x1A\n': ('image/png', '.png'),
    b'GIF87a': ('image/gif', '.gif'),
    b'GIF89a': ('image/gif', '.gif'),
    b'RIFF': ('image/webp', '.webp'),  # WebP 以 RIFF 开头
}


def detect_image_format(file_path: str) -> Tuple[str, str]:
    """
    通过文件头检测图片格式

    Args:
        file_path: 图片文件路径

    Returns:
        (mime_type, extension) 元组

    Raises:
        ImageProcessError: 无法识别的图片格式
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(12)  # 读取足够的字节用于识别

        # 检查各种图片格式签名
        for signature, (mime_type, ext) in IMAGE_SIGNATURES.items():
            if header.startswith(signature):
                return mime_type, ext

        # WebP 特殊处理：RIFF....WEBP
        if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
            return 'image/webp', '.webp'

        # 未知格式，尝试从扩展名推断
        path_ext = Path(file_path).suffix.lower()
        ext_to_mime = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        if path_ext in ext_to_mime:
            return ext_to_mime[path_ext], path_ext

        # 默认 JPEG
        logger.warning(f"Unknown image format for {file_path}, defaulting to JPEG")
        return 'image/jpeg', '.jpg'

    except Exception as e:
        raise ImageProcessError(f"Failed to detect image format: {e}")


def encode_image_to_base64(file_path: str) -> str:
    """
    读取图片并编码为 Base64

    Args:
        file_path: 图片文件路径

    Returns:
        Base64 编码的字符串

    Raises:
        ImageProcessError: 读取或编码失败
    """
    try:
        with open(file_path, 'rb') as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        raise ImageProcessError(f"Failed to encode image to base64: {e}")


def get_image_file_size(file_path: str) -> int:
    """获取图片文件大小（字节）"""
    return Path(file_path).stat().st_size


async def compress_image_if_needed(
    file_path: str,
    max_size_bytes: int = 2 * 1024 * 1024,  # 2MB
    max_dimension: int = 1920,
    quality: int = 85
) -> str:
    """
    压缩大图（如果超过限制）

    Args:
        file_path: 图片文件路径
        max_size_bytes: 最大文件大小（字节）
        max_dimension: 最大边长（像素）
        quality: JPEG 压缩质量 (1-100)

    Returns:
        处理后的图片路径（可能是原路径或压缩后的新路径）
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not installed, skipping image compression")
        return file_path

    file_size = get_image_file_size(file_path)

    # 如果文件大小在限制内，不需要压缩
    if file_size <= max_size_bytes:
        return file_path

    logger.info(f"Compressing image: {file_path} ({file_size / 1024 / 1024:.2f}MB)")

    try:
        img = Image.open(file_path)

        # 保持原始模式，但转换 RGBA 为 RGB（JPEG 不支持透明通道）
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 调整尺寸
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.debug(f"Resized from {width}x{height} to {new_width}x{new_height}")

        # 保存压缩后的图片
        compressed_path = file_path.replace('.', '_compressed.')
        if not compressed_path.endswith(('.jpg', '.jpeg')):
            compressed_path = str(Path(file_path).with_suffix('.jpg'))
            compressed_path = compressed_path.replace('.jpg', '_compressed.jpg')

        img.save(compressed_path, 'JPEG', quality=quality, optimize=True)

        new_size = get_image_file_size(compressed_path)
        logger.info(f"Compressed: {file_size / 1024:.1f}KB -> {new_size / 1024:.1f}KB")

        return compressed_path

    except Exception as e:
        logger.warning(f"Failed to compress image: {e}, using original")
        return file_path


def _get_headers_for_url(url: str) -> dict:
    """根据 URL 获取合适的请求头"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # B站
    if "bilibili" in url or "hdslb" in url:
        headers["Referer"] = "https://www.bilibili.com/"

    # 抖音
    if "douyinpic" in url or "bytedance" in url:
        headers["Referer"] = "https://www.douyin.com/"

    # 小红书
    if "xhscdn" in url or "xiaohongshu" in url:
        headers["Referer"] = "https://www.xiaohongshu.com/"

    # 快手
    if "kuaishou" in url or "kwcdn" in url:
        headers["Referer"] = "https://www.kuaishou.com/"

    return headers


def _get_extension_from_url(url: str) -> str:
    """从 URL 路径提取扩展名"""
    url_path = urlparse(url).path
    for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        if url_path.lower().endswith(ext):
            return ext
    return ".jpg"  # 默认


async def download_image(
    image_url: str,
    save_dir: Path,
    filename: str,
    timeout: int = 30
) -> str:
    """
    下载单张图片

    Args:
        image_url: 图片 URL
        save_dir: 保存目录
        filename: 文件名（不含扩展名）
        timeout: 超时时间（秒）

    Returns:
        保存的本地文件路径

    Raises:
        ImageProcessError: 下载失败
    """
    if not image_url:
        raise ImageProcessError("Image URL is empty")

    # 确保目录存在
    save_dir.mkdir(parents=True, exist_ok=True)

    headers = _get_headers_for_url(image_url)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(image_url, headers=headers)
            response.raise_for_status()

            # 从 Content-Type 或 URL 确定扩展名
            content_type = response.headers.get("content-type", "")
            if "jpeg" in content_type or "jpg" in content_type:
                ext = ".jpg"
            elif "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            elif "gif" in content_type:
                ext = ".gif"
            else:
                ext = _get_extension_from_url(image_url)

            # 保存文件
            save_path = save_dir / f"{filename}{ext}"
            with open(save_path, "wb") as f:
                f.write(response.content)

            logger.debug(f"Image downloaded: {save_path} ({len(response.content)} bytes)")
            return str(save_path)

    except httpx.TimeoutException:
        raise ImageProcessError(f"Image download timeout: {image_url}")
    except httpx.HTTPStatusError as e:
        raise ImageProcessError(f"Image download failed: HTTP {e.response.status_code}")
    except Exception as e:
        raise ImageProcessError(f"Image download failed: {e}")


async def download_and_process_images(
    image_urls: List[str],
    platform: str,
    content_id: str,
    max_images: Optional[int] = None,
    compress: Optional[bool] = None,
    max_size_bytes: Optional[int] = None,
    max_dimension: Optional[int] = None
) -> List[ProcessedImage]:
    """
    批量下载并处理图片

    Args:
        image_urls: 图片 URL 列表
        platform: 平台标识 (xhs/dy/bilibili/ks)
        content_id: 内容 ID
        max_images: 最多处理的图片数量（默认读取配置）
        compress: 是否压缩大图（默认读取配置）
        max_size_bytes: 单张图片最大大小（默认读取配置）
        max_dimension: 压缩后最大边长（默认读取配置）

    Returns:
        ProcessedImage 列表
    """
    if not image_urls:
        return []

    # 使用配置或默认值
    _max_images = max_images or getattr(settings, 'MULTIMODAL_MAX_IMAGES', 5)
    _compress = compress if compress is not None else getattr(settings, 'MULTIMODAL_COMPRESS_IMAGES', True)
    _max_size = max_size_bytes or getattr(settings, 'MULTIMODAL_MAX_IMAGE_SIZE', 2 * 1024 * 1024)
    _max_dim = max_dimension or getattr(settings, 'MULTIMODAL_MAX_DIMENSION', 1920)

    # 限制处理数量
    urls_to_process = image_urls[:_max_images]

    # 资源保存目录
    assets_dir = Path(settings.ASSETS_DIR)
    save_dir = assets_dir / platform / content_id / "images"

    processed_images: List[ProcessedImage] = []

    for idx, url in enumerate(urls_to_process):
        try:
            # 下载图片
            filename = f"image_{idx:02d}"
            local_path = await download_image(url, save_dir, filename)

            # 压缩（如果需要）
            if _compress:
                local_path = await compress_image_if_needed(
                    local_path,
                    max_size_bytes=_max_size,
                    max_dimension=_max_dim
                )

            # 检测格式并编码
            mime_type, _ = detect_image_format(local_path)
            base64_data = encode_image_to_base64(local_path)
            file_size = get_image_file_size(local_path)

            processed_images.append(ProcessedImage(
                base64_data=base64_data,
                mime_type=mime_type,
                original_url=url,
                local_path=local_path,
                file_size=file_size,
            ))

            logger.info(f"Processed image {idx + 1}/{len(urls_to_process)}: {file_size / 1024:.1f}KB")

        except Exception as e:
            logger.warning(f"Failed to process image {idx + 1}: {e}")
            continue

    logger.info(f"Downloaded and processed {len(processed_images)} images for {platform}/{content_id}")
    return processed_images


def build_image_content_block(image_path: str) -> dict:
    """
    构建 LangChain 多模态消息中的图片内容块

    Args:
        image_path: 本地图片路径

    Returns:
        图片内容块字典
    """
    mime_type, _ = detect_image_format(image_path)
    base64_data = encode_image_to_base64(image_path)

    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{mime_type};base64,{base64_data}"
        }
    }


def build_multimodal_content(text: str, image_paths: List[str], max_images: int = 5) -> List[dict]:
    """
    构建多模态消息内容列表

    Args:
        text: 文本内容
        image_paths: 本地图片路径列表
        max_images: 最多包含的图片数

    Returns:
        多模态内容列表（用于 HumanMessage.content）
    """
    content = [{"type": "text", "text": text}]

    for path in image_paths[:max_images]:
        try:
            content.append(build_image_content_block(path))
        except Exception as e:
            logger.warning(f"Failed to add image to content: {e}")
            continue

    return content
