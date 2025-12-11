from aiocache.serializers import PickleSerializer
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from pydantic import UUID4
from starlette.requests import Request
from starlette.responses import Response

from app.api.dto.paste_dto import CreatePaste
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
    max_size=1000,
)


@pastes_route.get("/{paste_id}")
@limiter.limit("10/minute")
@inject
async def get_paste(request: Request, paste_id: UUID4,
                    paste_service: PasteService = Depends(Provide[Container.paste_service])):

    cached_result = await cache.get(paste_id)
    if cached_result:
        return Response(
            cached_result,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "public, max-age=3600",
            }
        )


    paste_result = await paste_service.get_paste_by_id(paste_id)
    if not paste_result:
        return Response({"error": "Paste not found"},
                        status_code=404,
                        )
    paste_result = paste_result.model_dump_json()

    await cache.set(paste_id, paste_result)

    return Response(
        paste_result,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=3600",
        }
    )


@pastes_route.post("")
@limiter.limit("4/minute")
@inject
async def create_paste(request: Request,
                       create_paste_body: CreatePaste,
                       paste_service: PasteService = Depends(Provide[Container.paste_service])):
    return await paste_service.create_paste(create_paste_body, request.state.user_metadata)
