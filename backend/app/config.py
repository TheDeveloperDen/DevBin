from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    # DB
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
                              validation_alias="APP_DATABASE_URL")
    SQLALCHEMY_ECHO: bool = Field(default=False, validation_alias="APP_SQLALCHEMY_ECHO")

    # Paste
    MAX_CONTENT_LENGTH: int = Field(default=10000, validation_alias="APP_MAX_CONTENT_LENGTH")
    BASE_FOLDER_PATH: str = Field(default="./files", validation_alias="APP_BASE_FOLDER_PATH")
    WORKERS: int | Literal[True] = Field(default=1, validation_alias="APP_WORKERS")
    BYPASS_TOKEN: str | None = Field(default=None, validation_alias="APP_BYPASS_TOKEN")

    CORS_DOMAINS: list[str] = Field(default=["*"], validation_alias="APP_CORS_DOMAINS")

    SAVE_USER_AGENT: bool = Field(default=False, validation_alias="APP_SAVE_USER_AGENT")
    SAVE_IP_ADDRESS: bool = Field(default=False, validation_alias="APP_SAVE_IP_ADDRESS")

    CACHE_SIZE_LIMIT: int = Field(default=1000, validation_alias="APP_CACHE_SIZE_LIMIT")
    CACHE_TTL: int = Field(default=300, validation_alias="APP_CACHE_TTL")

    DEBUG: bool = Field(default=False, validation_alias="APP_DEBUG")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


config = Config()


def get_config() -> Config:
    return config
