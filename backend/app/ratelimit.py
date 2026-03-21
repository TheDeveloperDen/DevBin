import logging
from collections.abc import Callable
from typing import Literal
from uuid import uuid4

from slowapi import Limiter
from starlette.requests import Request

from app.config import Config, RateLimit

logger = logging.getLogger(__name__)

LimitName = Literal[
    "health",
    "get_paste",
    "get_paste_legacy",
    "create_paste",
    "create_paste_authenticated",
    "edit_paste",
    "delete_paste",
    # Auth endpoints
    "auth_register",
    "auth_login",
    "auth_refresh",
    "auth_verify_email",
    "auth_resend_verification",
    "auth_forgot_password",
    "auth_reset_password",
    "auth_me",
    "auth_logout",
]


class NoOpLimiter:
    """A limiter that does nothing when rate limiting is disabled."""

    def limit(self, *args, **kwargs) -> Callable:
        """Return a no-op decorator."""

        def decorator(func: Callable) -> Callable:
            return func

        return decorator


def get_ip_address(request: Request) -> str:
    """Extract client IP from request state."""
    return str(request.state.user_metadata.ip)


def create_exempt_key_func(config: Config) -> Callable[[Request], str]:
    """Create key function that exempts bypass tokens from rate limiting."""

    def get_exempt_key(request: Request) -> str:
        auth_header = request.headers.get("Authorization")
        if (
            auth_header
            and config.RATELIMIT_BYPASS_TOKENS
            and auth_header in config.RATELIMIT_BYPASS_TOKENS
        ):
            # Return unique key for each request = effectively unlimited
            return str(uuid4())
        return get_ip_address(request)

    return get_exempt_key


def create_limit_resolver(config: Config, limit_name: LimitName) -> Callable[[], str]:
    """Create callable that resolves the rate limit value for an endpoint."""
    limit_map: dict[LimitName, RateLimit] = {
        "health": config.RATELIMIT_HEALTH,
        "get_paste": config.RATELIMIT_GET_PASTE,
        "get_paste_legacy": config.RATELIMIT_GET_PASTE_LEGACY,
        "create_paste": config.RATELIMIT_CREATE_PASTE,
        "create_paste_authenticated": config.RATELIMIT_CREATE_PASTE_AUTHENTICATED,
        "edit_paste": config.RATELIMIT_EDIT_PASTE,
        "delete_paste": config.RATELIMIT_DELETE_PASTE,
        # Auth endpoints
        "auth_register": config.RATELIMIT_AUTH_REGISTER,
        "auth_login": config.RATELIMIT_AUTH_LOGIN,
        "auth_refresh": config.RATELIMIT_AUTH_REFRESH,
        "auth_verify_email": config.RATELIMIT_AUTH_VERIFY_EMAIL,
        "auth_resend_verification": config.RATELIMIT_AUTH_RESEND_VERIFICATION,
        "auth_forgot_password": config.RATELIMIT_AUTH_FORGOT_PASSWORD,
        "auth_reset_password": config.RATELIMIT_AUTH_RESET_PASSWORD,
        "auth_me": config.RATELIMIT_AUTH_ME,
        "auth_logout": config.RATELIMIT_AUTH_LOGOUT,
    }

    limit_value = limit_map.get(limit_name, config.RATELIMIT_DEFAULT)

    def resolver() -> str:
        return limit_value

    return resolver


def create_auth_aware_limit_resolver(
    config: Config, anon_name: LimitName, auth_name: LimitName
) -> Callable[[str], str]:
    """Create a limit callable that returns different rate limits based on the key prefix.

    slowapi calls this with the result of key_func(request) when the callable has a `key` parameter.
    Keys prefixed with "auth:" get the authenticated limit, others get the anonymous limit.
    """
    anon_limit = create_limit_resolver(config, anon_name)
    auth_limit = create_limit_resolver(config, auth_name)

    def resolver(key: str) -> str:
        if key.startswith("auth:"):
            return auth_limit()
        return anon_limit()

    return resolver


def create_auth_aware_key_func(config: Config) -> Callable[[Request], str]:
    """Create a key function that returns 'auth:{user_id}' for authenticated users and IP for anonymous."""
    exempt_key = create_exempt_key_func(config)

    def key_func(request: Request) -> str:
        user = getattr(getattr(request, "state", None), "current_user", None)
        if user is not None:
            return f"auth:{user.id}"
        return exempt_key(request)

    return key_func


def _build_redis_uri(config: Config) -> str:
    """Build Redis URI from config."""
    if config.REDIS_PASSWORD:
        return f"redis://:{config.REDIS_PASSWORD}@{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"
    return f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"


def create_rate_limiter(config: Config) -> Limiter | NoOpLimiter:
    """Factory function to create rate limiter with configurable backend.

    Args:
        config: Application configuration

    Returns:
        Limiter instance (Redis or memory-backed) or NoOpLimiter if disabled
    """
    if not config.RATELIMIT_ENABLED:
        logger.info("Rate limiting is disabled")
        return NoOpLimiter()

    if config.RATELIMIT_BACKEND == "redis":
        try:
            storage_uri = _build_redis_uri(config)
            limiter = Limiter(key_func=get_ip_address, storage_uri=storage_uri)
            logger.info(
                "Rate limiter using Redis backend: %s:%d",
                config.REDIS_HOST,
                config.REDIS_PORT,
            )
            return limiter
        except Exception as e:
            logger.warning("Redis rate limiter failed, falling back to memory: %s", e)

    logger.info("Rate limiter using memory backend")
    return Limiter(key_func=get_ip_address)


# Module-level instances (initialized during app startup)
limiter: Limiter | NoOpLimiter = NoOpLimiter()
get_exempt_key: Callable[[Request], str] = get_ip_address


def init_rate_limiter(config: Config) -> Limiter | NoOpLimiter:
    """Initialize the rate limiter with config. Called at app startup.

    Args:
        config: Application configuration

    Returns:
        The initialized limiter instance
    """
    global limiter, get_exempt_key
    limiter = create_rate_limiter(config)
    get_exempt_key = create_exempt_key_func(config)
    return limiter
