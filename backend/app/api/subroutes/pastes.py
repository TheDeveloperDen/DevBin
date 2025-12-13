from typing import Optional, Any

import slowapi
from aiocache.serializers import PickleSerializer
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from pydantic import UUID4
from slowapi.util import get_ipaddr
from starlette.requests import Request
from starlette.responses import Response
from uuid import uuid4

from app.api.dto.paste_dto import CreatePaste
from app.config import Config, config
from app.containers import Container
from app.ratelimit import limiter
from app.services.paste_service import PasteService
from app.utils.LRUMemoryCache import LRUMemoryCache

pastes_route = APIRouter(
    prefix="/pastes",
    tags=["Paste"]
)
cache = LRUMemoryCache(
    serializer=PickleSerializer(),
    max_size=config.CACHE_SIZE_LIMIT,
)


def get_exempt_key(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header != config.BYPASS_TOKEN:
        return get_ipaddr(request)

    return str(uuid4())  # To simulate a new request if it is the BYPASS_TOKEN


@pastes_route.get("/{paste_id}")
@limiter.limit("10/minute", key_func=get_exempt_key)
@inject
async def get_paste(request: Request, paste_id: UUID4,
                    paste_service: PasteService = Depends(Provide[Container.paste_service])):
    cached_result = await cache.get(paste_id)
    if cached_result:
        return Response(
            cached_result,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": f"public, max-age={config.CACHE_TTL}",
            }
        )

    paste_result = await paste_service.get_paste_by_id(paste_id)
    if not paste_result:
        return Response({"error": "Paste not found"},
                        status_code=404,
                        )
    paste_result = paste_result.model_dump_json()

    await cache.set(paste_id, paste_result, ttl=config.CACHE_TTL)

    return Response(
        paste_result,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": f"public, max-age={config.CACHE_TTL}",
        }
    )


@pastes_route.post("")
@limiter.limit("4/minute", key_func=get_exempt_key)
@inject
async def create_paste(request: Request,
                       create_paste_body: CreatePaste,
                       paste_service: PasteService = Depends(Provide[Container.paste_service])):
    return await paste_service.create_paste(create_paste_body, request.state.user_metadata)
