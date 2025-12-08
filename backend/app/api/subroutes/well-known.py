from fastapi import APIRouter

well_known_route = APIRouter(
    prefix="/.well-known",
    tags=[".well-known"]
)


@well_known_route.get("/security.txt")
async def security_txt():
    return {
        "Contact": "https://github.com/DevBins/backend/issues",
    }
