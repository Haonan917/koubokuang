#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/run_migrations.py
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
数据库迁移脚本

执行所有未完成的数据库迁移。

使用方式:
    # 执行迁移
    uv run python scripts/run_migrations.py

    # 查看状态（不执行）
    uv run python scripts/run_migrations.py --status

    # 试运行（查看待执行的迁移）
    uv run python scripts/run_migrations.py --dry-run

环境变量:
    AGENT_DB_HOST: 数据库主机
    AGENT_DB_PORT: 数据库端口
    AGENT_DB_USER: 数据库用户
    AGENT_DB_PASSWORD: 数据库密码
    AGENT_DB_NAME: 数据库名称
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.migration_service import migration_service
from utils.logger import logger


async def run_migrations(dry_run: bool = False):
    """执行迁移"""
    try:
        count = await migration_service.run_migrations(dry_run=dry_run)

        if dry_run:
            print(f"\nDry run completed. {count} migration(s) would be executed.")
        else:
            print(f"\nMigration completed. {count} migration(s) executed.")

        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await migration_service.close()


async def show_status():
    """显示迁移状态"""
    try:
        status = await migration_service.get_status()

        print("\n" + "=" * 60)
        print("Database Migration Status")
        print("=" * 60)
        print(f"Current version: V{status['current_version']:03d}")
        print(f"Total migrations: {status['total_migrations']}")
        print(f"Executed: {status['executed_count']}")
        print(f"Pending: {status['pending_count']}")

        if status['executed_migrations']:
            print("\nExecuted migrations:")
            for m in status['executed_migrations']:
                print(f"  ✓ V{m['version']:03d}: {m['description']}")
                print(f"       Executed at: {m['executed_at']}, Time: {m['execution_time_ms']}ms")

        if status['pending_migrations']:
            print("\nPending migrations:")
            for m in status['pending_migrations']:
                print(f"  ○ V{m['version']:03d}: {m['description']}")

        print("=" * 60)
        return True
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await migration_service.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Database migration tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show migration status without executing"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show pending migrations without executing"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Content Remix Agent - Database Migration")
    print("=" * 60)

    if args.status:
        success = asyncio.run(show_status())
    else:
        success = asyncio.run(run_migrations(dry_run=args.dry_run))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
