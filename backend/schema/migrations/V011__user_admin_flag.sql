-- ============================================================================
-- V011: User admin flag
-- ============================================================================
-- 为管理后台添加最小权限字段：is_admin
--
-- 说明：
-- - 使用存储过程实现条件添加列/索引，避免重复执行报错
-- - 不强制创建默认管理员（由运维/脚本设置）

DELIMITER //

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

DROP PROCEDURE IF EXISTS add_index_if_not_exists//
CREATE PROCEDURE add_index_if_not_exists(
    IN p_table_name VARCHAR(64),
    IN p_index_name VARCHAR(64),
    IN p_index_columns VARCHAR(255)
)
BEGIN
    DECLARE index_exists INT DEFAULT 0;

    SELECT COUNT(*) INTO index_exists
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = p_table_name
      AND index_name = p_index_name;

    IF index_exists = 0 THEN
        SET @sql = CONCAT('ALTER TABLE ', p_table_name, ' ADD INDEX ', p_index_name, ' (', p_index_columns, ')');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END//

DELIMITER ;

CALL add_column_if_not_exists('users', 'is_admin', "TINYINT NOT NULL DEFAULT 0 COMMENT '是否管理员: 0=否, 1=是' AFTER status");
CALL add_index_if_not_exists('users', 'idx_is_admin', 'is_admin');

DROP PROCEDURE IF EXISTS add_column_if_not_exists;
DROP PROCEDURE IF EXISTS add_index_if_not_exists;

