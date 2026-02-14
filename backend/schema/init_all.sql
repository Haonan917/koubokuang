-- ============================================================================
-- Content Remix Agent - 完整初始化脚本 (首次安装)
-- ============================================================================
-- 适用于: 首次安装，一次性创建所有表结构
-- 运行方式:
--   mysql -u root -p < init_all.sql
--   或在 MySQL 客户端中执行: source /path/to/init_all.sql
--
-- 注意: 如果是从旧版本升级，请使用迁移系统:
--   uv run python scripts/run_migrations.py
-- ============================================================================

-- ============================================================================
-- 1. 创建数据库
-- ============================================================================
CREATE DATABASE IF NOT EXISTS media_crawler_pro
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS remix_agent
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Grant privileges
-- NOTE: Managed databases often disallow GRANT; keep privileges in your DB admin layer.

-- 切换到 remix_agent 数据库
USE remix_agent;


-- ============================================================================
-- 2. 用户认证表
-- ============================================================================

-- 2.1 用户主表
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

-- 2.2 OAuth 关联表
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

-- 2.3 邮箱验证/密码重置令牌表
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

-- 2.4 JWT Refresh Token 白名单表
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


-- ============================================================================
-- 3. Agent 记忆存储表
-- ============================================================================

-- 3.1 Agent 检查点表 (短期记忆 - Checkpointer)
CREATE TABLE IF NOT EXISTS agent_checkpoints (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
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
    INDEX idx_created (created_at),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 检查点存储';

-- 3.2 Agent 检查点中间写入表
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

-- 3.3 Agent 长期记忆存储表 (Store)
CREATE TABLE IF NOT EXISTS agent_store (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    namespace VARCHAR(1024) NOT NULL COMMENT '命名空间 (JSON 数组序列化)',
    `key` VARCHAR(255) NOT NULL COMMENT '存储键',
    value LONGBLOB NOT NULL COMMENT '存储值 (JSON)',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uk_ns_key (namespace(191), `key`),
    INDEX idx_updated (updated_at),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='LangGraph Agent 长期记忆存储';

-- 3.4 会话元数据表
CREATE TABLE IF NOT EXISTS agent_sessions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE COMMENT '会话 ID (UUID)',
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    title VARCHAR(255) NOT NULL DEFAULT '新对话' COMMENT '会话标题',
    first_message TEXT COMMENT '首条消息内容',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX idx_updated (updated_at DESC),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Agent 会话元数据';

-- 3.5 会话消息表
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


-- ============================================================================
-- 4. Media AI 资产表
-- ============================================================================

CREATE TABLE IF NOT EXISTS media_ai_voice_clones (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    voice_id VARCHAR(128) NOT NULL COMMENT 'Voicv voice_id',
    title VARCHAR(255) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    source_type VARCHAR(50) DEFAULT NULL,
    source_url TEXT DEFAULT NULL,
    sample_audio_url TEXT DEFAULT NULL,
    full_audio_url TEXT DEFAULT NULL,
    full_audio_path TEXT DEFAULT NULL,
    clip_audio_url TEXT DEFAULT NULL,
    clip_audio_path TEXT DEFAULT NULL,
    expression_profile JSON DEFAULT NULL,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uk_user_voice (user_id, voice_id),
    INDEX idx_user_created (user_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='语音克隆记录';

CREATE TABLE IF NOT EXISTS media_ai_avatars (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    avatar_id VARCHAR(128) NOT NULL COMMENT 'Avatar ID',
    title VARCHAR(255) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    source_type VARCHAR(50) DEFAULT NULL,
    source_url TEXT DEFAULT NULL,
    full_video_url TEXT DEFAULT NULL,
    full_video_path TEXT DEFAULT NULL,
    clip_video_url TEXT DEFAULT NULL,
    clip_video_path TEXT DEFAULT NULL,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uk_user_avatar (user_id, avatar_id),
    INDEX idx_user_created (user_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='形象克隆记录';

CREATE TABLE IF NOT EXISTS media_ai_tts_results (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    voice_id VARCHAR(128) DEFAULT NULL,
    text LONGTEXT DEFAULT NULL,
    tagged_text LONGTEXT DEFAULT NULL,
    audio_url TEXT DEFAULT NULL,
    original_audio_url TEXT DEFAULT NULL,
    format VARCHAR(20) DEFAULT NULL,
    speed DECIMAL(6, 3) DEFAULT NULL,
    emotion VARCHAR(50) DEFAULT NULL,
    tone_tags JSON DEFAULT NULL,
    effect_tags JSON DEFAULT NULL,
    sentence_emotions JSON DEFAULT NULL,
    auto_emotion TINYINT DEFAULT NULL,
    auto_breaks TINYINT DEFAULT NULL,
    voice_profile JSON DEFAULT NULL,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_voice_created (voice_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='文本转语音结果';

CREATE TABLE IF NOT EXISTS media_ai_lipsync_results (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT NULL COMMENT '关联用户 ID',
    generation_id VARCHAR(128) DEFAULT NULL,
    model VARCHAR(64) DEFAULT NULL,
    status VARCHAR(32) DEFAULT NULL,
    output_url TEXT DEFAULT NULL,
    video_url TEXT DEFAULT NULL,
    audio_url TEXT DEFAULT NULL,
    video_source_type VARCHAR(50) DEFAULT NULL,
    audio_source_type VARCHAR(50) DEFAULT NULL,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uk_user_generation (user_id, generation_id),
    INDEX idx_user_created (user_id, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='对口型生成记录';


-- ============================================================================
-- 4. 平台 Cookies 表
-- ============================================================================
CREATE TABLE IF NOT EXISTS platform_cookies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    platform VARCHAR(20) NOT NULL COMMENT '平台标识: xhs/dy/bili/ks',
    cookies TEXT NOT NULL COMMENT 'Cookie 字符串',
    status TINYINT DEFAULT 0 COMMENT '状态: 0=有效, 1=过期, 2=禁用',
    remark VARCHAR(255) DEFAULT NULL COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_platform (platform)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='平台 Cookies 管理';


-- ============================================================================
-- 5. LLM 配置表
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
    support_multimodal TINYINT DEFAULT 0 COMMENT '是否支持多模态（图片理解）: 0=否, 1=是',

    -- 元数据
    description VARCHAR(255) COMMENT '配置描述/备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- 索引
    UNIQUE KEY uk_config_name (config_name),
    INDEX idx_provider (provider),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM 配置管理表';


-- ============================================================================
-- 6. 分析模式配置表
-- ============================================================================
CREATE TABLE IF NOT EXISTS insight_modes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mode_key VARCHAR(50) NOT NULL COMMENT '模式标识 (如 summarize, analyze)',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    sort_order INT DEFAULT 0 COMMENT '显示排序',

    -- 显示信息
    label_zh VARCHAR(100) NOT NULL COMMENT '中文名称',
    label_en VARCHAR(100) NOT NULL COMMENT '英文名称',
    description_zh VARCHAR(500) COMMENT '中文描述',
    description_en VARCHAR(500) COMMENT '英文描述',
    prefill_zh VARCHAR(200) COMMENT '中文输入预填充',
    prefill_en VARCHAR(200) COMMENT '英文输入预填充',

    -- 视觉配置
    icon VARCHAR(50) DEFAULT 'smart_toy' COMMENT 'Material Symbols 图标名',
    color VARCHAR(20) DEFAULT 'cyan' COMMENT '颜色主题 (cyan/orange/pink/purple)',

    -- 意图识别关键词
    keywords_zh TEXT COMMENT '中文关键词 (逗号分隔)',
    keywords_en TEXT COMMENT '英文关键词 (逗号分隔)',

    -- System Prompt
    system_prompt TEXT NOT NULL COMMENT '模式专属提示词',

    -- 系统标记
    is_system TINYINT DEFAULT 0 COMMENT '系统内置 (1=不可删除)',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_mode_key (mode_key),
    INDEX idx_is_active (is_active),
    INDEX idx_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分析模式配置表';


-- ============================================================================
-- 7. 插入默认分析模式
-- ============================================================================
INSERT INTO insight_modes (
    mode_key, is_active, sort_order,
    label_zh, label_en, description_zh, description_en, prefill_zh, prefill_en,
    icon, color, keywords_zh, keywords_en, system_prompt, is_system
) VALUES
-- 1. 精华提炼 (summarize)
(
    'summarize', 1, 1,
    '精华提炼', 'Summarize',
    '快速掌握核心要点，节省阅读时间', 'Quickly grasp core points, save reading time',
    '提炼这个内容的核心要点', 'Extract key points from this content',
    'format_list_bulleted', 'cyan',
    '总结,提炼,精简,要点,核心,概括,快速了解', 'summarize,summary,key points,extract,brief',
    '## 当前模式：精华提炼

你的任务是帮助用户快速掌握内容精华：

### 核心目标
- 提炼核心要点和关键信息
- 删除冗余、重复的信息
- 生成精简版本（不超过原文 50%）
- 保留最有价值的洞察

### 输出重点
1. **核心要点列表**: 3-5 个最重要的信息点
2. **金句提取**: 原文中最有价值的 2-3 句话
3. **一句话总结**: 用一句话概括全文精华
4. **可执行建议**: 用户可以立即采取的行动

### 风格要求
- 简洁明了，去除废话
- 层次清晰，便于快速浏览
- 保留原文精华，不遗漏关键信息',
    1
),
-- 2. 深度拆解 (analyze)
(
    'analyze', 1, 2,
    '深度拆解', 'Deep Analysis',
    '以教学视角解构创作技巧，学习爆款方法论', 'Deconstruct creation techniques from a teaching perspective',
    '深度拆解这个内容的创作技巧', 'Deep analyze the creation techniques of this content',
    'layers', 'orange',
    '分析,拆解,学习,为什么,怎么做到的,技巧,方法论', 'analyze,analysis,learn,why,how,technique,method',
    '## 当前模式：深度拆解

你的任务是以教学视角帮助用户系统学习创作方法：

### 核心目标
- 解构内容的每个结构和技巧
- 分析创作技巧背后的逻辑和原理
- 提供可复用的方法论和框架
- 解释"为什么有效"而不仅仅是"是什么"

### 输出重点
1. **结构化拆解**: 按时间线或逻辑线拆解每个部分
2. **技巧原理解释**: 每个技巧为什么有效，心理学/传播学原理
3. **方法论总结**: 提炼可复用的创作公式或框架
4. **实战应用建议**: 如何将这些技巧应用到自己的创作中

### 风格要求
- 专业深入，有理有据
- 教学视角，循循善诱
- 理论与实践结合
- 提供可操作的指导',
    1
),
-- 3. 模板学习 (template)
(
    'template', 1, 3,
    '模板学习', 'Template',
    '提取可复用的创作模板，应用到你的原创主题', 'Extract reusable templates for your original topics',
    '提取这个内容的可复用模板', 'Extract reusable templates from this content',
    'article', 'pink',
    '模板,套路,框架,结构,公式,仿写,照着写', 'template,pattern,framework,structure,formula,imitate',
    '## 当前模式：模板学习

你的任务是帮助用户提取可复用的创作模板：

### 核心目标
- 提取成功的结构模板（开头套路、叙事结构、收尾方式）
- 分析爆款元素的具体应用方式
- 输出可直接填充的框架模板
- 标注每个模块的作用和替换方法

### 输出重点
1. **结构模板**: 可复用的内容框架，带有占位符
2. **开头模板**: 3 种可选的开头套路
3. **爆款元素清单**: 本内容使用的爆款元素及应用方式
4. **填充指南**: 如何用自己的内容填充模板

### 风格要求
- 模板清晰，便于复制
- 标注每个部分的作用
- 提供替换示例
- **重要提醒**：模板仅供学习参考，用户需要用自己的原创内容填充',
    1
),
-- 4. 风格探索 (style_explore)
(
    'style_explore', 1, 4,
    '风格探索', 'Style Explore',
    '探索同一话题的不同表达风格和视角', 'Explore different styles and perspectives on the same topic',
    '探索这个内容的不同表达风格', 'Explore different expression styles of this content',
    'palette', 'purple',
    '风格,换种说法,不同角度,改写,变体,多种版本', 'style,rephrase,different angle,rewrite,variation,version',
    '## 当前模式：风格探索

你的任务是帮助用户探索多元表达风格：

### 核心目标
- 提供同一话题的不同表达风格
- 尝试不同的叙事角度和语气
- 展示多种创意方向供选择
- 帮助用户找到适合自己的表达方式

### 输出重点
1. **风格变体**: 至少 3 种不同风格的表达版本
   - 专业严谨版
   - 轻松幽默版
   - 故事化版本
   - 数据驱动版
2. **风格特点分析**: 每种风格的适用场景和优劣势
3. **角度对比**: 不同叙事角度的效果差异
4. **个性化建议**: 根据内容特点推荐最适合的风格

### 风格要求
- 展示多样性，启发创意
- 每种风格特点鲜明
- 提供选择依据
- 鼓励用户尝试和创新',
    1
)
ON DUPLICATE KEY UPDATE
    label_zh = VALUES(label_zh),
    label_en = VALUES(label_en),
    description_zh = VALUES(description_zh),
    description_en = VALUES(description_en),
    prefill_zh = VALUES(prefill_zh),
    prefill_en = VALUES(prefill_en),
    icon = VALUES(icon),
    color = VALUES(color),
    keywords_zh = VALUES(keywords_zh),
    keywords_en = VALUES(keywords_en),
    system_prompt = VALUES(system_prompt),
    is_system = VALUES(is_system);

-- ============================================================================
-- 8. OAuth state 表
-- ============================================================================
CREATE TABLE IF NOT EXISTS oauth_states (
    state VARCHAR(255) PRIMARY KEY COMMENT 'OAuth state token',
    provider VARCHAR(50) NOT NULL COMMENT 'github / google',
    expires_at TIMESTAMP(6) NOT NULL COMMENT '过期时间',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_expires (expires_at)
) ENGINE=InnoDB CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OAuth CSRF state 存储';

-- ============================================================================
-- 9. 迁移记录表 (用于追踪已执行的迁移)
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version INT NOT NULL UNIQUE COMMENT '迁移版本号',
    description VARCHAR(255) NOT NULL COMMENT '迁移描述',
    filename VARCHAR(255) NOT NULL COMMENT '迁移文件名',
    checksum VARCHAR(64) COMMENT '文件校验和 (SHA-256)',
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
    execution_time_ms INT COMMENT '执行耗时 (毫秒)',
    success TINYINT NOT NULL DEFAULT 1 COMMENT '是否成功',
    INDEX idx_version (version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据库迁移记录表';

-- 标记所有迁移已完成 (首次安装包含所有结构)
INSERT INTO schema_migrations (version, description, filename, success) VALUES
    (1, 'init databases', 'V001__init_databases.sql', 1),
    (2, 'agent memory', 'V002__agent_memory.sql', 1),
    (3, 'platform cookies', 'V003__platform_cookies.sql', 1),
    (4, 'llm configs', 'V004__llm_configs.sql', 1),
    (5, 'insight modes', 'V005__insight_modes.sql', 1),
    (6, 'llm configs multimodal', 'V006__llm_configs_multimodal.sql', 1),
    (7, 'user auth', 'V007__user_auth.sql', 1),
    (8, 'oauth states', 'V008__oauth_states.sql', 1)
ON DUPLICATE KEY UPDATE executed_at = CURRENT_TIMESTAMP;


-- ============================================================================
-- 完成！
-- ============================================================================
SELECT '✅ Content Remix Agent 数据库初始化完成！' AS message;
SELECT '📦 已创建数据库: remix_agent' AS info;
SELECT '📋 已创建表: users, user_oauth_accounts, email_verification_tokens, user_refresh_tokens,' AS tables1;
SELECT '            agent_checkpoints, agent_checkpoint_writes, agent_store, agent_sessions,' AS tables2;
SELECT '            agent_session_messages, platform_cookies, llm_configs, insight_modes, oauth_states' AS tables3;
