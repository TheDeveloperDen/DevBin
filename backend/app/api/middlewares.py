import ipaddress
import logging
from typing import Literal

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.dto.user_meta_data import UserMetaData
from app.config import config
from app.utils.ip import validate_ip_address


class UserMetadataMiddleware(BaseHTTPMiddleware):
    def get_ip_address(
        self, request: Request
    ) -> ipaddress.IPv4Address | ipaddress.IPv6Address | Literal["unknown"]:
        # Try X-Forwarded-For first (proxy headers)
        forwarded = request.headers.get("X-Forwarded-For")
        ip = "unknown"

        if (
            forwarded
            and request.client
            and request.client.host
            and request.client.host in config.TRUSTED_HOSTS
        ):
            # Get first IP in the list (original client)
            split_ip = forwarded.split(",")[0].strip()

            validated_ip = validate_ip_address(split_ip)
            if validated_ip is not None:
                if validated_ip.is_private:
                    logging.warning(
                        f"Forwarded Private IP address: {ip}, maybe behind proxy/docker?"
                    )
                ip = validated_ip
            if validated_ip is None and request.client and request.client.host:
                try:
                    ip = ipaddress.ip_address(request.client.host)
                except ValueError:
                    logging.warning("Host has invalid IP.")
        else:
            # Fallback to direct client host
            if request.client and request.client.host:
                try:
                    ip = ipaddress.ip_address(request.client.host)
                except ValueError:
                    logging.warning("Host has invalid IP.")

        return ip

    async def dispatch(self, request: Request, call_next):
        # Get the user agent from headers
        user_agent = request.headers.get("user-agent", "unknown")
        ip = self.get_ip_address(request)
        # Store metadata in the request state for later use
        request.state.user_metadata = UserMetaData(ip=ip, user_agent=user_agent)

        # Continue with the request
        response = await call_next(request)
        return response
