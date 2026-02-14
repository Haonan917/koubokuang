-- ============================================================================
-- V002: Agent Memory Tables
-- ============================================================================
-- LangGraph Agent 状态存储：检查点、中间写入、长期记忆
-- ============================================================================

-- 1. Agent 检查点表 (短期记忆 - Checkpointer)
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

    UNIQUE KEY uk_checkpoint (thread_id(64), checkpoint_ns(64), checkpoint_id(64)),
    INDEX idx_thread_ns (thread_id(64), checkpoint_ns(64)),
    INDEX idx_parent (parent_checkpoint_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 检查点存储';


-- 2. Agent 检查点中间写入表
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

    UNIQUE KEY uk_write (thread_id(64), checkpoint_ns(64), checkpoint_id(64), task_id(64), idx),
    INDEX idx_checkpoint (thread_id(64), checkpoint_ns(64), checkpoint_id(64))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 检查点中间写入';


-- 3. Agent 长期记忆存储表 (Store)
CREATE TABLE IF NOT EXISTS agent_store (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    namespace VARCHAR(1024) NOT NULL COMMENT '命名空间 (JSON 数组序列化)',
    `key` VARCHAR(255) NOT NULL COMMENT '存储键',
    value LONGBLOB NOT NULL COMMENT '存储值 (JSON)',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uk_ns_key (namespace(191), `key`),
    INDEX idx_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 长期记忆存储';


-- 4. 会话元数据表
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


-- 5. 会话消息表
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
