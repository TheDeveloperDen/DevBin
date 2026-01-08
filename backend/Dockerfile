# ============================================
# Build Arguments
# ============================================
ARG UV_VERSION=0.9.18

# ============================================
# Stage 0: UV Binary
# ============================================
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ============================================
# Stage 1: Base - Common Configuration
# ============================================
FROM python:3.13.1-slim AS base

# Install security updates and minimal runtime dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ============================================
# Stage 2: Builder - Dependency Installation
# ============================================
FROM base AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

# Copy dependencies
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups --extra production --extra migrations  --no-install-project

# ============================================
# Stage 3: Runtime - Production Image
# ============================================
FROM base AS runtime

# Copy uv and the pre-built venv
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/
COPY --from=builder /app/.venv /app/.venv

# Copy application code with correct ownership
COPY . .

# Overwrite config
COPY alembic.docker.ini alembic.ini

# Create files directory
RUN mkdir -p /app/files
RUN mkdir -p /app/files/pastes

# Environment variables
ENV APP_PORT=8000 \
    APP_RELOAD=false \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT="/app/.venv"

# Expose application port
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT:-8000}/health || exit 1

# FIX: Added --no-project to prevent uv from trying to write .egg-info
CMD ["uv", "run", "--no-project", "python", "main.py"]
