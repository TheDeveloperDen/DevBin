"""Authentication dependencies for FastAPI routes."""

from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.containers import Container
from app.db.models import UserEntity
from app.exceptions import (
    EmailNotVerifiedError,
    InvalidJWTError,
    TokenExpiredError,
    UserInactiveError,
    UserNotFoundError,
)
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService, TokenType

# HTTPBearer scheme for OpenAPI documentation
auth_scheme = HTTPBearer(
    auto_error=True,
    description="JWT Bearer token authentication",
)

# Optional version that doesn't raise on missing token
auth_scheme_optional = HTTPBearer(
    auto_error=False,
    description="Optional JWT Bearer token authentication",
)


@inject
async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
    jwt_service: JWTService = Depends(Provide[Container.jwt_service]),
) -> UUID:
    """
    Extract and validate user ID from JWT access token.

    This is a lightweight dependency that only validates the token
    without hitting the database.

    Args:
        credentials: Bearer token from Authorization header
        jwt_service: JWT service for token validation

    Returns:
        User UUID from the token

    Raises:
        InvalidJWTError: If token is invalid
        TokenExpiredError: If token has expired
    """
    token = credentials.credentials
    payload = jwt_service.decode_token(token, expected_type=TokenType.ACCESS)
    return payload.user_id


@inject
async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
) -> UserEntity:
    """
    Get the current authenticated user from the database.

    Args:
        user_id: User ID extracted from token
        auth_service: Auth service for user lookup

    Returns:
        User entity

    Raises:
        UserNotFoundError: If user doesn't exist
        UserInactiveError: If user account is deactivated
    """
    user = await auth_service.get_user_by_id(user_id)

    if not user:
        raise UserNotFoundError()

    if not user.is_active:
        raise UserInactiveError()

    return user


async def get_current_active_verified_user(
    user: UserEntity = Depends(get_current_user),
) -> UserEntity:
    """
    Get the current authenticated user, ensuring email is verified.

    Args:
        user: Current user from get_current_user

    Returns:
        Verified user entity

    Raises:
        EmailNotVerifiedError: If email is not verified
    """
    if not user.is_verified:
        raise EmailNotVerifiedError()

    return user


@inject
async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme_optional),
    jwt_service: JWTService = Depends(Provide[Container.jwt_service]),
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
) -> UserEntity | None:
    """
    Optionally get the current authenticated user.

    Returns None if no token is provided instead of raising an error.
    Useful for routes that have different behavior for authenticated
    vs anonymous users.

    Args:
        credentials: Optional Bearer token
        jwt_service: JWT service for token validation
        auth_service: Auth service for user lookup

    Returns:
        User entity or None if not authenticated
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = jwt_service.decode_token(token, expected_type=TokenType.ACCESS)
        user = await auth_service.get_user_by_id(payload.user_id)

        if user and user.is_active:
            return user

        return None

    except (InvalidJWTError, TokenExpiredError, UserNotFoundError, UserInactiveError):
        # Invalid/expired token or inactive user treated as not authenticated
        return None
