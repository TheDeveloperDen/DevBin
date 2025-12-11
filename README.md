# DevBin – The Bin for all your Pasting needs

A simple pastebin service written in Python using FastAPI for the Backend and using Svelt for the Frontend.

## Features ( Comming soon )

- Simple and clean interface
- Syntax highlighting
- Paste expiration
- Easy to deploy
- No database required (uses JSON files)
- Supports multiple paste formats

## Requirements

- Docker Engine
- Docker Compose

## Installation

> Note: You maybe required to use docker-compose instead of docker compose depending on your docker version

1. Clone the repository
2. Copy the `.env.example` to `.env` and update the values.   
   2.1. Run `docker compose up -d`  
   2.2. Run migrations with `docker compose run --rm app uv run alembic upgrade head`  
3. Check http://localhost:8000/docs for the Swagger docs in your browser
4. Run `docker compose down` to stop the service
