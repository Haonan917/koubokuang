# koubokuang (Agent Only)

这个目录是从 `libs/MediaCrawlerPro-ContentRemixAgent` 抽出来的独立版本，便于部署与维护。

## 目录结构

- `backend/` FastAPI + LangGraph + MySQL
- `frontend/` Vite + React
- `services/` 签名服务 + 下载服务（本地依赖已内置）
- `start.sh` 本地一键启动
- `docker-compose.yml` 可选，本地 MySQL

## 本地启动

```bash
cd koubokuang
chmod +x start.sh
./start.sh
```

后端：`http://localhost:8001`  
前端：`http://localhost:5373`

## GitHub Pages 部署（前端）

前端可独立部署到 GitHub Pages。后端需要单独部署（见 `DEPLOY.md`）。

## 重要环境变量

前端（Vite）：

- `VITE_BACKEND_ORIGIN`：后端域名，例如 `https://api.example.com`
- `VITE_BASE`：GitHub Pages 仓库名路径，例如 `/koubokuang/`
- `VITE_USE_HASH_ROUTER`：`true`（GitHub Pages 建议）

后端：

- 参考 `backend/.env` 与 `DEPLOY.md`
