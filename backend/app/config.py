import logging
import re
from typing import Annotated, Literal

from dotenv import load_dotenv
from pydantic import AfterValidator, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings

from app.utils.ip import TrustedHost, parse_ip_or_network, resolve_hostname, validate_ip_address

# Rate limit format validation
RATE_LIMIT_PATTERN = re.compile(r"^\d+/(second|minute|hour|day)$")


def validate_rate_limit(value: str) -> str:
    """Validate rate limit format (e.g., '10/minute', '100/hour')."""
    if not RATE_LIMIT_PATTERN.match(value):
        raise ValueError(
            f"Invalid rate limit format: '{value}'. " "Expected format: '<number>/<second|minute|hour|day>'"
        )
    return value


RateLimit = Annotated[str, AfterValidator(validate_rate_limit)]

# Load .env file if it exists
load_dotenv()


class Config(BaseSettings):
    # Environment
    ENVIRONMENT: Literal["dev", "staging", "prod"] = Field(
        default="dev", validation_alias="APP_ENVIRONMENT", description="Application environment (dev, staging, prod)"
    )

    PORT: int = Field(default=8000, validation_alias="APP_PORT")
    HOST: str = Field(default="0.0.0.0", validation_alias="APP_HOST")

    # DB
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        validation_alias="APP_DATABASE_URL",
    )
    SQLALCHEMY_ECHO: bool = Field(default=False, validation_alias="APP_SQLALCHEMY_ECHO")

    # Paste
    MAX_CONTENT_LENGTH: int = Field(default=10000, validation_alias="APP_MAX_CONTENT_LENGTH")
    BASE_FOLDER_PATH: str = Field(default="./files", validation_alias="APP_BASE_FOLDER_PATH")
    WORKERS: int | Literal[True] = Field(default=1, validation_alias="APP_WORKERS")
    METRICS_TOKEN: str | None = Field(
        default=None,
        validation_alias="APP_METRICS_TOKEN",
        description="Bearer token for Prometheus metrics endpoint authentication",
    )

    ALLOW_CORS_WILDCARD: bool = Field(
        default=False,
        validation_alias="APP_ALLOW_CORS_WILDCARD",
        description="Allow wildcard (*) in CORS domains (disable in production)",
    )

    CORS_DOMAINS: list[str] = Field(default=["*"], validation_alias="APP_CORS_DOMAINS")

    SAVE_USER_AGENT: bool = Field(default=False, validation_alias="APP_SAVE_USER_AGENT")
    SAVE_IP_ADDRESS: bool = Field(default=False, validation_alias="APP_SAVE_IP_ADDRESS")

    CACHE_SIZE_LIMIT: int = Field(default=1000, validation_alias="APP_CACHE_SIZE_LIMIT")
    CACHE_TTL: int = Field(default=300, validation_alias="APP_CACHE_TTL")

    # Cache backend configuration
    CACHE_TYPE: Literal["memory", "redis"] = Field(
        default="memory", validation_alias="APP_CACHE_TYPE", description="Cache backend type (memory, redis)"
    )
    REDIS_HOST: str = Field(default="localhost", validation_alias="APP_REDIS_HOST", description="Redis server host")
    REDIS_PORT: int = Field(default=6379, validation_alias="APP_REDIS_PORT", description="Redis server port")
    REDIS_DB: int = Field(default=0, validation_alias="APP_REDIS_DB", description="Redis database number")
    REDIS_PASSWORD: str | None = Field(
        default=None, validation_alias="APP_REDIS_PASSWORD", description="Redis password (optional)"
    )

    # Lock backend configuration
    LOCK_TYPE: Literal["file", "redis"] = Field(
        default="file", validation_alias="APP_LOCK_TYPE", description="Lock backend type (file, redis)"
    )

    # Rate limiting configuration
    RATELIMIT_ENABLED: bool = Field(
        default=True,
        validation_alias="APP_RATELIMIT_ENABLED",
        description="Enable/disable rate limiting globally",
    )
    RATELIMIT_BACKEND: Literal["memory", "redis"] = Field(
        default="memory",
        validation_alias="APP_RATELIMIT_BACKEND",
        description="Rate limiting storage backend (memory, redis)",
    )
    RATELIMIT_DEFAULT: RateLimit = Field(
        default="60/minute",
        validation_alias="APP_RATELIMIT_DEFAULT",
        description="Default rate limit for endpoints without explicit limits",
    )

    # Per-endpoint rate limits
    RATELIMIT_HEALTH: RateLimit = Field(
        default="60/minute",
        validation_alias="APP_RATELIMIT_HEALTH",
        description="Rate limit for health check endpoints",
    )
    RATELIMIT_GET_PASTE: RateLimit = Field(
        default="10/minute",
        validation_alias="APP_RATELIMIT_GET_PASTE",
        description="Rate limit for GET /p/{paste_id}",
    )
    RATELIMIT_GET_PASTE_LEGACY: RateLimit = Field(
        default="10/minute",
        validation_alias="APP_RATELIMIT_GET_PASTE_LEGACY",
        description="Rate limit for GET /{paste_id} (legacy endpoint)",
    )
    RATELIMIT_CREATE_PASTE: RateLimit = Field(
        default="4/minute",
        validation_alias="APP_RATELIMIT_CREATE_PASTE",
        description="Rate limit for POST /p/",
    )
    RATELIMIT_EDIT_PASTE: RateLimit = Field(
        default="4/minute",
        validation_alias="APP_RATELIMIT_EDIT_PASTE",
        description="Rate limit for PUT /p/{paste_id}",
    )
    RATELIMIT_DELETE_PASTE: RateLimit = Field(
        default="4/minute",
        validation_alias="APP_RATELIMIT_DELETE_PASTE",
        description="Rate limit for DELETE /p/{paste_id}",
    )

    # Bypass tokens for rate limiting (JSON list format)
    RATELIMIT_BYPASS_TOKENS: list[str] = Field(
        default=[],
        validation_alias="APP_RATELIMIT_BYPASS_TOKENS",
        description="List of tokens that bypass rate limiting",
    )

    # Logging configuration
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", validation_alias="APP_LOG_LEVEL", description="Logging level"
    )
    LOG_FORMAT: Literal["text", "json"] = Field(
        default="text",
        validation_alias="APP_LOG_FORMAT",
        description="Log output format (text for human-readable, json for structured)",
    )

    MIN_STORAGE_MB: int = Field(
        default=1024,
        validation_alias="APP_MIN_STORAGE_MB",
        description="Minimum storage size in MB free",
    )

    # Compression settings
    COMPRESSION_ENABLED: bool = Field(
        default=True,
        validation_alias="APP_COMPRESSION_ENABLED",
        description="Enable gzip compression for paste content",
    )
    COMPRESSION_THRESHOLD_BYTES: int = Field(
        default=2048,
        validation_alias="APP_COMPRESSION_THRESHOLD_BYTES",
        description="Minimum content size in bytes to trigger compression (2KB+ shows 30-40% compression ratio)",
    )
    COMPRESSION_LEVEL: int = Field(
        default=6, validation_alias="APP_COMPRESSION_LEVEL", description="Gzip compression level (1-9, 6=balanced)"
    )

    # Storage settings
    STORAGE_TYPE: Literal["local", "s3", "minio"] = Field(
        default="local", validation_alias="APP_STORAGE_TYPE", description="Storage backend type (local, s3, minio)"
    )
    S3_BUCKET_NAME: str = Field(default="", validation_alias="APP_S3_BUCKET_NAME", description="S3 bucket name")
    S3_REGION: str = Field(default="us-east-1", validation_alias="APP_S3_REGION", description="AWS region for S3")
    S3_ACCESS_KEY: str = Field(default="", validation_alias="APP_S3_ACCESS_KEY", description="S3 access key ID")
    S3_SECRET_KEY: str = Field(default="", validation_alias="APP_S3_SECRET_KEY", description="S3 secret access key")
    S3_ENDPOINT_URL: str | None = Field(
        default=None,
        validation_alias="APP_S3_ENDPOINT_URL",
        description="Custom S3 endpoint URL (for S3-compatible services)",
    )
    MINIO_ENDPOINT: str = Field(
        default="", validation_alias="APP_MINIO_ENDPOINT", description="MinIO server endpoint (e.g., 'minio:9000')"
    )
    MINIO_ACCESS_KEY: str = Field(default="", validation_alias="APP_MINIO_ACCESS_KEY", description="MinIO access key")
    MINIO_SECRET_KEY: str = Field(default="", validation_alias="APP_MINIO_SECRET_KEY", description="MinIO secret key")
    MINIO_SECURE: bool = Field(
        default=True, validation_alias="APP_MINIO_SECURE", description="Use HTTPS for MinIO connection"
    )

    KEEP_DELETED_PASTES_TIME_HOURS: int = Field(
        default=336,
        validation_alias="APP_KEEP_DELETED_PASTES_TIME_HOURS",
        description="Keep deleted pastes for X hours ( Default 336 hours, 2 weeks, -1 disable, 0 instant )",
    )

    TRUSTED_HOSTS: list[str] = Field(
        default=["127.0.0.1"],
        validation_alias="APP_TRUSTED_HOSTS",
        description="Trusted hosts/networks for X-Forwarded-For (supports CIDR: 10.0.0.0/8, 172.16.0.0/12)",
    )

    RELOAD: bool = Field(default=False, validation_alias="APP_RELOAD")
    DEBUG: bool = Field(default=False, validation_alias="APP_DEBUG")

    ENFORCE_HTTPS: bool = Field(
        default=False,
        validation_alias="APP_ENFORCE_HTTPS",
        description="Enforce HTTPS by redirecting HTTP requests",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @field_validator("DATABASE_URL", mode="after")
    def verify_db_url(cls, db_url: str) -> str:
        split_url = db_url.split(":")
        if len(split_url) <= 2:
            raise ValidationError("Invalid database URL")

        library = split_url[0]
        if library == "postgresql":
            split_url[0] += "+asyncpg"

            return ":".join(split_url)

        return db_url

    @field_validator("TRUSTED_HOSTS", mode="after")
    def verify_trusted_hosts(cls, hosts: list[str]) -> list[TrustedHost]:
        validated_hosts: list[TrustedHost] = []
        for host in hosts:
            # Try parsing as IP or network (CIDR notation)
            parsed = parse_ip_or_network(host)
            if parsed:
                validated_hosts.append(parsed)
            else:
                # Try resolving as hostname
                resolved = resolve_hostname(host)
                if resolved:
                    resolved_ip = validate_ip_address(resolved)
                    if resolved_ip:
                        validated_hosts.append(resolved_ip)
        logging.info("Trusted hosts: %s", validated_hosts)
        return validated_hosts

    @field_validator("CORS_DOMAINS", mode="after")
    def validate_cors_domains(cls, domains: list[str], info) -> list[str]:
        """Validate CORS domains and warn/error on wildcard."""
        if "*" in domains:
            # Check if ALLOW_CORS_WILDCARD is in the data (field name, not alias)
            allow_wildcard = info.data.get("ALLOW_CORS_WILDCARD", False)

            if not allow_wildcard:
                logging.error(
                    "SECURITY WARNING: CORS wildcard (*) is NOT allowed. "
                    "Set APP_ALLOW_CORS_WILDCARD=true to enable, "
                    "or specify exact domains in APP_CORS_DOMAINS."
                )
                raise ValueError(
                    "CORS wildcard (*) is disabled. Set APP_ALLOW_CORS_WILDCARD=true or use specific domains."
                )
            else:
                logging.warning(
                    "SECURITY WARNING: CORS wildcard (*) allows ANY origin. "
                    "Use only in development, NEVER in production!"
                )

        logging.info("CORS domains: %s", domains)
        return domains

    @field_validator("COMPRESSION_LEVEL", mode="after")
    def validate_compression_level(cls, level: int) -> int:
        """Validate compression level is in valid range."""
        if not 1 <= level <= 9:
            logging.warning("Invalid compression level %d, must be 1-9. Using default 6.", level)
            return 6
        return level

    @field_validator("COMPRESSION_THRESHOLD_BYTES", mode="after")
    def validate_compression_threshold(cls, threshold: int) -> int:
        """Validate compression threshold is reasonable."""
        if threshold < 0:
            logging.warning("Invalid compression threshold %d, must be >= 0. Using default 512.", threshold)
            return 512
        return threshold

    def model_post_init(self, __context):
        """Post-initialization validation for environment-specific rules."""
        if self.ENVIRONMENT == "prod":
            # Production security validations
            if self.DEBUG:
                logging.error("PRODUCTION ERROR: DEBUG mode is enabled in production. Set APP_DEBUG=false")
                raise ValueError("DEBUG must be False in production")

            if "*" in self.CORS_DOMAINS:
                logging.error(
                    "PRODUCTION ERROR: CORS wildcard (*) is not allowed in production. "
                    "Set specific domains in APP_CORS_DOMAINS"
                )
                raise ValueError("CORS wildcard not allowed in production")

            if self.RELOAD:
                logging.warning(
                    "PRODUCTION WARNING: Auto-reload is enabled in production. "
                    "Set APP_RELOAD=false for better performance"
                )

            if self.LOG_FORMAT != "json":
                logging.warning(
                    "PRODUCTION WARNING: Log format is not JSON. "
                    "Set APP_LOG_FORMAT=json for structured logging in production"
                )

            # Warn if metrics endpoint is not secured in production
            if not self.METRICS_TOKEN:
                logging.warning(
                    "PRODUCTION WARNING: Metrics endpoint is not secured. "
                    "Set APP_METRICS_TOKEN to enable authentication for /metrics"
                )

            logging.info("Production environment validated successfully")


config = Config()


def get_config() -> Config:
    return config
