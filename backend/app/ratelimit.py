import logging
from typing import Callable, Literal
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
    "edit_paste",
    "delete_paste",
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
        if auth_header and config.RATELIMIT_BYPASS_TOKENS:
            if auth_header in config.RATELIMIT_BYPASS_TOKENS:
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
        "edit_paste": config.RATELIMIT_EDIT_PASTE,
        "delete_paste": config.RATELIMIT_DELETE_PASTE,
    }

    limit_value = limit_map.get(limit_name, config.RATELIMIT_DEFAULT)

    def resolver() -> str:
        return limit_value

    return resolver


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
            logger.info("Rate limiter using Redis backend: %s:%d", config.REDIS_HOST, config.REDIS_PORT)
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
