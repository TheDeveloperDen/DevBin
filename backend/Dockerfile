FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PORT=8000
ENV RELOAD=false

# Set the working directory in the container
WORKDIR /app

# Copy the project files
COPY . .

COPY alembic.docker.ini alembic.ini

# Install system dependencies (if any)
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*  \
    && uv sync --extra migrations # Install Python dependencies using uv

# Expose the port the app runs on
EXPOSE $PORT

HEALTHCHECK --interval=5s --timeout=5s --start-period=3s --retries=3 CMD curl -f http://localhost:"$PORT"/health || exit 1

# Command to run the application
CMD ["uv", "run", "main.py"]