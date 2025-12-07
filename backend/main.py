from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.subroutes.pastes import pastes_route
from app.containers import Container


def _build_container() -> Container:
    container = Container()
    # Configure from environment with sensible defaults
    container.config.db.url.from_env(
        "DATABASE_URL",
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
    )
    container.config.db.echo.from_env("SQLALCHEMY_ECHO", as_=bool, default=False)
    return container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = _build_container()
    app.container = container  # type: ignore[attr-defined]

    # Initialize resources (e.g., DB engine) and wire dependencies
    await container.init_resources()
    container.wire()

    try:
        yield
    finally:
        await container.shutdown_resources()


def create_app() -> FastAPI:
    app = FastAPI(title="DevBins API", version="0.1.0", lifespan=lifespan)
    app.include_router(pastes_route)
    return app


# Expose ASGI app
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")), reload=os.getenv("RELOAD", "true").lower() == "true")
