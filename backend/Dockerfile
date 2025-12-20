# ============================================
# Stage 1: Base - Common Configuration
# ============================================
FROM python:3.13.1-slim AS base

# Install security updates and minimal runtime dependencies
# Create non-root user (UID 10001 is common convention)
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /bin/bash appuser

WORKDIR /app

# ============================================
# Stage 2: Builder - Dependency Installation
# ============================================
FROM base AS builder

# Install build dependencies (only needed during build)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy uv from official image (pinned version for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.5.16 /uv /uvx /usr/local/bin/

# Copy dependency files first for optimal layer caching
# Changes to source code won't invalidate this layer
COPY pyproject.toml uv.lock ./

# Install dependencies
# --frozen: Use exact versions from uv.lock (reproducible builds)
# --no-dev: Exclude development dependencies
# --extra migrations: Include migrations group (psycopg2-binary)
# --no-cache: Prevent uv cache bloat in image
RUN uv sync --frozen --no-dev --extra migrations --no-cache

# ============================================
# Stage 3: Runtime - Production Image
# ============================================
FROM base AS runtime

# Copy uv for runtime execution
COPY --from=ghcr.io/astral-sh/uv:0.5.16 /uv /uvx /usr/local/bin/

# Copy installed dependencies from builder stage
# This excludes build tools (gcc, g++, libpq-dev)
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser . .

# Copy Docker-specific alembic config
COPY --chown=appuser:appuser alembic.docker.ini alembic.ini

# Create files directory and set ownership for entire /app directory
# This ensures appuser can write to .venv and create build artifacts
RUN mkdir -p /app/files && \
    chown -R appuser:appuser /app

# Switch to non-root user for security
USER appuser

# Environment variables
ENV APP_PORT=8000 \
    APP_RELOAD=false \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose application port
EXPOSE 8000

# Health check using existing /health endpoint
# --interval=30s: Check every 30 seconds
# --timeout=5s: Mark unhealthy if no response in 5s
# --start-period=10s: Grace period for app startup
# --retries=3: Require 3 consecutive failures before marking unhealthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT:-8000}/health || exit 1

# Use exec form for proper signal handling (graceful shutdown)
CMD ["uv", "run", "main.py"]
