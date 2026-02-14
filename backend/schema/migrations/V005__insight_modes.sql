-- ============================================================================
-- V005: Insight Modes Table
-- ============================================================================
-- 分析模式配置表，用于动态管理 System Prompt Mode
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
-- 插入 4 个默认模式 (系统内置)
-- 使用 ON DUPLICATE KEY UPDATE 保证幂等性
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
