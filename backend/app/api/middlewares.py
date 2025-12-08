from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.dto.user_meta_data import UserMetaData


class UserMetadataMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get the client's IP address
        ip = request.client.host if request.client else "unknown"

        # Handle forwarded IP addresses (e.g., when behind a proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the list (the original client IP)
            ip = forwarded_for.split(",")[0].strip()

        # Get the user agent from headers
        user_agent = request.headers.get("user-agent", "unknown")

        # Store metadata in the request state for later use
        request.state.user_metadata = UserMetaData(ip=ip, user_agent=user_agent)

        # Continue with the request
        response = await call_next(request)
        return response
