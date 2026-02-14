-- ============================================================================
-- [DEPRECATED] 此文件已废弃
-- ============================================================================
-- 首次安装请使用: schema/init_all.sql
-- 升级请使用迁移系统: uv run python scripts/run_migrations.py
-- ============================================================================

-- ============================================================================
-- Content Remix Agent - MySQL Memory Storage DDL
-- ============================================================================
-- 创建数据库: CREATE DATABASE IF NOT EXISTS remix_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 使用数据库: USE remix_agent;
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Agent 检查点表 (短期记忆 - Checkpointer)
-- 存储 LangGraph 状态快照，支持会话历史回溯
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_checkpoints (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL COMMENT '会话线程 ID',
    checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '' COMMENT '检查点命名空间',
    checkpoint_id VARCHAR(255) NOT NULL COMMENT '检查点 ID (UUID)',
    parent_checkpoint_id VARCHAR(255) DEFAULT NULL COMMENT '父检查点 ID',
    checkpoint LONGBLOB NOT NULL COMMENT '序列化的检查点数据',
    metadata LONGBLOB COMMENT '检查点元数据',
    channel_versions JSON COMMENT '通道版本信息',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    -- 复合唯一索引：确保同一线程/命名空间下检查点 ID 唯一
    UNIQUE KEY uk_checkpoint (thread_id(64), checkpoint_ns(64), checkpoint_id(64)),
    -- 查询索引
    INDEX idx_thread_ns (thread_id(64), checkpoint_ns(64)),
    INDEX idx_parent (parent_checkpoint_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 检查点存储';


-- ----------------------------------------------------------------------------
-- 2. Agent 检查点中间写入表
-- 存储 pending writes，用于支持 Agent 状态恢复
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_checkpoint_writes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL COMMENT '会话线程 ID',
    checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '' COMMENT '检查点命名空间',
    checkpoint_id VARCHAR(255) NOT NULL COMMENT '关联的检查点 ID',
    task_id VARCHAR(255) NOT NULL COMMENT '任务 ID',
    task_path VARCHAR(255) NOT NULL DEFAULT '' COMMENT '任务路径',
    idx INT NOT NULL COMMENT '写入序号',
    channel VARCHAR(255) NOT NULL COMMENT '通道名称',
    `type` VARCHAR(255) DEFAULT NULL COMMENT '写入类型',
    `blob` LONGBLOB COMMENT '序列化的写入数据',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    -- 复合唯一索引
    UNIQUE KEY uk_write (thread_id(64), checkpoint_ns(64), checkpoint_id(64), task_id(64), idx),
    -- 查询索引
    INDEX idx_checkpoint (thread_id(64), checkpoint_ns(64), checkpoint_id(64))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 检查点中间写入';


-- ----------------------------------------------------------------------------
-- 3. Agent 长期记忆存储表 (Store)
-- 存储跨会话的持久化数据，支持命名空间和键值查询
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_store (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    namespace VARCHAR(1024) NOT NULL COMMENT '命名空间 (JSON 数组序列化)',
    `key` VARCHAR(255) NOT NULL COMMENT '存储键',
    value LONGBLOB NOT NULL COMMENT '存储值 (JSON)',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    -- 复合唯一索引 (namespace 前缀索引)
    UNIQUE KEY uk_ns_key (namespace(191), `key`),
    -- 更新时间索引
    INDEX idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 长期记忆存储';


-- ----------------------------------------------------------------------------
-- 4. 会话元数据表
-- 存储会话列表、标题等元信息
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_sessions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE COMMENT '会话 ID (UUID)',
    title VARCHAR(255) NOT NULL DEFAULT '新对话' COMMENT '会话标题',
    first_message TEXT COMMENT '首条消息内容',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX idx_updated (updated_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Agent 会话元数据';


-- ----------------------------------------------------------------------------
-- 5. 会话消息表
-- 存储会话中的消息历史
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_session_messages (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(255) NOT NULL UNIQUE COMMENT '消息 ID (UUID)',
    session_id VARCHAR(255) NOT NULL COMMENT '关联会话 ID',
    role VARCHAR(50) NOT NULL COMMENT '角色: user/assistant/system',
    content LONGTEXT NOT NULL COMMENT '消息内容',
    segments_json JSON DEFAULT NULL COMMENT '消息 segments 元数据 (thinking, tool_call 等)',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_session (session_id),
    INDEX idx_session_time (session_id, created_at),
    FOREIGN KEY (session_id) REFERENCES agent_sessions(session_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Agent 会话消息历史';


-- ----------------------------------------------------------------------------
-- 升级脚本：为已存在的表添加 segments_json 字段
-- ----------------------------------------------------------------------------
-- ALTER TABLE agent_session_messages
-- ADD COLUMN segments_json JSON DEFAULT NULL
-- COMMENT '消息 segments 元数据 (thinking, tool_call 等)'
-- AFTER content;
