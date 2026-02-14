-- ============================================================================
-- V001: Database Initialization
-- ============================================================================
-- Creates both MediaCrawlerPro and Remix Agent databases
-- Note: This migration runs with admin privileges before connecting to AGENT_DB
-- ============================================================================

-- Create MediaCrawlerPro database (for cookies, platform data)
CREATE DATABASE IF NOT EXISTS media_crawler_pro
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Create Remix Agent database (for Agent memory, sessions)
CREATE DATABASE IF NOT EXISTS remix_agent
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
