"""Authentication API routes."""

import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.api.dto.auth_dto import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.api.dto.Error import ErrorResponse
from app.config import config
from app.containers import Container
from app.db.models import UserEntity
from app.dependencies.auth import get_current_user
from app.ratelimit import create_limit_resolver, limiter
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

auth_route = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_route.post(
    "/register",
    response_model=MessageResponse,
    responses={
        200: {"model": MessageResponse},
        409: {"model": ErrorResponse, "description": "User already exists"},
        400: {"model": ErrorResponse, "description": "Validation error"},
    },
    summary="Register a new user",
    description="Create a new user account. A verification email will be sent.",
)
@limiter.limit(create_limit_resolver(config, "auth_register"))
@inject
async def register(
    request: Request,
    body: RegisterRequest,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
) -> MessageResponse:
    """Register a new user account."""
    await auth_service.register(
        username=body.username,
        email=body.email,
        password=body.password,
    )
    return MessageResponse(
        message="Registration successful. Please check your email to verify your account."
    )


@auth_route.post(
    "/login",
    response_model=TokenResponse,
    responses={
        200: {"model": TokenResponse},
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        403: {
            "model": ErrorResponse,
            "description": "Email not verified or account inactive",
        },
    },
    summary="Login",
    description="Authenticate with username/email and password to receive access and refresh tokens.",
)
@limiter.limit(create_limit_resolver(config, "auth_login"))
@inject
async def login(
    request: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
) -> TokenResponse:
    """Authenticate user and return tokens."""
    user_agent = request.headers.get("user-agent")
    ip_address = str(request.state.user_metadata.ip)

    access_token, refresh_token, expires_in = await auth_service.login(
        username=body.username,
        password=body.password,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@auth_route.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        200: {"model": TokenResponse},
        401: {
            "model": ErrorResponse,
            "description": "Invalid or expired refresh token",
        },
    },
    summary="Refresh tokens",
    description="Exchange a refresh token for new access and refresh tokens.",
)
@limiter.limit(create_limit_resolver(config, "auth_refresh"))
@inject
async def refresh_tokens(
    request: Request,
    body: RefreshTokenRequest,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    user_agent = request.headers.get("user-agent")
    ip_address = str(request.state.user_metadata.ip)

    access_token, refresh_token, expires_in = await auth_service.refresh_tokens(
        refresh_token=body.refresh_token,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@auth_route.post(
    "/verify-email",
    response_model=MessageResponse,
    responses={
        200: {"model": MessageResponse},
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
    },
    summary="Verify email",
    description="Verify email address using the token sent via email.",
)
@limiter.limit(create_limit_resolver(config, "auth_verify_email"))
@inject
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
) -> MessageResponse:
    """Verify user's email address."""
    await auth_service.verify_email(token=body.token)
    return MessageResponse(message="Email verified successfully. You can now login.")


@auth_route.post(
    "/resend-verification",
    response_model=MessageResponse,
    responses={
        200: {"model": MessageResponse},
    },
    summary="Resend verification email",
    description="Resend the email verification link. Rate limited to prevent abuse.",
)
@limiter.limit(create_limit_resolver(config, "auth_resend_verification"))
@inject
async def resend_verification(
    request: Request,
    body: ResendVerificationRequest,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
) -> MessageResponse:
    """Resend email verification link."""
    await auth_service.resend_verification_email(email=body.email)
    # Always return success to prevent email enumeration
    return MessageResponse(
        message="If an unverified account exists with this email, a verification link has been sent."
    )


@auth_route.post(
    "/forgot-password",
    response_model=MessageResponse,
    responses={
        200: {"model": MessageResponse},
    },
    summary="Forgot password",
    description="Request a password reset email. Rate limited to prevent abuse.",
)
@limiter.limit(create_limit_resolver(config, "auth_forgot_password"))
@inject
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
) -> MessageResponse:
    """Request password reset email."""
    await auth_service.forgot_password(email=body.email)
    # Always return success to prevent email enumeration
    return MessageResponse(
        message="If an account exists with this email, a password reset link has been sent."
    )


@auth_route.post(
    "/reset-password",
    response_model=MessageResponse,
    responses={
        200: {"model": MessageResponse},
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
    },
    summary="Reset password",
    description="Reset password using the token sent via email.",
)
@limiter.limit(create_limit_resolver(config, "auth_reset_password"))
@inject
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
) -> MessageResponse:
    """Reset user's password."""
    await auth_service.reset_password(
        token=body.token,
        new_password=body.new_password,
    )
    return MessageResponse(
        message="Password reset successful. You can now login with your new password."
    )


@auth_route.get(
    "/me",
    response_model=UserResponse,
    responses={
        200: {"model": UserResponse},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="Get current user",
    description="Get the currently authenticated user's profile.",
)
@limiter.limit(create_limit_resolver(config, "auth_me"))
async def get_me(
    request: Request,
    user: UserEntity = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user's profile."""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_verified=user.is_verified,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@auth_route.post(
    "/logout",
    response_model=MessageResponse,
    responses={
        200: {"model": MessageResponse},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="Logout",
    description="Logout by revoking the current refresh token or all tokens.",
)
@limiter.limit(create_limit_resolver(config, "auth_logout"))
@inject
async def logout(
    request: Request,
    user: UserEntity = Depends(get_current_user),
    body: RefreshTokenRequest | None = None,
    auth_service: AuthService = Depends(Provide[Container.auth_service]),
) -> MessageResponse:
    """Logout user by revoking refresh tokens."""
    refresh_token = body.refresh_token if body else None
    await auth_service.logout(
        user_id=user.id,
        refresh_token=refresh_token,
    )
    return MessageResponse(message="Logged out successfully.")
