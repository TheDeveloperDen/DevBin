# Configuration

All configuration is done via environment variables. Copy `.env.example` to `.env` and adjust as needed.

## Server

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENVIRONMENT` | Environment mode (`dev`, `staging`, `prod`) | `dev` |
| `APP_PORT` | API port | `8000` |
| `APP_HOST` | Bind address | `0.0.0.0` |
| `APP_WORKERS` | Uvicorn worker count | `1` |
| `APP_RELOAD` | Auto-reload on code changes | `false` |
| `APP_DEBUG` | Debug mode | `false` |

## Logging

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |
| `APP_LOG_FORMAT` | `text` (human-readable) or `json` (structured) | `text` |

## Database

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/devbin` |

## Security

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENFORCE_HTTPS` | Redirect HTTP to HTTPS (disable if behind reverse proxy) | `false` |
| `APP_CORS_DOMAINS` | Allowed CORS origins (JSON array) | `["*"]` |
| `APP_ALLOW_CORS_WILDCARD` | Allow `*` in CORS | `true` |
| `APP_TRUSTED_HOSTS` | Trusted hosts for X-Forwarded-For (JSON array) | `["127.0.0.1"]` |
| `APP_BYPASS_TOKEN` | Token to bypass rate limits | - |

## Paste Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_MAX_CONTENT_LENGTH` | Maximum paste size in bytes | `10000` |
| `APP_BASE_FOLDER_PATH` | Local file storage path | `./files` |
| `APP_MIN_STORAGE_MB` | Minimum required disk space (MB) | `1024` |
| `APP_KEEP_DELETED_PASTES_TIME_HOURS` | Soft-delete retention period | `336` (14 days) |

## Storage Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_STORAGE_TYPE` | `local`, `s3`, or `minio` | `local` |

### S3 (when `STORAGE_TYPE=s3`)

| Variable | Description |
|----------|-------------|
| `APP_S3_BUCKET_NAME` | S3 bucket name |
| `APP_S3_REGION` | AWS region |
| `APP_S3_ACCESS_KEY` | AWS access key |
| `APP_S3_SECRET_KEY` | AWS secret key |
| `APP_S3_ENDPOINT_URL` | Custom S3 endpoint (optional) |

### MinIO (when `STORAGE_TYPE=minio`)

| Variable | Description |
|----------|-------------|
| `APP_S3_BUCKET_NAME` | Bucket name |
| `APP_MINIO_ENDPOINT` | MinIO endpoint (e.g., `minio:9000`) |
| `APP_MINIO_ACCESS_KEY` | Access key |
| `APP_MINIO_SECRET_KEY` | Secret key |
| `APP_MINIO_SECURE` | Use HTTPS | `true` |

## Compression

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_COMPRESSION_ENABLED` | Enable content compression | `true` |
| `APP_COMPRESSION_THRESHOLD_BYTES` | Minimum size to compress | `2048` |
| `APP_COMPRESSION_LEVEL` | Compression level (1-9) | `6` |

## Caching

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_CACHE_TYPE` | `memory` or `redis` | `memory` |
| `APP_CACHE_SIZE_LIMIT` | Max cached items (memory only) | `1000` |
| `APP_CACHE_TTL` | Cache TTL in seconds | `300` |

### Redis (when `CACHE_TYPE=redis` or `LOCK_TYPE=redis`)

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_REDIS_HOST` | Redis host | `localhost` |
| `APP_REDIS_PORT` | Redis port | `6379` |
| `APP_REDIS_DB` | Redis database number | `0` |
| `APP_REDIS_PASSWORD` | Redis password (optional) | - |

## Distributed Locking

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_LOCK_TYPE` | `file` or `redis` | `file` |

## Privacy

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_SAVE_USER_AGENT` | Store user agent | `false` |
| `APP_SAVE_IP_ADDRESS` | Store IP address | `false` |

## Metrics

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_METRICS_TOKEN` | Bearer token for `/metrics` endpoint (optional) | - |

Generate a secure token: `openssl rand -hex 32`

## Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | Backend API URL | `http://devbin:8000` |
| `PORT` | Frontend port | `3000` |
| `ORIGIN` | Frontend origin | `http://localhost:3000` |
