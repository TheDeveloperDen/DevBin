from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.middlewares import UserMetadataMiddleware
from app.containers import Container
from app.ratelimit import limiter


def _build_container() -> Container:
    container = Container()
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


def apply_rate_limiter(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def create_app() -> FastAPI:
    from app.api.routes import router
    app = FastAPI(title="DevBins API", version="0.1.0", lifespan=lifespan)
    apply_rate_limiter(app)
    app.add_middleware(UserMetadataMiddleware)
    app.include_router(router)
    return app


# Expose ASGI app
app = create_app()


def main():
    import uvicorn

    uvicorn.run("main:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")),
                reload=os.getenv("RELOAD", "true").lower() == "true")


if __name__ == "__main__":
    main()
