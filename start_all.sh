#!/bin/bash
set -e

cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

SIGN_PID=""
DOWN_PID=""
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo -e "${YELLOW}正在关闭服务...${NC}"
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && echo -e "${BLUE}[前端] 已停止${NC}"
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && echo -e "${RED}[后端] 已停止${NC}"
  [ -n "$DOWN_PID" ] && kill "$DOWN_PID" 2>/dev/null && echo -e "${PURPLE}[下载服务] 已停止${NC}"
  [ -n "$SIGN_PID" ] && kill "$SIGN_PID" 2>/dev/null && echo -e "${PURPLE}[签名服务] 已停止${NC}"
  wait 2>/dev/null
  echo -e "${GREEN}所有服务已关闭${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM

source_env_file() {
  local env_file="$1"
  if [ -f "$env_file" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
  fi
}

load_service_env() {
  local service_name="$1"
  source_env_file "config/common.env"
  source_env_file "config/${service_name}.env"
}

echo -e "${CYAN}检查依赖...${NC}"
if ! command -v uv &>/dev/null; then
  echo -e "${RED}错误: 未找到 uv，请先安装: https://docs.astral.sh/uv/${NC}"
  exit 1
fi
if ! command -v npm &>/dev/null; then
  echo -e "${RED}错误: 未找到 npm，请先安装 Node.js${NC}"
  exit 1
fi

# 默认加载公共配置
load_service_env "backend"
load_service_env "download"

# 依赖服务检查策略
STRICT_DEP_CHECK="${STRICT_DEP_CHECK:-1}"

dep_check_fail_or_warn() {
  local message="$1"
  if [ "$STRICT_DEP_CHECK" = "1" ]; then
    echo -e "${RED}${message}${NC}"
    exit 1
  else
    echo -e "${YELLOW}${message} (继续启动)${NC}"
  fi
}

echo -e "${CYAN}加载环境变量...${NC}"

check_mysql() {
  local host="${AGENT_DB_HOST:-localhost}"
  local port="${AGENT_DB_PORT:-3306}"
  local user="${AGENT_DB_USER:-root}"
  local password="${AGENT_DB_PASSWORD:-}"

  if ! command -v mysqladmin &>/dev/null; then
    dep_check_fail_or_warn "[依赖] 未找到 mysqladmin，无法检查 MySQL"
    return
  fi

  if [ -n "$password" ]; then
    mysqladmin --connect-timeout=3 ping -h "$host" -P "$port" -u "$user" -p"$password" >/dev/null 2>&1 \
      || dep_check_fail_or_warn "[依赖] MySQL 不可用: ${host}:${port}, user=${user}"
  else
    mysqladmin --connect-timeout=3 ping -h "$host" -P "$port" -u "$user" >/dev/null 2>&1 \
      || dep_check_fail_or_warn "[依赖] MySQL 不可用: ${host}:${port}, user=${user}"
  fi
  echo -e "${GREEN}[依赖] MySQL 可用: ${host}:${port}${NC}"
}

check_redis_if_needed() {
  local enable_proxy="${ENABLE_IP_PROXY:-false}"
  local cache_type="${USE_CACHE_TYPE:-redis}"
  if [[ "${enable_proxy,,}" != "true" && "$cache_type" != "redis" ]]; then
    echo -e "${YELLOW}[依赖] 已跳过 Redis 检查 (ENABLE_IP_PROXY=${enable_proxy}, USE_CACHE_TYPE=${cache_type})${NC}"
    return
  fi

  local host="${REDIS_DB_HOST:-127.0.0.1}"
  local port="${REDIS_DB_PORT:-6379}"
  local db="${REDIS_DB_NUM:-0}"
  local password="${REDIS_DB_PWD:-}"

  if ! command -v redis-cli &>/dev/null; then
    dep_check_fail_or_warn "[依赖] 未找到 redis-cli，无法检查 Redis"
    return
  fi

  local ping_result=""
  if [ -n "$password" ]; then
    ping_result="$(redis-cli -h "$host" -p "$port" -n "$db" -a "$password" --no-auth-warning ping 2>/dev/null || true)"
  else
    ping_result="$(redis-cli -h "$host" -p "$port" -n "$db" ping 2>/dev/null || true)"
  fi

  if [ "$ping_result" != "PONG" ]; then
    dep_check_fail_or_warn "[依赖] Redis 不可用: ${host}:${port}/${db}"
  fi
  echo -e "${GREEN}[依赖] Redis 可用: ${host}:${port}/${db}${NC}"
}

echo -e "${CYAN}检查依赖服务...${NC}"
check_mysql
check_redis_if_needed

# 是否在启动前初始化 MediaCrawlerPro-Python 的 media_crawler_pro 表结构
INIT_MEDIA_CRAWLER_PRO_DB_ON_START="${INIT_MEDIA_CRAWLER_PRO_DB_ON_START:-0}"

init_media_crawler_pro_db_if_needed() {
  if [ "$INIT_MEDIA_CRAWLER_PRO_DB_ON_START" != "1" ]; then
    return
  fi
  if ! command -v mysql &>/dev/null; then
    dep_check_fail_or_warn "[依赖] 未找到 mysql 客户端，无法初始化 media_crawler_pro"
    return
  fi

  local host="${CRAWLER_DB_HOST:-127.0.0.1}"
  local port="${CRAWLER_DB_PORT:-3306}"
  local user="${CRAWLER_DB_USER:-root}"
  local password="${CRAWLER_DB_PASSWORD:-}"
  local db="${CRAWLER_DB_NAME:-media_crawler_pro}"
  local schema_file="services/DownloadServer/DownloadServer/schema/media_crawler_pro_tables.sql"

  if [ ! -f "$schema_file" ]; then
    dep_check_fail_or_warn "[依赖] 找不到 schema 文件: ${schema_file}"
    return
  fi

  echo -e "${CYAN}[依赖] 检查并初始化 media_crawler_pro（仅空库时执行）...${NC}"

  # 1) Ensure DB exists
  if [ -n "$password" ]; then
    mysql --protocol=tcp -h "$host" -P "$port" -u "$user" -p"$password" -e "CREATE DATABASE IF NOT EXISTS \`$db\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" >/dev/null 2>&1 \
      || dep_check_fail_or_warn "[依赖] 创建数据库失败: ${db} (${host}:${port})"
  else
    mysql --protocol=tcp -h "$host" -P "$port" -u "$user" -e "CREATE DATABASE IF NOT EXISTS \`$db\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" >/dev/null 2>&1 \
      || dep_check_fail_or_warn "[依赖] 创建数据库失败: ${db} (${host}:${port})"
  fi

  # 2) Count tables
  local table_count=""
  if [ -n "$password" ]; then
    table_count="$(mysql --protocol=tcp -h "$host" -P "$port" -u "$user" -p"$password" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${db}';" 2>/dev/null || true)"
  else
    table_count="$(mysql --protocol=tcp -h "$host" -P "$port" -u "$user" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${db}';" 2>/dev/null || true)"
  fi

  if [ -z "$table_count" ]; then
    dep_check_fail_or_warn "[依赖] 无法读取 ${db} 表数量，请检查 MySQL 连接/权限"
    return
  fi

  if [ "$table_count" != "0" ]; then
    echo -e "${GREEN}[依赖] media_crawler_pro 已有表 (${table_count})，跳过初始化${NC}"
    return
  fi

  echo -e "${CYAN}[依赖] media_crawler_pro 为空库，开始导入表结构...${NC}"
  if [ -n "$password" ]; then
    mysql --protocol=tcp -h "$host" -P "$port" -u "$user" -p"$password" "$db" < "$schema_file" \
      || dep_check_fail_or_warn "[依赖] 导入表结构失败: ${schema_file}"
  else
    mysql --protocol=tcp -h "$host" -P "$port" -u "$user" "$db" < "$schema_file" \
      || dep_check_fail_or_warn "[依赖] 导入表结构失败: ${schema_file}"
  fi
  echo -e "${GREEN}[依赖] media_crawler_pro 表结构导入完成${NC}"
}

init_media_crawler_pro_db_if_needed

# 是否在启动前自动同步 uv 依赖:
# - 默认开启 (UV_SYNC_ON_START=1)
# - 关闭方式: UV_SYNC_ON_START=0 ./start_all.sh
UV_SYNC_ON_START="${UV_SYNC_ON_START:-1}"

sync_uv_project() {
  local project_dir="$1"
  local service_name="$2"
  echo -e "${CYAN}[依赖] ${service_name} 执行 uv sync...${NC}"
  (
    cd "$project_dir"
    UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv sync
  ) 2>&1 | sed "s/^/$(printf "${CYAN}[依赖]${NC} ")/"
}

if [ "$UV_SYNC_ON_START" = "1" ]; then
  sync_uv_project "services/SignSrv/MediaCrawlerPro-SignSrv" "签名服务"
  sync_uv_project "services/DownloadServer/DownloadServer" "下载服务"
  sync_uv_project "backend" "后端"
else
  echo -e "${YELLOW}[依赖] 已跳过 uv sync (UV_SYNC_ON_START=0)${NC}"
fi

echo -e "${PURPLE}[签名服务] 启动 (端口 8989)...${NC}"
(
  load_service_env "signsrv"
  cd services/SignSrv/MediaCrawlerPro-SignSrv
  export APP_HOST="${APP_HOST:-0.0.0.0}"
  export APP_ADDRESS="${APP_ADDRESS:-0.0.0.0}"
  uv run python app.py 2>&1 | sed "s/^/$(printf "${PURPLE}[签名服务]${NC} ")/"
) &
SIGN_PID=$!

echo -e "${PURPLE}[下载服务] 启动 (端口 8205)...${NC}"
(
  load_service_env "download"
  cd services/DownloadServer/DownloadServer
  export APP_HOST="${APP_HOST:-0.0.0.0}"
  uv run python app.py 2>&1 | sed "s/^/$(printf "${PURPLE}[下载服务]${NC} ")/"
) &
DOWN_PID=$!

echo -e "${GREEN}[后端] 启动 (端口 8001)...${NC}"
(
  load_service_env "backend"
  cd backend
  uv run python scripts/run_api_server.py 2>&1 | sed "s/^/$(printf "${RED}[后端]${NC} ")/"
) &
BACKEND_PID=$!

echo -e "${BLUE}[前端] 启动 (端口 5373)...${NC}"
(
  load_service_env "frontend"
  cd frontend
  npm install --silent 2>&1 | sed "s/^/$(printf "${BLUE}[前端]${NC} ")/"
  npm run dev -- --host "${FRONTEND_HOST:-0.0.0.0}" --port "${FRONTEND_PORT:-5373}" 2>&1 | sed "s/^/$(printf "${BLUE}[前端]${NC} ")/"
) &
FRONTEND_PID=$!

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  koubokuang 全栈开发服务器${NC}"
echo -e "${CYAN}  签名服务: http://localhost:8989${NC}"
echo -e "${CYAN}  下载服务: http://localhost:8205${NC}"
echo -e "${CYAN}  后端: http://localhost:8001${NC}"
echo -e "${CYAN}  前端: http://localhost:${FRONTEND_PORT:-5373}${NC}"
echo -e "${CYAN}  按 Ctrl+C 停止所有服务${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

wait
