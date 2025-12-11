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
    WORKERS: int | Literal[True] = Field(default=True, validation_alias="APP_WORKERS")
    BYPASS_TOKEN: str | None = Field(default=None, validation_alias="APP_BYPASS_TOKEN")

    DEBUG: bool = Field(default=False, validation_alias="APP_DEBUG")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


config = Config()


def get_config() -> Config:
    return config
