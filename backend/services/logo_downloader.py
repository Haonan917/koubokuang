# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/logo_downloader.py
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
Brand Logo Downloader Service
品牌 Logo 下载服务
"""

import asyncio
from pathlib import Path
from typing import Dict
from urllib.parse import quote_plus

import httpx
from PIL import Image

from config.brand_logos import BrandInfo


# ========== 预设 Logo URL（作为 fallback） ==========
PRESET_LOGO_URLS: Dict[str, str] = {
    # 平台 logo
    "xhs": "https://www.xiaohongshu.com/favicon.ico",
    "dy": "https://www.douyin.com/favicon.ico",
    "bili": "https://logo.clearbit.com/bilibili.com",  # Clearbit Logo API
    "ks": "https://www.kuaishou.com/favicon.ico",

    # LLM 提供商 logo
    "openai": "https://logo.clearbit.com/openai.com",  # Clearbit Logo API
    "anthropic": "https://www.anthropic.com/favicon.ico",
    "deepseek": "https://www.deepseek.com/favicon.ico",
}


class LogoDownloadError(Exception):
    """Logo 下载异常"""
    pass


async def search_logo_url(brand: BrandInfo) -> str:
    """
    搜索品牌 logo URL

    策略：
    1. 优先使用预设 URL
    2. 如果预设 URL 不可用，返回 Google Images 搜索 URL 供手动下载

    Args:
        brand: 品牌信息

    Returns:
        图片 URL 或搜索 URL

    Raises:
        LogoDownloadError: 无法获取 logo URL
    """
    # 优先使用预设 URL
    if brand.key in PRESET_LOGO_URLS:
        return PRESET_LOGO_URLS[brand.key]

    # 如果没有预设，返回 Google Images 搜索 URL（供用户手动下载）
    search_url = f"https://www.google.com/search?tbm=isch&q={quote_plus(brand.search_query)}"
    raise LogoDownloadError(
        f"No preset URL for '{brand.key}'. "
        f"Please manually download from: {search_url}"
    )


async def download_image(url: str, save_path: Path, timeout: int = 30) -> None:
    """
    下载图片到本地

    Args:
        url: 图片 URL
        save_path: 保存路径
        timeout: 超时时间（秒）

    Raises:
        LogoDownloadError: 下载失败
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            # 验证内容类型
            content_type = response.headers.get("content-type", "")
            if not any(img_type in content_type for img_type in ["image/", "application/octet-stream"]):
                raise LogoDownloadError(f"Invalid content type: {content_type}")

            # 保存原始文件
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(response.content)

    except httpx.HTTPError as e:
        raise LogoDownloadError(f"HTTP error downloading image: {e}")
    except Exception as e:
        raise LogoDownloadError(f"Error downloading image: {e}")


def optimize_image(
    image_path: Path,
    target_size: tuple = (128, 128),
    max_file_size: int = 500_000  # 500KB
) -> None:
    """
    优化图片尺寸和大小

    处理流程：
    1. 加载图片
    2. 转换为 RGBA（保留透明度）
    3. 缩放到目标尺寸（保持长宽比）
    4. 保存为 PNG 格式

    Args:
        image_path: 图片路径
        target_size: 目标尺寸（宽, 高）
        max_file_size: 最大文件大小（字节）

    Raises:
        LogoDownloadError: 优化失败
    """
    try:
        # 打开图片
        img = Image.open(image_path)

        # 转换为 RGBA（保留透明度）
        if img.mode != 'RGBA':
            # 如果是 P 模式（调色板），需要先转换
            if img.mode == 'P' and 'transparency' in img.info:
                img = img.convert('RGBA')
            elif img.mode == 'RGB':
                # RGB 转 RGBA，添加不透明的 alpha 通道
                img = img.convert('RGBA')
            else:
                img = img.convert('RGBA')

        # 缩放（保持长宽比）
        img.thumbnail(target_size, Image.Resampling.LANCZOS)

        # 保存为 PNG（优化压缩）
        output_path = image_path.with_suffix('.png')
        img.save(output_path, format='PNG', optimize=True)

        # 如果输出路径不同，删除原文件
        if output_path != image_path:
            image_path.unlink(missing_ok=True)

        # 检查文件大小
        file_size = output_path.stat().st_size
        if file_size > max_file_size:
            # 如果文件过大，使用更高的压缩
            img.save(output_path, format='PNG', optimize=True, compress_level=9)

    except Exception as e:
        raise LogoDownloadError(f"Error optimizing image: {e}")


async def download_brand_logo(
    brand: BrandInfo,
    logos_dir: Path,
    force: bool = False,
    target_size: tuple = (128, 128)
) -> dict:
    """
    下载单个品牌 logo（主入口函数）

    Args:
        brand: 品牌信息
        logos_dir: Logo 存储目录
        force: 是否强制重新下载
        target_size: 目标尺寸

    Returns:
        结果字典: {
            'status': 'success' | 'skip' | 'error',
            'path': 文件路径,
            'message': 消息,
            'file_size': 文件大小（字节）,
            'dimensions': (宽, 高)
        }
    """
    # 检查目标文件
    logo_path = logos_dir / f"{brand.key}.png"

    if logo_path.exists() and not force:
        # 获取现有文件信息
        try:
            img = Image.open(logo_path)
            dimensions = img.size
            file_size = logo_path.stat().st_size
            return {
                'status': 'skip',
                'path': str(logo_path),
                'message': 'Logo already exists',
                'file_size': file_size,
                'dimensions': dimensions
            }
        except Exception:
            # 如果文件损坏，继续下载
            pass

    # 开始下载
    temp_path = logos_dir / f"{brand.key}_temp"
    final_path = logos_dir / f"{brand.key}.png"

    try:
        # 1. 获取 logo URL
        logo_url = await search_logo_url(brand)

        # 2. 下载图片
        await download_image(logo_url, temp_path)

        # 3. 优化图片（会将 temp_path 转换为 .png）
        optimize_image(temp_path, target_size=target_size)

        # 4. 重命名为最终文件
        temp_png = temp_path.with_suffix('.png')
        if temp_png.exists():
            temp_png.rename(final_path)

        # 5. 获取结果信息
        if not final_path.exists():
            raise LogoDownloadError(f"Final file not created: {final_path}")

        img = Image.open(final_path)
        dimensions = img.size
        file_size = final_path.stat().st_size

        return {
            'status': 'success',
            'path': str(final_path),
            'message': f'Downloaded from {logo_url}',
            'file_size': file_size,
            'dimensions': dimensions
        }

    except LogoDownloadError as e:
        return {
            'status': 'error',
            'path': None,
            'message': str(e),
            'file_size': 0,
            'dimensions': (0, 0)
        }

    except Exception as e:
        return {
            'status': 'error',
            'path': None,
            'message': f'Unexpected error: {e}',
            'file_size': 0,
            'dimensions': (0, 0)
        }

    finally:
        # 清理临时文件（不删除最终文件）
        temp_path.unlink(missing_ok=True)
        temp_png = temp_path.with_suffix('.png')
        if temp_png.exists() and temp_png != final_path:
            temp_png.unlink(missing_ok=True)


async def download_multiple_logos(
    brands: list[BrandInfo],
    logos_dir: Path,
    force: bool = False,
    max_concurrent: int = 3
) -> list[dict]:
    """
    并发下载多个品牌 logo

    Args:
        brands: 品牌列表
        logos_dir: Logo 存储目录
        force: 是否强制重新下载
        max_concurrent: 最大并发数

    Returns:
        结果列表
    """
    # 确保目录存在
    logos_dir.mkdir(parents=True, exist_ok=True)

    # 创建信号量控制并发
    semaphore = asyncio.Semaphore(max_concurrent)

    async def download_with_semaphore(brand: BrandInfo) -> dict:
        async with semaphore:
            result = await download_brand_logo(brand, logos_dir, force)
            # 添加品牌信息到结果
            result['brand_key'] = brand.key
            result['brand_name'] = brand.display_name
            return result

    # 并发下载
    tasks = [download_with_semaphore(brand) for brand in brands]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    return results
