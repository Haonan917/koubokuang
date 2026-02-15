-- ============================================================================
-- V012: Usage & billing events
-- ============================================================================
-- 目标：
-- - 记录 LLM token 使用与估算费用（用于运营侧看板/对账）
-- - 记录 API 请求计数（用于限流/审计/基础统计）
--
-- 注意：
-- - 这里做“事件表”，上层可再做日报/周报聚合表或离线汇总
-- - 表会增长，生产建议做分区或定期归档/清理

CREATE TABLE IF NOT EXISTS llm_usage_events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 (可空，匿名请求)',
    session_id VARCHAR(64) DEFAULT NULL COMMENT '会话/线程 ID',
    endpoint VARCHAR(255) NOT NULL COMMENT '触发的 API 路由',
    provider VARCHAR(64) DEFAULT NULL COMMENT 'LLM provider (openrouter/openai/ollama...)',
    model VARCHAR(128) NOT NULL COMMENT '模型名 (provider/model)',
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    total_tokens INT NOT NULL DEFAULT 0,
    estimated_cost_usd DECIMAL(12, 6) DEFAULT NULL COMMENT '估算费用(USD)',
    latency_ms INT DEFAULT NULL COMMENT '端到端耗时(毫秒)',
    success TINYINT NOT NULL DEFAULT 1 COMMENT '是否成功',
    error VARCHAR(255) DEFAULT NULL COMMENT '失败原因(截断)',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_created_at (created_at),
    INDEX idx_user_created (user_id, created_at),
    INDEX idx_model_created (model, created_at),
    CONSTRAINT fk_llm_usage_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LLM 使用事件表（token/费用估算）';


CREATE TABLE IF NOT EXISTS api_request_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 (可空，匿名请求)',
    method VARCHAR(10) NOT NULL,
    path VARCHAR(255) NOT NULL,
    status_code INT NOT NULL,
    latency_ms INT NOT NULL,
    request_bytes INT DEFAULT NULL,
    response_bytes INT DEFAULT NULL,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_created_at (created_at),
    INDEX idx_user_created (user_id, created_at),
    INDEX idx_path_created (path, created_at),
    CONSTRAINT fk_api_log_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='API 请求日志（计数/审计/统计）';

