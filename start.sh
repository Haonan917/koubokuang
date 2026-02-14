#!/bin/bash
set -e

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo -e "${YELLOW}正在关闭服务...${NC}"
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && echo -e "${RED}[后端] 已停止${NC}"
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && echo -e "${BLUE}[前端] 已停止${NC}"
    wait 2>/dev/null
    echo -e "${GREEN}所有服务已关闭${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 检查依赖
echo -e "${CYAN}检查依赖...${NC}"
if ! command -v uv &>/dev/null; then
    echo -e "${RED}错误: 未找到 uv，请先安装: https://docs.astral.sh/uv/${NC}"
    exit 1
fi
if ! command -v npm &>/dev/null; then
    echo -e "${RED}错误: 未找到 npm，请先安装 Node.js${NC}"
    exit 1
fi

# 启动后端
echo -e "${GREEN}[后端] 安装依赖并启动 (端口 8001)...${NC}"
(
    set -a
    [ -f backend/.env ] && source backend/.env
    set +a
    cd backend
    # uv sync 2>&1 | sed "s/^/$(printf "${RED}[后端]${NC} ")/"
    uv run python scripts/run_api_server.py 2>&1 | sed "s/^/$(printf "${RED}[后端]${NC} ")/"
) &
BACKEND_PID=$!

# 启动前端
echo -e "${BLUE}[前端] 安装依赖并启动 (端口 5373)...${NC}"
(
    cd frontend
    npm install --silent 2>&1 | sed "s/^/$(printf "${BLUE}[前端]${NC} ")/"
    npm run dev 2>&1 | sed "s/^/$(printf "${BLUE}[前端]${NC} ")/"
) &
FRONTEND_PID=$!

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Content Remix Agent 开发服务器${NC}"
echo -e "${CYAN}  后端: http://localhost:8001${NC}"
echo -e "${CYAN}  前端: http://localhost:5373${NC}"
echo -e "${CYAN}  按 Ctrl+C 停止所有服务${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 等待子进程
wait
