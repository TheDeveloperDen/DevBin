from fastapi import APIRouter

well_known_route = APIRouter(prefix="/.well-known", tags=[".well-known"])


@well_known_route.get("/security.txt")
async def security_txt():
    return {
        "Contact": "https://github.com/DevBins/backend/issues",
    }


@well_known_route.get("/robots.txt")
async def robots_txt():
    return {
        "User-agent": "*",
        "Disallow": "/",
    }
