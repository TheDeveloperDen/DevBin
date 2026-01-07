# Production Deployment

## Quick Deploy

```bash
# Clone and configure
git clone https://github.com/TheDeveloperDen/DevBin.git
cd DevBin
cp .env.example .env
# Required: Edit .env with production values
```

Then triggering docker compose manually  
(you maybe required replacing `docker compose` with `docker-compose`)

```bash
# Start services
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose -f docker-compose.prod.yml run --rm app uv run alembic upgrade head
```

Or with Taskfile:

```bash
task prod:up
task db:migrate
```

## Production Checklist

### Security (**REQUIRED**)

> If not set, DevBin will not be secure and
> do not open an issue reporting any security problems if those below are not set

- [ ] Strong database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`)
- [ ] `APP_DEBUG=false`
- [ ] `APP_RELOAD=false`
- [ ] Configure `APP_TRUSTED_HOSTS`

> Note: Your reverse proxy IPs from the frontend, if on docker it can be the containers
> name, for example `["devbin_frontend"]` otherwise specify the ip of the frontend server

- [ ] Set specific `APP_CORS_DOMAINS` (no wildcards)
- [ ] Set `APP_ALLOW_CORS_WILDCARD=false`
- [ ] Generate secure `APP_BYPASS_TOKEN` if needed, if empty no bypass token will be used
- [ ] Set `APP_METRICS_TOKEN` for Prometheus endpoint (Required, otherwise public)

### Performance

- [ ] Set `APP_WORKERS` based on your required performance for your use case. (true=Uses CPU cores count)
- [ ] Configure `APP_CACHE_TTL` appropriately
- [ ] Consider Redis for caching (`APP_CACHE_TYPE=redis`) at scale
- [ ] Consider Redis for locking (`APP_LOCK_TYPE=redis`) for multi-instance

### Storage

- [ ] Set `APP_MIN_STORAGE_MB` for disk space monitoring
- [ ] For multi-instance: use S3 or MinIO (`APP_STORAGE_TYPE`)
- [ ] Configure compression settings for storage efficiency

### Logging

- [ ] Set `APP_LOG_LEVEL=INFO` or `WARNING`
- [ ] Use `APP_LOG_FORMAT=json` for log aggregation

## Scaling

### Single Instance

Default configuration works out of the box. Increase `APP_WORKERS` as needed.

### Multiple Instances

For horizontal scaling:

1. **Storage**: Switch to S3 or MinIO
   ```env
   APP_STORAGE_TYPE=s3
   APP_S3_BUCKET_NAME=devbin-pastes
   APP_S3_REGION=us-east-1
   APP_S3_ACCESS_KEY=...
   APP_S3_SECRET_KEY=...
   ```

2. **Caching**: Use Redis
   ```env
   APP_CACHE_TYPE=redis
   APP_REDIS_HOST=redis.example.com
   ```

3. **Locking**: Use Redis
   ```env
   APP_LOCK_TYPE=redis
   ```

## Reverse Proxy

When behind nginx, traefik, or similar:

```env
APP_ENFORCE_HTTPS=false  # Let proxy handle SSL
APP_TRUSTED_HOSTS=["10.0.0.0/8", "172.16.0.0/12"]  # Proxy IPs (configure for your setup)
```

## Health Checks

- **Health endpoint**: `GET /health`
- **Ready endpoint**: `GET /ready` (if you are running load balancers )
- **Metrics endpoint**: `GET /metrics` (protected by `APP_METRICS_TOKEN`)

## Stopping Services

```bash
docker compose -f docker-compose.prod.yml down
```

Or: `task prod:down`
