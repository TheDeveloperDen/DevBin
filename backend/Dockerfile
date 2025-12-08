FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PORT=8000

# Set the working directory in the container
WORKDIR /app

# Copy the project files
COPY . .

# Install system dependencies (if any)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies using uv
RUN uv sync

# Expose the port the app runs on
EXPOSE $PORT

# Command to run the application
CMD ["python", "main.py"]