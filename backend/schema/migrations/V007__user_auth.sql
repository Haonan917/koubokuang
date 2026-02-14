-- ============================================================================
-- V007: User Authentication Tables
-- ============================================================================
-- 用户认证系统：支持邮箱密码登录和 OAuth (GitHub/Google)
-- ============================================================================

-- 1. 用户主表
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(36) PRIMARY KEY COMMENT '用户 ID (UUID)',
    email VARCHAR(255) NOT NULL UNIQUE COMMENT '邮箱地址',
    password_hash VARCHAR(255) DEFAULT NULL COMMENT '密码哈希 (bcrypt)，OAuth 用户可为空',
    display_name VARCHAR(100) DEFAULT NULL COMMENT '显示名称',
    avatar_url VARCHAR(512) DEFAULT NULL COMMENT '头像 URL',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '状态: 0=待验证, 1=正常, 2=禁用',
    email_verified_at TIMESTAMP(6) DEFAULT NULL COMMENT '邮箱验证时间',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX idx_email (email),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='用户主表';


-- 2. OAuth 关联表
CREATE TABLE IF NOT EXISTS user_oauth_accounts (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL COMMENT '关联用户 ID',
    provider VARCHAR(50) NOT NULL COMMENT 'OAuth 提供商: github, google',
    provider_user_id VARCHAR(255) NOT NULL COMMENT '提供商用户 ID',
    provider_email VARCHAR(255) DEFAULT NULL COMMENT '提供商邮箱',
    access_token TEXT DEFAULT NULL COMMENT 'Access Token (加密存储)',
    refresh_token TEXT DEFAULT NULL COMMENT 'Refresh Token (加密存储)',
    token_expires_at TIMESTAMP(6) DEFAULT NULL COMMENT 'Token 过期时间',
    raw_data JSON DEFAULT NULL COMMENT '原始用户数据',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uk_provider_user (provider, provider_user_id),
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='用户 OAuth 关联表';


-- 3. 邮箱验证/密码重置令牌表
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL COMMENT '关联用户 ID',
    token VARCHAR(255) NOT NULL UNIQUE COMMENT '验证令牌',
    token_type VARCHAR(50) NOT NULL COMMENT '令牌类型: email_verify, password_reset',
    expires_at TIMESTAMP(6) NOT NULL COMMENT '过期时间',
    used_at TIMESTAMP(6) DEFAULT NULL COMMENT '使用时间',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_user_id (user_id),
    INDEX idx_token_type (token_type),
    INDEX idx_expires (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='邮箱验证/密码重置令牌';


-- 4. JWT Refresh Token 白名单表
CREATE TABLE IF NOT EXISTS user_refresh_tokens (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL COMMENT '关联用户 ID',
    token_hash VARCHAR(255) NOT NULL COMMENT 'Refresh Token 哈希',
    device_info VARCHAR(255) DEFAULT NULL COMMENT '设备信息',
    ip_address VARCHAR(45) DEFAULT NULL COMMENT 'IP 地址',
    expires_at TIMESTAMP(6) NOT NULL COMMENT '过期时间',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    UNIQUE KEY uk_token_hash (token_hash),
    INDEX idx_user_id (user_id),
    INDEX idx_expires (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='JWT Refresh Token 白名单';


-- 5. 为现有表添加 user_id 字段（用户数据隔离）
-- 使用存储过程实现条件添加列，避免重复列名错误

DELIMITER //

-- 添加列的通用存储过程
DROP PROCEDURE IF EXISTS add_column_if_not_exists//
CREATE PROCEDURE add_column_if_not_exists(
    IN p_table_name VARCHAR(64),
    IN p_column_name VARCHAR(64),
    IN p_column_definition VARCHAR(255)
)
BEGIN
    DECLARE column_exists INT DEFAULT 0;

    SELECT COUNT(*) INTO column_exists
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = p_table_name
      AND column_name = p_column_name;

    IF column_exists = 0 THEN
        SET @sql = CONCAT('ALTER TABLE ', p_table_name, ' ADD COLUMN ', p_column_name, ' ', p_column_definition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END//

-- 添加索引的通用存储过程
DROP PROCEDURE IF EXISTS add_index_if_not_exists//
CREATE PROCEDURE add_index_if_not_exists(
    IN p_table_name VARCHAR(64),
    IN p_index_name VARCHAR(64),
    IN p_column_name VARCHAR(64)
)
BEGIN
    DECLARE index_exists INT DEFAULT 0;

    SELECT COUNT(*) INTO index_exists
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = p_table_name
      AND index_name = p_index_name;

    IF index_exists = 0 THEN
        SET @sql = CONCAT('ALTER TABLE ', p_table_name, ' ADD INDEX ', p_index_name, ' (', p_column_name, ')');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END//

DELIMITER ;

-- agent_sessions 添加 user_id
CALL add_column_if_not_exists('agent_sessions', 'user_id', "VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID' AFTER session_id");
CALL add_index_if_not_exists('agent_sessions', 'idx_user_id', 'user_id');

-- agent_checkpoints 添加 user_id
CALL add_column_if_not_exists('agent_checkpoints', 'user_id', "VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID' AFTER id");
CALL add_index_if_not_exists('agent_checkpoints', 'idx_user_id', 'user_id');

-- agent_store 添加 user_id
CALL add_column_if_not_exists('agent_store', 'user_id', "VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID' AFTER id");
CALL add_index_if_not_exists('agent_store', 'idx_user_id', 'user_id');

-- 清理临时存储过程
DROP PROCEDURE IF EXISTS add_column_if_not_exists;
DROP PROCEDURE IF EXISTS add_index_if_not_exists;
