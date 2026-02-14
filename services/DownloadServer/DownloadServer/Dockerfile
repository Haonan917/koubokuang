# 多阶段构建 - Builder 阶段
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
COPY app.py router.py context_vars.py ./
COPY abs/ ./abs/
COPY apis/ ./apis/
COPY config/ ./config/
COPY constant/ ./constant/
COPY logic/ ./logic/
COPY models/ ./models/
COPY pkg/ ./pkg/
COPY repo/ ./repo/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime 阶段
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8205 \
    IS_DEBUG=False \
    LOGGER_LEVEL=INFO \
    SIGN_SRV_HOST=sign-srv \
    SIGN_SRV_PORT=8989

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app /app

RUN mkdir -p /app/logs && chown -R appuser:appgroup /app/logs

USER appuser

EXPOSE 8205

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8205/ping', timeout=5)" || exit 1

CMD ["/app/.venv/bin/python", "app.py"]
