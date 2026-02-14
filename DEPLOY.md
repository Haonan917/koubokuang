# 部署指南

本指南分为两部分：前端（GitHub Pages）和后端（可选云平台 + 数据库）。

---

## 1. 前端部署到 GitHub Pages

### 1) 创建仓库
1. 在 GitHub 新建仓库，例如 `koubokuang`。
2. 将本目录作为独立仓库推送（推荐）：
   ```bash
   cd koubokuang
   git init
   git add .
   git commit -m "init agent-only"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/koubokuang.git
   git push -u origin main
   ```

### 2) 配置 GitHub Actions
仓库内已经包含 `.github/workflows/deploy.yml`，无需手动添加。

### 3) 配置 GitHub Pages
1. 进入仓库 Settings → Pages
2. Source 选择 **GitHub Actions**

### 4) 配置前端环境变量
在 GitHub 仓库 Settings → Secrets and variables → Actions → Variables，新增：

- `VITE_BACKEND_ORIGIN`：后端地址，例如 `https://api.yourdomain.com`
- `VITE_BASE`：`/koubokuang/`（必须与仓库名一致）
- `VITE_USE_HASH_ROUTER`：`true`（推荐 GitHub Pages 使用）

完成后推送任意提交触发构建，页面访问：
`https://<你的用户名>.github.io/koubokuang/`

---

## 2. 后端部署（示例：Render / Railway / Fly.io）

### 2.1 你需要准备
- 一台可运行 Python 3.11 的容器/服务器
- 一个 MySQL 8.0 数据库（推荐：Railway/PlanetScale/阿里云RDS）

### 2.2 环境变量（后端）
参考 `backend/.env`，至少需要：
- `AGENT_DB_HOST`
- `AGENT_DB_PORT`
- `AGENT_DB_USER`
- `AGENT_DB_PASSWORD`
- `AGENT_DB_NAME`
- `VOICV_API_KEY`
- `SYNCSO_API_KEY`

### 2.3 安装与启动
```bash
cd backend
uv sync
uv run python scripts/run_migrations.py
uv run python scripts/run_api_server.py
```

### 2.4 生产部署建议
- 用 `uvicorn` 绑定 0.0.0.0，并设置 `--proxy-headers`
- 给 Nginx/反代配置 `/api` `/media` `/assets` 转发

---

## 3. 数据库部署

推荐方案：
- Railway MySQL
- PlanetScale
- 阿里云 RDS MySQL

部署后，将连接信息写入后端环境变量即可。
