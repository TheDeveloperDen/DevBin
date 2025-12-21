# DevBin – The Bin for all your Pasting needs

A lightweight and modern pastebin service built with FastAPI (Python) for the backend and Svelte for the frontend. Share
code snippets, text, and more with ease.

## Features

- **Simple and Clean Interface** – Intuitive UI for quick paste creation and sharing
- **Syntax Highlighting** – Support for multiple programming languages
- **Paste Expiration** – Automatic cleanup of expired pastes
- **Rate Limiting** – Built-in protection with configurable limits and bypass tokens
- **Caching Layer** – LRU cache for improved performance
- **Legacy Paste Support** – Backward compatibility with older paste formats
- **Health Monitoring** – Built-in health check endpoint and storage monitoring
- **Docker Ready** – Easy deployment with Docker Compose
- **Configurable Storage** – Customizable file storage and size limits
- **Trusted Hosts** – IP-based access control

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Alembic (migrations)
- **Frontend**: Svelte
- **Deployment**: Docker, Docker Compose
- **Caching**: LRU Memory Cache with configurable TTL

## Requirements

- Docker Engine
- Docker Compose (or `docker-compose` for older versions)

## Installation

> **Note**: Depending on your Docker version, you may need to use `docker-compose` instead of `docker compose`

### Quick Start

DevBin can be deployed in two ways:

#### Option 1: Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd DevBin
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and update the values according to your needs. Key configurations include:
    - Database credentials
    - API port and host
    - Rate limiting settings
    - CORS domains
    - Storage paths and limits
    - Trusted hosts

3. **Start the services**
   ```bash
   docker compose up -d
   ```

4. **Run database migrations**
   ```bash
   docker compose run --rm app uv run alembic upgrade head
   ```

5. **Access the application**
    - Frontend: http://localhost:3000
    - API Documentation (Swagger): http://localhost:8000/docs
    - Health Check: http://localhost:8000/health

#### Option 2: Production Setup

For production deployment, you only need the production compose file and environment configuration:

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd DevBin
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with production-ready values (strong passwords, proper domains, etc.)

3. **Start the services**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

4. **Run database migrations**
   ```bash
   docker compose -f docker-compose.prod.yml run --rm app uv run alembic upgrade head
   ```

### Stopping the Service

Development:

```bash
docker compose down
```

Production:

```bash
docker compose -f docker-compose.prod.yml down
```

## Configuration

Key environment variables in `.env`:

| Variable                 | Description                             | Default                   |
|--------------------------|-----------------------------------------|---------------------------|
| `APP_PORT`               | Backend API port                        | 8000                      |
| `APP_MAX_CONTENT_LENGTH` | Maximum paste size                      | 10000                     |
| `APP_WORKERS`            | Number of worker processes              | 1                         |
| `APP_BYPASS_TOKEN`       | Token to bypass rate limits             | -                         |
| `APP_CACHE_TTL`          | Cache time-to-live (seconds)            | 300                       |
| `APP_MIN_STORAGE_MB`     | Minimum required storage (MB)           | 1024                      |
| `TRUSTED_HOSTS`          | Array of trusted IP addresses/hostnames | ["127.0.0.1"]             |
| `APP_CORS_DOMAINS`       | Allowed CORS origins                    | ["http://localhost:3000"] |

See `.env.example` for a complete list of configuration options.

## Development

### Running in Development Mode

Set these variables in `.env`:

```env
APP_DEBUG=true
APP_RELOAD=true
APP_SQLALCHEMY_ECHO=true
```

### Tests

### Backend Tests

Run tests with:

```bash
cd backend
uv run pytest
```

> If you modified any of the core API endpoints, make sure to run the tests to ensure they still work as expected. Or if
> you are committing breaking changes, please adjust them and add a note why this breaking change is necessary.

See [Testing](/backend/TESTING.md)

### API Endpoints

- `GET /health` – Health check
- `GET /pastes/{paste_id}` – Retrieve a paste
- `GET /pastes/legacy/{paste_id}` – Retrieve a legacy paste
- `POST /pastes` – Create a new paste

Full API documentation available at `/docs` when running.

## Production Deployment

See **[Option 2: Production Setup](#option-2-production-setup)** in the Quick Start section above for deployment
instructions.

### Production Checklist

Make sure to configure the following in your `.env` file:

- ✅ Set strong database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`)
- ✅ Configure appropriate rate limits
- ✅ Set `APP_DEBUG=false` and `APP_RELOAD=false`
- ✅ Configure trusted hosts properly (`TRUSTED_HOSTS`)
- ✅ Set up proper CORS domains (`APP_CORS_DOMAINS`)
- ✅ Use a secure bypass token (`APP_BYPASS_TOKEN`)
- ✅ Configure minimum storage requirements (`APP_MIN_STORAGE_MB`)
- ✅ Set appropriate worker count (`APP_WORKERS`)
