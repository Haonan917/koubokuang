-- ============================================================================
-- [DEPRECATED] 此文件已废弃
-- ============================================================================
-- 首次安装请使用: schema/init_all.sql
-- 升级请使用迁移系统: uv run python scripts/run_migrations.py
-- ============================================================================

-- ============================================================================
-- Content Remix Agent - Database Initialization Script
-- ============================================================================
-- This script runs on first MySQL container startup
-- Creates both MediaCrawlerPro and Remix Agent databases
-- ============================================================================

-- Create MediaCrawlerPro database (for cookies, platform data)
CREATE DATABASE IF NOT EXISTS media_crawler_pro
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Create Remix Agent database (for Agent memory, sessions)
CREATE DATABASE IF NOT EXISTS remix_agent
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Grant privileges
-- NOTE: Managed databases often disallow GRANT; keep privileges in your DB admin layer.

-- Switch to remix_agent database for subsequent scripts
USE remix_agent;
