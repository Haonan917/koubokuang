# 数据库迁移指南

本项目使用轻量级的版本化迁移系统管理数据库 schema。

## 首次安装 vs 升级

### 首次安装（推荐）

如果你是首次安装本项目，使用整合的初始化脚本：

```bash
cd content_remix_agent/backend

# 方式一：直接执行
mysql -u root -p < schema/init_all.sql

# 方式二：在 MySQL 客户端中
mysql> source /path/to/schema/init_all.sql
```

这会一次性创建所有数据库和表，包括最新的用户认证系统。

### 从旧版本升级

如果你已经有旧版本的数据库，使用迁移系统：

```bash
cd content_remix_agent/backend

# 执行所有未完成的迁移
uv run python scripts/run_migrations.py
```

---

## 工作原理

1. **迁移文件命名**: `V{版本号}__{描述}.sql`
   - 版本号: 3 位数字，如 `001`, `002`, `003`
   - 描述: 使用下划线分隔的单词，如 `init_databases`, `add_user_table`
   - 示例: `V001__init_databases.sql`, `V006__add_user_preferences.sql`

2. **执行顺序**: 按版本号从小到大顺序执行

3. **幂等性**:
   - DDL 使用 `CREATE TABLE IF NOT EXISTS`
   - DML 使用 `ON DUPLICATE KEY UPDATE` 或 `INSERT IGNORE`
   - 这样可以安全地重复执行迁移

4. **版本记录**:
   - 已执行的迁移记录在 `schema_migrations` 表
   - 每个版本只执行一次

## 使用方式

### 应用启动时自动执行

应用启动时会自动检测并执行未完成的迁移，无需手动干预。

### 手动执行

```bash
cd content_remix_agent/backend

# 执行所有未完成的迁移
uv run python scripts/run_migrations.py

# 查看迁移状态
uv run python scripts/run_migrations.py --status

# 试运行（仅显示待执行的迁移，不实际执行）
uv run python scripts/run_migrations.py --dry-run
```

## 添加新迁移

### 场景 1: 添加新表

创建文件 `V006__add_user_preferences.sql`:

```sql
-- ============================================================================
-- V006: User Preferences Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL UNIQUE,
    theme VARCHAR(20) DEFAULT 'light',
    language VARCHAR(10) DEFAULT 'zh',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 场景 2: 修改已有表 (ALTER TABLE)

创建文件 `V007__add_avatar_to_preferences.sql`:

```sql
-- ============================================================================
-- V007: Add avatar column to user_preferences
-- ============================================================================

-- 注意: ALTER TABLE 不支持 IF NOT EXISTS，需要特殊处理
-- 方法 1: 使用存储过程检查列是否存在 (复杂)
-- 方法 2: 接受可能的 "Duplicate column" 错误 (迁移系统会忽略)

ALTER TABLE user_preferences
ADD COLUMN avatar_url VARCHAR(500) DEFAULT NULL COMMENT '头像 URL';
```

**重要**: ALTER TABLE 语句没有 `IF NOT EXISTS`，如果重复执行会报错。
迁移系统会捕获 "Duplicate column" 错误并跳过，但建议：
- 每个 ALTER 语句放在单独的迁移文件
- 或使用存储过程检查列是否存在

### 场景 3: 新增表 (OAuth state)

创建文件 `V008__oauth_states.sql`:

```sql
-- ============================================================================
-- V008: OAuth state storage
-- ============================================================================

CREATE TABLE IF NOT EXISTS oauth_states (
    state VARCHAR(255) PRIMARY KEY COMMENT 'OAuth state token',
    provider VARCHAR(50) NOT NULL COMMENT 'github / google',
    expires_at TIMESTAMP(6) NOT NULL COMMENT '过期时间',
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_expires (expires_at)
) ENGINE=InnoDB CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OAuth CSRF state 存储';
```

### 场景 4: 复杂数据迁移 (DML)

对于复杂的数据迁移，建议创建 Python 脚本：

```python
# scripts/migrate_xxx_data.py
async def migrate_data():
    # 复杂的数据迁移逻辑
    pass
```

然后在 SQL 迁移文件中只做 schema 变更，数据迁移单独执行。

## 最佳实践

1. **每个迁移做一件事**: 不要在一个迁移中做太多事情

2. **写好注释**: 说明迁移的目的和影响

3. **测试迁移**:
   - 在开发环境测试后再提交
   - 使用 `--dry-run` 先预览

4. **不要修改已执行的迁移**:
   - 如果需要修改，创建新的迁移文件
   - 已执行的迁移版本号不应该改变

5. **备份生产数据库**:
   - 执行迁移前备份数据库
   - 特别是涉及数据修改的迁移

## 故障排除

### 迁移失败

1. 检查错误日志
2. 修复问题后，可以：
   - 手动修复数据库状态
   - 删除 `schema_migrations` 表中对应的失败记录
   - 重新运行迁移

### 跳过某个迁移

如果需要跳过某个迁移（不推荐），可以手动插入记录：

```sql
INSERT INTO schema_migrations (version, description, filename, success)
VALUES (6, 'add user preferences', 'V006__add_user_preferences.sql', 1);
```

## 迁移历史

| 版本 | 文件 | 描述 |
|------|------|------|
| V001 | `V001__init_databases.sql` | 创建数据库 |
| V002 | `V002__agent_memory.sql` | Agent 记忆表 (checkpoints, store, sessions) |
| V003 | `V003__platform_cookies.sql` | 平台 Cookies 表 |
| V004 | `V004__llm_configs.sql` | LLM 配置表 |
| V005 | `V005__insight_modes.sql` | Insight Modes 表 + 默认数据 |
| V006 | `V006__llm_configs_multimodal.sql` | LLM 配置添加多模态支持字段 |
| V007 | `V007__user_auth.sql` | 用户认证系统 (users, oauth, tokens) |
| V008 | `V008__oauth_states.sql` | OAuth state 持久化存储 |
| V009 | `V009__media_ai_assets.sql` | Media-AI 资源表（用户语音/形象等资产） |
| V010 | `V010__platform_cookie_pool.sql` | 平台 Cookies 池（多账号轮换） |
| V011 | `V011__user_admin_flag.sql` | 用户管理员字段（is_admin） |
| V012 | `V012__usage_events.sql` | LLM/API 使用事件表（token/费用估算/计数） |
| V013 | `V013__ensure_media_ai_assets.sql` | 兜底创建 media_ai_* 表（修复历史迁移冲突） |
