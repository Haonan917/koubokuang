# 多阶段构建 - 从 Node.js 镜像获取 Node.js (pyexecjs 需要)
FROM node:18-slim AS nodejs

# Builder 阶段
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 先复制依赖文件利用缓存
COPY pyproject.toml uv.lock ./

# 安装依赖
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# 复制源代码
COPY app.py config.py context_vars.py urls.py ./
COPY apis/ ./apis/
COPY constant/ ./constant/
COPY logic/ ./logic/
COPY params/ ./params/
COPY pkg/ ./pkg/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime 阶段
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8989 \
    IS_DEBUG=False \
    LOGGER_LEVEL=INFO

# 从 Node.js 阶段复制 Node.js
COPY --from=nodejs /usr/local/bin/node /usr/local/bin/
COPY --from=nodejs /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app /app

RUN mkdir -p /app/logs && chown -R appuser:appgroup /app/logs

USER appuser

EXPOSE 8989

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8989/signsrv/pong', timeout=5)" || exit 1

CMD ["/app/.venv/bin/python", "app.py"]
