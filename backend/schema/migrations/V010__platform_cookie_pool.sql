-- ============================================================================
-- V009: Platform Cookie Pool
-- ============================================================================
-- 每个平台支持多条 cookies，支持失败自动降级与冷却切换
-- ============================================================================

CREATE TABLE IF NOT EXISTS platform_cookie_pool (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    platform VARCHAR(20) NOT NULL COMMENT '平台标识: xhs/dy/bili/ks',
    account_name VARCHAR(100) DEFAULT NULL COMMENT '账号标识（可选）',
    cookies MEDIUMTEXT NOT NULL COMMENT 'Cookie 字符串',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '状态: 0=有效,1=过期,2=禁用',
    fail_count INT NOT NULL DEFAULT 0 COMMENT '连续失败次数',
    priority INT NOT NULL DEFAULT 100 COMMENT '优先级，越大越优先',
    cooldown_until DATETIME DEFAULT NULL COMMENT '冷却截止时间',
    last_success_at DATETIME DEFAULT NULL COMMENT '最近成功时间',
    last_failure_at DATETIME DEFAULT NULL COMMENT '最近失败时间',
    remark VARCHAR(255) DEFAULT NULL COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_platform_status (platform, status),
    INDEX idx_platform_cooldown (platform, cooldown_until),
    INDEX idx_platform_priority (platform, priority),
    INDEX idx_platform_updated (platform, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='平台 Cookies 池';
