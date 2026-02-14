-- V006: Add Multimodal Support Field to LLM Configs
-- 增加多模态支持字段，标识模型是否支持图片理解

ALTER TABLE llm_configs
    ADD COLUMN support_multimodal TINYINT DEFAULT 0
    COMMENT '是否支持多模态（图片理解）: 0=否, 1=是'
    AFTER reasoning_effort;
