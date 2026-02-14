# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/migration_service.py
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
数据库迁移服务

提供轻量级的 schema 版本管理，类似 Flyway 的设计：
- 迁移文件命名: V{版本号}__{描述}.sql (如 V001__init_databases.sql)
- 自动按版本号顺序执行
- 记录已执行的迁移，跳过重复执行
- 支持 DDL 和 DML 语句

使用方式:
1. 应用启动时自动执行: 在 lifespan 中调用 await migration_service.run_migrations()
2. 手动执行: uv run python scripts/run_migrations.py
"""

import re
import time
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

import aiomysql

from config import settings
from utils.logger import logger


@dataclass
class Migration:
    """迁移文件信息"""
    version: int
    description: str
    filename: str
    filepath: Path
    checksum: str = ""


class MigrationService:
    """数据库迁移服务"""

    # 迁移文件目录
    MIGRATIONS_DIR = Path(__file__).parent.parent / "schema" / "migrations"

    # 迁移文件名正则: V{版本号}__{描述}.sql
    MIGRATION_PATTERN = re.compile(r"^V(\d+)__(.+)\.sql$")

    def __init__(self):
        self._pool: Optional[aiomysql.Pool] = None
        self._db_ensured: bool = False

    async def _get_pool(self) -> aiomysql.Pool:
        """获取数据库连接池"""
        if self._pool is None:
            kwargs = dict(
                host=settings.AGENT_DB_HOST or "localhost",
                port=settings.AGENT_DB_PORT or 3306,
                user=settings.AGENT_DB_USER or "root",
                password=settings.AGENT_DB_PASSWORD or "",
                charset="utf8mb4",
                autocommit=True,
                minsize=1,
                maxsize=3,
            )
            # 数据库确认存在后，连接时指定 db
            if self._db_ensured:
                kwargs["db"] = settings.AGENT_DB_NAME
            self._pool = await aiomysql.create_pool(**kwargs)
        return self._pool

    async def close(self):
        """关闭数据库连接池"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def _ensure_database_exists(self) -> None:
        """确保目标数据库存在（使用不绑定数据库的连接）"""
        pool = await self._get_pool()
        db_name = settings.AGENT_DB_NAME
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        # 数据库创建完毕，关闭无 db 的连接池，后续重建带 db 的连接池
        self._db_ensured = True
        await self.close()

    async def _ensure_migrations_table(self) -> None:
        """确保迁移记录表存在，兼容旧版 init_all.sql 创建的表结构"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 检查表是否已存在
                await cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = DATABASE() AND table_name = 'schema_migrations'
                    """
                )
                table_exists = (await cursor.fetchone())[0] > 0

                if table_exists:
                    # 检查 version 列类型是否为 VARCHAR（旧版 init_all.sql 的结构）
                    await cursor.execute(
                        """
                        SELECT DATA_TYPE FROM information_schema.columns
                        WHERE table_schema = DATABASE()
                          AND table_name = 'schema_migrations'
                          AND column_name = 'version'
                        """
                    )
                    row = await cursor.fetchone()
                    if row and row[0] == 'varchar':
                        # 旧表结构不兼容，需要重建
                        # 先读取已执行的版本号用于迁移
                        await cursor.execute("SELECT version FROM schema_migrations")
                        old_rows = await cursor.fetchall()
                        old_versions = set()
                        for r in old_rows:
                            v = r[0]
                            # 将 'V001' 格式转为 int 1
                            if isinstance(v, str) and v.startswith('V'):
                                try:
                                    old_versions.add(int(v[1:]))
                                except ValueError:
                                    pass

                        logger.info(f"Rebuilding schema_migrations table (old VARCHAR format detected, {len(old_versions)} records)")
                        await cursor.execute("DROP TABLE schema_migrations")
                        table_exists = False

                if not table_exists:
                    await cursor.execute("""
                        CREATE TABLE schema_migrations (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            version INT NOT NULL UNIQUE COMMENT '迁移版本号',
                            description VARCHAR(255) NOT NULL COMMENT '迁移描述',
                            filename VARCHAR(255) NOT NULL COMMENT '迁移文件名',
                            checksum VARCHAR(64) COMMENT '文件校验和 (SHA-256)',
                            executed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
                            execution_time_ms INT COMMENT '执行耗时 (毫秒)',
                            success TINYINT NOT NULL DEFAULT 1 COMMENT '是否成功',
                            INDEX idx_version (version)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据库迁移记录表'
                    """)

                    # 如果有旧版本记录，重新插入
                    if table_exists is False and 'old_versions' in dir():
                        for v in sorted(old_versions):
                            await cursor.execute(
                                """
                                INSERT IGNORE INTO schema_migrations (version, description, filename, success)
                                VALUES (%s, %s, %s, 1)
                                """,
                                (v, f"migrated from old table", f"V{v:03d}__unknown.sql")
                            )
                    return

                # 表已存在且是正确的 INT 格式，检查并添加缺失列
                await cursor.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = DATABASE() AND table_name = 'schema_migrations'
                    """
                )
                existing_columns = {row[0] for row in await cursor.fetchall()}

                columns_to_add = {
                    'filename': "VARCHAR(255) NOT NULL DEFAULT '' COMMENT '迁移文件名'",
                    'checksum': "VARCHAR(64) COMMENT '文件校验和 (SHA-256)'",
                    'execution_time_ms': "INT COMMENT '执行耗时 (毫秒)'",
                    'success': "TINYINT NOT NULL DEFAULT 1 COMMENT '是否成功'",
                }

                for col_name, col_def in columns_to_add.items():
                    if col_name not in existing_columns:
                        await cursor.execute(
                            f"ALTER TABLE schema_migrations ADD COLUMN {col_name} {col_def}"
                        )
                        logger.info(f"Added missing column '{col_name}' to schema_migrations")

    async def _get_executed_versions(self) -> set:
        """获取已执行的迁移版本号"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT version FROM schema_migrations WHERE success = 1"
                )
                rows = await cursor.fetchall()
                return {row[0] for row in rows}

    def _scan_migrations(self) -> List[Migration]:
        """扫描迁移文件目录，返回按版本号排序的迁移列表"""
        migrations = []

        if not self.MIGRATIONS_DIR.exists():
            logger.warning(f"Migrations directory not found: {self.MIGRATIONS_DIR}")
            return migrations

        for filepath in self.MIGRATIONS_DIR.glob("V*.sql"):
            match = self.MIGRATION_PATTERN.match(filepath.name)
            if match:
                version = int(match.group(1))
                description = match.group(2).replace("_", " ")

                # 计算文件校验和
                import hashlib
                content = filepath.read_bytes()
                checksum = hashlib.sha256(content).hexdigest()[:16]

                migrations.append(Migration(
                    version=version,
                    description=description,
                    filename=filepath.name,
                    filepath=filepath,
                    checksum=checksum,
                ))

        # 按版本号排序
        migrations.sort(key=lambda m: m.version)
        return migrations

    def _parse_sql_statements(self, sql_content: str) -> List[str]:
        """
        解析 SQL 文件内容，分割成独立的语句

        支持 DELIMITER 语法（用于存储过程等）
        """
        statements = []
        current = []
        delimiter = ";"

        for line in sql_content.split("\n"):
            stripped = line.strip()

            # 跳过空行和纯注释行
            if not stripped or stripped.startswith("--"):
                continue

            # 处理 DELIMITER 指令（MySQL 客户端命令，不发送到服务器）
            if stripped.upper().startswith("DELIMITER"):
                delimiter = stripped.split()[1] if len(stripped.split()) > 1 else ";"
                continue

            current.append(line)

            # 检测语句结束（使用当前分隔符）
            if stripped.endswith(delimiter):
                # 移除末尾的分隔符
                statement = "\n".join(current).strip()
                if delimiter != ";":
                    statement = statement[: -len(delimiter)].strip()
                if statement:
                    statements.append(statement)
                current = []

        # 处理最后一个没有分隔符的语句
        if current:
            statement = "\n".join(current).strip()
            if statement:
                statements.append(statement)

        return statements

    async def _execute_migration(self, migration: Migration) -> Tuple[bool, int]:
        """
        执行单个迁移

        Returns:
            (success, execution_time_ms)
        """
        pool = await self._get_pool()
        start_time = time.time()

        sql_content = migration.filepath.read_text(encoding="utf-8")
        statements = self._parse_sql_statements(sql_content)

        logger.info(f"Executing migration V{migration.version:03d}: {migration.description}")
        logger.info(f"  File: {migration.filename} ({len(statements)} statements)")

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for idx, statement in enumerate(statements, 1):
                    # 识别语句类型用于日志
                    stmt_upper = statement.upper().strip()
                    if stmt_upper.startswith("CREATE TABLE"):
                        stmt_type = "CREATE TABLE"
                    elif stmt_upper.startswith("CREATE DATABASE"):
                        stmt_type = "CREATE DATABASE"
                    elif stmt_upper.startswith("ALTER TABLE"):
                        stmt_type = "ALTER TABLE"
                    elif stmt_upper.startswith("INSERT"):
                        stmt_type = "INSERT"
                    elif stmt_upper.startswith("UPDATE"):
                        stmt_type = "UPDATE"
                    elif stmt_upper.startswith("DELETE"):
                        stmt_type = "DELETE"
                    else:
                        stmt_type = stmt_upper[:20] + "..."

                    try:
                        await cursor.execute(statement)
                        logger.debug(f"  [{idx}/{len(statements)}] {stmt_type} - OK")
                    except Exception as e:
                        error_msg = str(e).lower()
                        # 忽略 "已存在" 类型的错误 (幂等性)
                        if "already exists" in error_msg or "duplicate entry" in error_msg:
                            logger.debug(f"  [{idx}/{len(statements)}] {stmt_type} - Skipped (already exists)")
                        else:
                            logger.error(f"  [{idx}/{len(statements)}] {stmt_type} - FAILED")
                            logger.error(f"    Error: {e}")
                            raise

        execution_time_ms = int((time.time() - start_time) * 1000)
        return True, execution_time_ms

    async def _record_migration(
        self,
        migration: Migration,
        success: bool,
        execution_time_ms: int
    ) -> None:
        """记录迁移执行结果"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO schema_migrations
                        (version, description, filename, checksum, execution_time_ms, success)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        execution_time_ms = VALUES(execution_time_ms),
                        success = VALUES(success),
                        executed_at = CURRENT_TIMESTAMP
                """, (
                    migration.version,
                    migration.description,
                    migration.filename,
                    migration.checksum,
                    execution_time_ms,
                    1 if success else 0,
                ))

    async def run_migrations(self, dry_run: bool = False) -> int:
        """
        执行所有未完成的迁移

        Args:
            dry_run: 仅显示待执行的迁移，不实际执行

        Returns:
            执行的迁移数量
        """
        # 确保数据库存在（首次启动时创建）
        await self._ensure_database_exists()

        # 确保迁移记录表存在
        await self._ensure_migrations_table()

        # 获取已执行的版本
        executed_versions = await self._get_executed_versions()

        # 扫描迁移文件
        all_migrations = self._scan_migrations()

        # 过滤出待执行的迁移
        pending_migrations = [
            m for m in all_migrations
            if m.version not in executed_versions
        ]

        if not pending_migrations:
            logger.info("Database schema is up to date. No migrations to run.")
            return 0

        logger.info(f"Found {len(pending_migrations)} pending migration(s)")

        if dry_run:
            logger.info("Dry run mode - showing pending migrations:")
            for m in pending_migrations:
                logger.info(f"  - V{m.version:03d}: {m.description} ({m.filename})")
            return len(pending_migrations)

        # 执行迁移
        executed_count = 0
        for migration in pending_migrations:
            try:
                success, execution_time_ms = await self._execute_migration(migration)
                await self._record_migration(migration, success, execution_time_ms)
                logger.info(f"  Migration V{migration.version:03d} completed in {execution_time_ms}ms")
                executed_count += 1
            except Exception as e:
                logger.error(f"Migration V{migration.version:03d} failed: {e}")
                await self._record_migration(migration, False, 0)
                raise

        logger.info(f"Successfully executed {executed_count} migration(s)")
        return executed_count

    async def get_status(self) -> dict:
        """获取迁移状态"""
        await self._ensure_migrations_table()

        executed_versions = await self._get_executed_versions()
        all_migrations = self._scan_migrations()
        pending_migrations = [m for m in all_migrations if m.version not in executed_versions]

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT version, description, filename, executed_at, execution_time_ms
                    FROM schema_migrations
                    WHERE success = 1
                    ORDER BY version
                """)
                executed_records = await cursor.fetchall()

        return {
            "current_version": max(executed_versions) if executed_versions else 0,
            "total_migrations": len(all_migrations),
            "executed_count": len(executed_versions),
            "pending_count": len(pending_migrations),
            "pending_migrations": [
                {"version": m.version, "description": m.description, "filename": m.filename}
                for m in pending_migrations
            ],
            "executed_migrations": [
                {
                    "version": r["version"],
                    "description": r["description"],
                    "filename": r["filename"],
                    "executed_at": r["executed_at"].isoformat() if r["executed_at"] else None,
                    "execution_time_ms": r["execution_time_ms"],
                }
                for r in executed_records
            ],
        }


# 创建全局服务实例
migration_service = MigrationService()
