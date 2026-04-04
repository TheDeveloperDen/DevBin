"""Authentication DTOs for request/response models."""

import re
from datetime import datetime

from pydantic import UUID4, BaseModel, EmailStr, Field, field_validator

from app.config import config


def validate_password_requirements(v: str) -> str:
    """Validate password meets configured requirements."""
    errors = []

    if config.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", v):
        errors.append("at least one uppercase letter")

    if config.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", v):
        errors.append("at least one lowercase letter")

    if config.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", v):
        errors.append("at least one digit")

    if config.PASSWORD_REQUIRE_SPECIAL and not re.search(
        r"[!@#$%^&*(),.?\":{}|<>]", v
    ):
        errors.append("at least one special character")

    if errors:
        raise ValueError(f"Password must contain {', '.join(errors)}")

    return v


class RegisterRequest(BaseModel):
    """Request model for user registration."""

    username: str = Field(
        min_length=3,
        max_length=50,
        description="Username (3-50 characters, alphanumeric and underscores)",
        examples=["john_doe"],
    )
    email: EmailStr = Field(
        description="Valid email address",
        examples=["john@example.com"],
    )
    password: str = Field(
        min_length=config.PASSWORD_MIN_LENGTH,
        max_length=128,
        description="Password meeting security requirements",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError(
                "Username must start with a letter and contain only letters, numbers, and underscores"
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets requirements."""
        return validate_password_requirements(v)


class LoginRequest(BaseModel):
    """Request model for user login."""

    username: str = Field(
        min_length=1,
        max_length=512,
        description="Username or email",
        examples=["john_doe"],
    )
    password: str = Field(
        min_length=1,
        max_length=512,
        description="User password",
    )


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(
        description="JWT refresh token for obtaining new access tokens"
    )
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(description="Access token expiration time in seconds")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str = Field(description="Refresh token to exchange for new tokens")


class VerifyEmailRequest(BaseModel):
    """Request model for email verification."""

    token: str = Field(description="Email verification token")


class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""

    email: EmailStr = Field(
        description="Email address associated with the account",
        examples=["john@example.com"],
    )


class ResetPasswordRequest(BaseModel):
    """Request model for password reset."""

    token: str = Field(description="Password reset token")
    new_password: str = Field(
        min_length=config.PASSWORD_MIN_LENGTH,
        max_length=128,
        description="New password meeting security requirements",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets requirements."""
        return validate_password_requirements(v)


class ResendVerificationRequest(BaseModel):
    """Request model for resending verification email."""

    email: EmailStr = Field(
        description="Email address to resend verification to",
        examples=["john@example.com"],
    )


class UserResponse(BaseModel):
    """Response model for user profile."""

    id: UUID4 = Field(description="User UUID")
    username: str = Field(description="Username")
    email: EmailStr = Field(description="Email address")
    is_verified: bool = Field(description="Whether email is verified")
    created_at: datetime = Field(description="Account creation timestamp")
    last_login_at: datetime | None = Field(description="Last login timestamp")

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(description="Response message")
