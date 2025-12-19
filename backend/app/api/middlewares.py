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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.

    Headers added:
    - Strict-Transport-Security (HSTS) - Only on HTTPS
    - X-Content-Type-Options - Prevent MIME sniffing
    - X-Frame-Options - Prevent clickjacking
    - Content-Security-Policy - XSS protection (relaxed for /docs, /redoc)
    - X-XSS-Protection - Legacy XSS protection
    - Referrer-Policy - Control referrer information

    Note: CSP is more permissive for Swagger/ReDoc endpoints to allow
    UI functionality while remaining strict for API endpoints.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # X-Content-Type-Options: Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Content-Security-Policy: Different policies for docs vs API
        # Check if request is for Swagger/ReDoc documentation
        is_docs_endpoint = request.url.path in ["/docs", "/redoc", "/openapi.json"]

        if is_docs_endpoint:
            # Permissive CSP for Swagger UI (needs to load scripts/styles)
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' data:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'"
            )
        else:
            # Strict CSP for API endpoints (no scripts/styles needed)
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'none'; "
                "base-uri 'none'; "
                "form-action 'none'"
            )

        # X-XSS-Protection: Legacy header for older browsers
        # Modern browsers rely on CSP, but this doesn't hurt
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy: Control referrer information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Strict-Transport-Security (HSTS): Only add on HTTPS
        # Check if request came over HTTPS
        # Note: In production behind proxy, check X-Forwarded-Proto header
        is_https = (
            request.url.scheme == "https"
            or request.headers.get("X-Forwarded-Proto") == "https"
        )

        if is_https:
            # HSTS: Force HTTPS for 1 year, include subdomains
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Redirects all HTTP requests to HTTPS.

    Only active when ENFORCE_HTTPS config is True.
    Checks X-Forwarded-Proto header for proxy deployments.
    """

    async def dispatch(self, request: Request, call_next):
        # Check if request is over HTTPS
        is_https = (
            request.url.scheme == "https"
            or request.headers.get("X-Forwarded-Proto") == "https"
        )

        if not is_https:
            # Redirect to HTTPS
            from starlette.responses import RedirectResponse

            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=301)

        return await call_next(request)
