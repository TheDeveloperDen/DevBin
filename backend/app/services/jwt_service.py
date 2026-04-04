"""JWT token service for authentication."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import NamedTuple

import jwt

from app.config import Config
from app.exceptions import InvalidJWTError, TokenExpiredError


class TokenType(str, Enum):
    """JWT token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(NamedTuple):
    """Decoded JWT token payload."""

    user_id: uuid.UUID
    token_type: TokenType
    jti: str  # JWT ID for refresh token tracking
    exp: datetime
    iat: datetime


class TokenResult(NamedTuple):
    """Result of token creation."""

    token: str
    expires_at: datetime
    jti: str


class JWTService:
    """Service for creating and validating JWT tokens."""

    def __init__(self, config: Config):
        self.config = config
        self.secret_key = config.JWT_SECRET_KEY
        self.algorithm = config.JWT_ALGORITHM
        self.access_token_expire_minutes = config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = config.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_access_token(self, user_id: uuid.UUID) -> TokenResult:
        """
        Create a new access token.

        Args:
            user_id: The user's UUID

        Returns:
            TokenResult with the token string and expiration time
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self.access_token_expire_minutes)
        jti = str(uuid.uuid4())

        payload = {
            "sub": str(user_id),
            "type": TokenType.ACCESS.value,
            "jti": jti,
            "iat": now,
            "exp": expires_at,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        self.logger.debug("Created access token for user %s", user_id)

        return TokenResult(token=token, expires_at=expires_at, jti=jti)

    def create_refresh_token(
        self, user_id: uuid.UUID, jti: str | None = None
    ) -> TokenResult:
        """
        Create a new refresh token.

        Args:
            user_id: The user's UUID
            jti: Optional JWT ID (generated if not provided)

        Returns:
            TokenResult with the token string and expiration time
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=self.refresh_token_expire_days)
        token_jti = jti or str(uuid.uuid4())

        payload = {
            "sub": str(user_id),
            "type": TokenType.REFRESH.value,
            "jti": token_jti,
            "iat": now,
            "exp": expires_at,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        self.logger.debug("Created refresh token for user %s", user_id)

        return TokenResult(token=token, expires_at=expires_at, jti=token_jti)

    def decode_token(
        self, token: str, expected_type: TokenType | None = None
    ) -> TokenPayload:
        """
        Decode and validate a JWT token.

        Args:
            token: The JWT token string
            expected_type: Expected token type (access or refresh)

        Returns:
            TokenPayload with decoded token information

        Raises:
            TokenExpiredError: If the token has expired
            InvalidJWTError: If the token is invalid or malformed
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require": ["sub", "type", "jti", "exp", "iat"]},
            )

            token_type = TokenType(payload["type"])

            if expected_type and token_type != expected_type:
                raise InvalidJWTError(
                    f"Expected {expected_type.value} token, got {token_type.value}"
                )

            return TokenPayload(
                user_id=uuid.UUID(payload["sub"]),
                token_type=token_type,
                jti=payload["jti"],
                exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
                iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
            )

        except jwt.ExpiredSignatureError as e:
            self.logger.debug("Token expired")
            token_type_name = expected_type.value if expected_type else "token"
            raise TokenExpiredError(token_type_name) from e

        except jwt.InvalidTokenError as e:
            self.logger.warning("Invalid token: %s", str(e))
            raise InvalidJWTError(f"Invalid token: {e}") from e

        except (KeyError, ValueError) as e:
            self.logger.warning("Malformed token payload: %s", str(e))
            raise InvalidJWTError("Malformed token payload") from e
