# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/download_brand_logos.py
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
Brand Logo Downloader CLI Script
品牌 Logo 批量下载脚本

Usage:
    uv run python scripts/download_brand_logos.py [OPTIONS]

Examples:
    # 下载所有品牌 logo
    uv run python scripts/download_brand_logos.py

    # 仅下载平台 logo
    uv run python scripts/download_brand_logos.py --category platform

    # 仅下载指定品牌
    uv run python scripts/download_brand_logos.py --brand xhs

    # 强制重新下载
    uv run python scripts/download_brand_logos.py --force

    # 预览模式（不实际下载）
    uv run python scripts/download_brand_logos.py --dry-run
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.brand_logos import (
    ALL_BRANDS,
    BrandInfo,
    get_brand_by_key,
    get_brands_by_category,
)
from services.logo_downloader import download_multiple_logos


# ========== 配置 ==========
DEFAULT_LOGOS_DIR = Path(__file__).parent.parent / "assets" / "logos"
MAX_CONCURRENT = 3


# ========== CLI 函数 ==========
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Download brand logos for platforms and LLM providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/download_brand_logos.py                    # Download all logos
  python scripts/download_brand_logos.py --category platform   # Only platform logos
  python scripts/download_brand_logos.py --brand xhs          # Only xhs logo
  python scripts/download_brand_logos.py --force              # Force re-download
  python scripts/download_brand_logos.py --dry-run            # Preview mode
        """
    )

    parser.add_argument(
        "--brand",
        type=str,
        help="Download only specified brand (e.g., xhs, openai)"
    )

    parser.add_argument(
        "--category",
        type=str,
        choices=["platform", "llm_provider"],
        help="Download only specified category"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download (overwrite existing files)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode (don't actually download)"
    )

    parser.add_argument(
        "--logos-dir",
        type=Path,
        default=DEFAULT_LOGOS_DIR,
        help=f"Logo storage directory (default: {DEFAULT_LOGOS_DIR})"
    )

    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=MAX_CONCURRENT,
        help=f"Maximum concurrent downloads (default: {MAX_CONCURRENT})"
    )

    return parser.parse_args()


def filter_brands(args) -> List[BrandInfo]:
    """根据命令行参数过滤品牌列表"""
    if args.brand:
        # 单个品牌
        brand = get_brand_by_key(args.brand)
        if not brand:
            print(f"❌ Error: Unknown brand '{args.brand}'")
            print(f"   Available brands: {', '.join(b.key for b in ALL_BRANDS)}")
            sys.exit(1)
        return [brand]

    elif args.category:
        # 按分类
        return get_brands_by_category(args.category)

    else:
        # 所有品牌
        return ALL_BRANDS


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}GB"


def print_banner():
    """打印横幅"""
    print("=" * 60)
    print("Brand Logo Downloader")
    print("品牌 Logo 批量下载工具")
    print("=" * 60)
    print()


def print_summary(results: List[dict]):
    """打印下载总结"""
    # 统计结果
    success_count = sum(1 for r in results if r['status'] == 'success')
    skip_count = sum(1 for r in results if r['status'] == 'skip')
    error_count = sum(1 for r in results if r['status'] == 'error')

    print()
    print("=" * 60)
    print("Summary:")
    print(f"  ✓ Success: {success_count}")
    print(f"  ⊙ Skipped: {skip_count}")
    print(f"  ✗ Failed: {error_count}")
    print()

    # 输出失败详情
    if error_count > 0:
        print("Failed brands (manual download required):")
        for result in results:
            if result['status'] == 'error':
                brand_name = result.get('brand_name', result.get('brand_key', 'Unknown'))
                message = result.get('message', 'Unknown error')
                print(f"  - {result['brand_key']} ({brand_name}): {message}")
        print()

    # 输出成功详情
    if success_count > 0:
        print("Successfully downloaded:")
        for result in results:
            if result['status'] == 'success':
                size = format_file_size(result.get('file_size', 0))
                dims = result.get('dimensions', (0, 0))
                print(f"  ✓ {result['brand_key']}: {dims[0]}x{dims[1]}, {size}")
        print()

    print("=" * 60)


async def main():
    """主函数"""
    # 解析参数
    args = parse_args()

    # 打印横幅
    print_banner()

    # 过滤品牌列表
    brands = filter_brands(args)

    # 显示任务信息
    print(f"Target: {len(brands)} brand(s)")
    if args.force:
        print("Mode: Force re-download (overwrite existing)")
    if args.dry_run:
        print("Mode: Dry run (preview only)")
    print(f"Output directory: {args.logos_dir}")
    print()

    # 预览模式
    if args.dry_run:
        print("Brands to download:")
        for i, brand in enumerate(brands, 1):
            print(f"  [{i}/{len(brands)}] {brand.key} ({brand.display_name}) - {brand.category}")
        print()
        print("Run without --dry-run to actually download.")
        return

    # 开始下载
    print("Starting download...")
    print()

    results = await download_multiple_logos(
        brands=brands,
        logos_dir=args.logos_dir,
        force=args.force,
        max_concurrent=args.max_concurrent
    )

    # 实时显示进度
    for i, result in enumerate(results, 1):
        brand_key = result.get('brand_key', 'unknown')
        brand_name = result.get('brand_name', 'Unknown')
        status = result['status']

        if status == 'success':
            size = format_file_size(result.get('file_size', 0))
            dims = result.get('dimensions', (0, 0))
            print(f"[{i}/{len(results)}] {brand_key} ({brand_name})... ✓ Success ({dims[0]}x{dims[1]}, {size})")
        elif status == 'skip':
            print(f"[{i}/{len(results)}] {brand_key} ({brand_name})... ⊙ Skipped (already exists)")
        else:
            print(f"[{i}/{len(results)}] {brand_key} ({brand_name})... ✗ Failed")

    # 打印总结
    print_summary(results)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
