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

echo -e "${CYAN}检查依赖...${NC}"
if ! command -v uv &>/dev/null; then
  echo -e "${RED}错误: 未找到 uv，请先安装: https://docs.astral.sh/uv/${NC}"
  exit 1
fi
if ! command -v npm &>/dev/null; then
  echo -e "${RED}错误: 未找到 npm，请先安装 Node.js${NC}"
  exit 1
fi

echo -e "${PURPLE}[签名服务] 启动 (端口 8989)...${NC}"
(
  cd services/SignSrv/MediaCrawlerPro-SignSrv
  uv run python app.py 2>&1 | sed "s/^/$(printf "${PURPLE}[签名服务]${NC} ")/"
) &
SIGN_PID=$!

echo -e "${PURPLE}[下载服务] 启动 (端口 8205)...${NC}"
(
  cd services/DownloadServer/DownloadServer
  uv run python app.py 2>&1 | sed "s/^/$(printf "${PURPLE}[下载服务]${NC} ")/"
) &
DOWN_PID=$!

echo -e "${GREEN}[后端] 启动 (端口 8001)...${NC}"
(
  set -a
  [ -f backend/.env ] && source backend/.env
  set +a
  cd backend
  uv run python scripts/run_api_server.py 2>&1 | sed "s/^/$(printf "${RED}[后端]${NC} ")/"
) &
BACKEND_PID=$!

echo -e "${BLUE}[前端] 启动 (端口 5373)...${NC}"
(
  cd frontend
  npm install --silent 2>&1 | sed "s/^/$(printf "${BLUE}[前端]${NC} ")/"
  npm run dev 2>&1 | sed "s/^/$(printf "${BLUE}[前端]${NC} ")/"
) &
FRONTEND_PID=$!

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  koubokuang 全栈开发服务器${NC}"
echo -e "${CYAN}  签名服务: http://localhost:8989${NC}"
echo -e "${CYAN}  下载服务: http://localhost:8205${NC}"
echo -e "${CYAN}  后端: http://localhost:8001${NC}"
echo -e "${CYAN}  前端: http://localhost:5373${NC}"
echo -e "${CYAN}  按 Ctrl+C 停止所有服务${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

wait
