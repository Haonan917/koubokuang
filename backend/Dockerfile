# ============================================================
# Content Remix Agent Backend Dockerfile
# Multi-stage build for Python FastAPI + FunASR + ffmpeg
# ============================================================

# -------------------- Builder Stage --------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies (without project itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy source code
COPY . .

# Install project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# -------------------- Runtime Stage --------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Ensure venv Python is used
    PATH="/app/.venv/bin:$PATH"

# Use Aliyun mirror for faster downloads in China (optional, comment out if not needed)
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# Install runtime dependencies: ffmpeg for video/audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment and source from builder
COPY --from=builder /app /app

# Create necessary directories
# Note: /app/assets contains built-in static files (fonts, logos)
# /app/data/assets is for user-generated content (covers, videos) - mounted at runtime
RUN mkdir -p /app/temp/videos /app/temp/asr /app/data/assets

# Expose API port
EXPOSE 8001

# Health check
# Note: Using full path for robustness, though PATH is set above
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/.venv/bin/python -c "import httpx; httpx.get('http://localhost:8001/health', timeout=5)" || exit 1

# Run API server
# Note: The entry point is relative to /app directory
CMD ["python", "scripts/run_api_server.py"]
