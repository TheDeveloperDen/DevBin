FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV APP_PORT=8000
ENV APP_RELOAD=false
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy project files
COPY . .

# Copy alembic config
COPY alembic.docker.ini alembic.ini

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies using uv
RUN uv sync --extra migrations

EXPOSE $PORT

HEALTHCHECK --interval=15s --timeout=5s --start-period=3s CMD curl -f http://localhost:${APP_PORT:-8000}/health || exit 1

CMD ["uv", "run", "main.py"]
