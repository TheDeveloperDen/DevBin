# DevBin

A lightweight pastebin service built with FastAPI and Svelte.

## Quick Development Start

```bash
git clone https://github.com/TheDeveloperDen/DevBin.git
cd DevBin
cp .env.example .env      # Configure as needed
task dev:up               # Start all services
task db:migrate           # Run migrations
```

**Access:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Commands

Run `task --list` for all available commands.

| Command | Description |
|---------|-------------|
| `task dev:up` | Start all dev services |
| `task dev:down` | Stop all dev services |
| `task dev:logs` | Tail logs |
| `task dev:reset` | Reset with fresh volumes |
| `task db:migrate` | Run migrations |
| `task db:shell` | PostgreSQL shell |
| `task test:all` | Run all tests |
| `task prod:up` | Start production |
| `task prod:down` | Stop production |
| `task clean` | Remove containers and volumes |

## Configuration

See [`.env.example`](.env.example) for all options. Key settings:

| Variable | Description |
|----------|-------------|
| `APP_PORT` | API port (default: 8000) |
| `APP_MAX_CONTENT_LENGTH` | Max paste size |
| `APP_STORAGE_TYPE` | `local`, `s3`, or `minio` |
| `APP_CACHE_TYPE` | `memory` or `redis` |

Full reference: [`docs/configuration.md`](docs/configuration.md)

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /metrics` | Prometheus metrics |
| `POST /pastes` | Create paste (linked to account if authenticated) |
| `GET /pastes/{id}` | Get paste |
| `GET /pastes/me` | Get authenticated user's pastes |
| `DELETE /pastes/{id}` | Delete paste |
| `POST /auth/register` | Register a new user |
| `POST /auth/login` | Authenticate and get tokens |
| `POST /auth/refresh` | Refresh access token |
| `POST /auth/verify-email` | Verify email address |
| `POST /auth/resend-verification` | Resend verification email |
| `POST /auth/forgot-password` | Request password reset |
| `POST /auth/reset-password` | Reset password |
| `GET /auth/me` | Get current user profile |
| `POST /auth/logout` | Logout and revoke tokens |

Interactive docs at `/docs` when running.

## Documentation

- [Configuration Reference](docs/configuration.md)
- [Production Deployment](docs/deployment.md)
- [Testing Guide](backend/TESTING.md)

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: Svelte
- **Deployment**: Docker Compose
