-- ============================================================================
-- V003: Platform Cookies Table
-- ============================================================================
-- 用于存储各平台的 Cookies，解耦对外部数据库的依赖
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
