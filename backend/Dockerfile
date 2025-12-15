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

CMD ["uv", "run", "main.py"]
