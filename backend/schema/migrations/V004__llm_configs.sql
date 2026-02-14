-- ============================================================================
-- V004: LLM Configuration Table
-- ============================================================================
-- 用于存储多个 LLM 提供商的配置信息
-- 支持: OpenAI-compatible (Kimi/MiniMax/GPT), Anthropic, DeepSeek, Ollama
-- ============================================================================

CREATE TABLE IF NOT EXISTS llm_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- 配置标识
    config_name VARCHAR(50) NOT NULL COMMENT '配置名称，如 default, reasoning, fast',
    provider VARCHAR(20) NOT NULL COMMENT '提供商: openai / anthropic / deepseek / ollama',
    is_active TINYINT DEFAULT 0 COMMENT '是否为当前激活配置: 0=否, 1=是',

    -- 核心配置
    api_key VARCHAR(1024) COMMENT 'API Key',
    base_url VARCHAR(255) COMMENT 'API 基础 URL',
    model_name VARCHAR(255) NOT NULL COMMENT '模型名称',

    -- 思考/推理配置 (仅部分模型需要)
    enable_thinking TINYINT DEFAULT 0 COMMENT '启用思考模式: 0=否, 1=是',
    thinking_budget_tokens INT DEFAULT 4096 COMMENT 'Anthropic Extended Thinking token 预算',
    reasoning_effort VARCHAR(20) DEFAULT 'high' COMMENT 'OpenAI GPT-5 推理强度: none/low/medium/high/xhigh',

    -- 元数据
    description VARCHAR(255) COMMENT '配置描述/备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- 索引
    UNIQUE KEY uk_config_name (config_name),
    INDEX idx_provider (provider),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM 配置管理表';
