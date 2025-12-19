import ipaddress
import logging
from typing import Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings

from app.utils.ip import resolve_hostname, validate_ip_address


class Config(BaseSettings):
    PORT: int = Field(default=8000, validation_alias="APP_PORT")
    HOST: str = Field(default="0.0.0.0", validation_alias="APP_HOST")

    # DB
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        validation_alias="APP_DATABASE_URL",
    )
    SQLALCHEMY_ECHO: bool = Field(default=False, validation_alias="APP_SQLALCHEMY_ECHO")

    # Paste
    MAX_CONTENT_LENGTH: int = Field(
        default=10000, validation_alias="APP_MAX_CONTENT_LENGTH"
    )
    BASE_FOLDER_PATH: str = Field(
        default="./files", validation_alias="APP_BASE_FOLDER_PATH"
    )
    WORKERS: int | Literal[True] = Field(default=1, validation_alias="APP_WORKERS")
    BYPASS_TOKEN: str | None = Field(default=None, validation_alias="APP_BYPASS_TOKEN")

    CORS_DOMAINS: list[str] = Field(default=["*"], validation_alias="APP_CORS_DOMAINS")

    ALLOW_CORS_WILDCARD: bool = Field(
        default=False,
        validation_alias="APP_ALLOW_CORS_WILDCARD",
        description="Allow wildcard (*) in CORS domains (disable in production)",
    )

    SAVE_USER_AGENT: bool = Field(default=False, validation_alias="APP_SAVE_USER_AGENT")
    SAVE_IP_ADDRESS: bool = Field(default=False, validation_alias="APP_SAVE_IP_ADDRESS")

    CACHE_SIZE_LIMIT: int = Field(default=1000, validation_alias="APP_CACHE_SIZE_LIMIT")
    CACHE_TTL: int = Field(default=300, validation_alias="APP_CACHE_TTL")

    MIN_STORAGE_MB: int = Field(
        default=1024,
        validation_alias="APP_MIN_STORAGE_MB",
        description="Minimum storage size in MB free",
    )

    KEEP_DELETED_PASTES_TIME_HOURS: int = Field(
        default=336,
        validation_alias="APP_KEEP_DELETED_PASTES_TIME_HOURS",
        description="Keep deleted pastes for X hours ( Default 336 hours, 2 weeks, -1 disable, 0 instant )",
    )

    TRUSTED_HOSTS: list[str] = Field(
        default=["127.0.0.1"],
        validation_alias="APP_TRUSTED_HOSTS",
        description="Trusted hosts where X-Forwarded-For header is to be trusted",
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
    def verify_trusted_hosts(cls, hosts: list[str]) -> list[str]:
        validated_hosts = []
        for host in hosts:
            validated_ip = validate_ip_address(host)
            if validated_ip:
                validated_hosts.append(validated_ip)
            else:
                validated_host = resolve_hostname(host)
                if validated_host is not None:
                    validated_hosts.append(validated_host)
        logging.info("Trusted hosts: %s", validated_hosts)
        return validated_hosts

    @field_validator("CORS_DOMAINS", mode="after")
    def validate_cors_domains(cls, domains: list[str], info) -> list[str]:
        """Validate CORS domains and warn/error on wildcard."""
        if "*" in domains:
            allow_wildcard = info.data.get("ALLOW_CORS_WILDCARD", False)

            if not allow_wildcard:
                logging.error(
                    "SECURITY WARNING: CORS wildcard (*) is NOT allowed. "
                    "Set APP_ALLOW_CORS_WILDCARD=true to enable, "
                    "or specify exact domains in APP_CORS_DOMAINS."
                )
                raise ValueError(
                    "CORS wildcard (*) is disabled. "
                    "Set APP_ALLOW_CORS_WILDCARD=true or use specific domains."
                )
            else:
                logging.warning(
                    "SECURITY WARNING: CORS wildcard (*) allows ANY origin. "
                    "Use only in development, NEVER in production!"
                )

        logging.info("CORS domains: %s", domains)
        return domains


config = Config()


def get_config() -> Config:
    return config
