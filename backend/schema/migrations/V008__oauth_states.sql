-- OAuth state 持久化存储（替代内存字典，支持服务重启和多进程）
CREATE TABLE IF NOT EXISTS oauth_states (
    state VARCHAR(255) PRIMARY KEY COMMENT 'OAuth state token',
    provider VARCHAR(50) NOT NULL COMMENT 'github / google',
    expires_at TIMESTAMP(6) NOT NULL COMMENT '过期时间',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_expires (expires_at)
) ENGINE=InnoDB CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OAuth CSRF state 存储';
