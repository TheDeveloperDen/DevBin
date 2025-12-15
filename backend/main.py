from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware

from app.api.middlewares import UserMetadataMiddleware
from app.config import config
from app.containers import Container
from app.ratelimit import limiter
from app.services.paste_service import PasteService


# Set the custom encoder
def _build_container() -> Container:
    container = Container()
    return container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = _build_container()
    app.container = container  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]

    # Initialize resources (e.g., DB engine) and wire dependencies
    await container.init_resources()  # pyright: ignore[reportGeneralTypeIssues]
    container.wire()
    paste_service: PasteService = (
        await container.paste_service()  # pyright: ignore[reportGeneralTypeIssues]
    )  # or however you resolve it
    paste_service.start_cleanup_worker()
    try:
        yield
    finally:
        await paste_service.stop_cleanup_worker()
        await container.shutdown_resources()  # pyright: ignore[reportGeneralTypeIssues]


def apply_rate_limiter(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def create_app() -> FastAPI:
    from app.api.routes import router

    if config.DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    app = FastAPI(
        title="DevBins API",
        version="0.1.0-alpha",
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )
    apply_rate_limiter(app)
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_DOMAINS,  # Adjust this to your needs
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(UserMetadataMiddleware)
    app.include_router(router)
    return app


# Expose ASGI app
app = create_app()


def main():
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=int(config.PORT),
        reload=config.RELOAD,
        server_header=False,
        workers=os.cpu_count() or 1 if config.WORKERS is True else config.WORKERS,
        log_level=None if config.DEBUG else "info",
        proxy_headers=False,
    )


if __name__ == "__main__":
    main()
