"""Authentication service for user management and auth flows."""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import HashingError, InvalidHashError, VerifyMismatchError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.db.models import (
    EmailVerificationTokenEntity,
    PasswordResetTokenEntity,
    RefreshTokenEntity,
    UserEntity,
)
from app.exceptions import (
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidJWTError,
    TokenExpiredError,
    UserAlreadyExistsError,
    UserInactiveError,
    UserNotFoundError,
)
from app.services.email_service import EmailService
from app.services.jwt_service import JWTService, TokenType


class AuthService:
    """Service for handling authentication operations."""

    def __init__(
        self,
        session_factory: sessionmaker[AsyncSession],
        jwt_service: JWTService,
        email_service: EmailService,
        config: Config,
    ):
        self.session_factory = session_factory
        self.jwt_service = jwt_service
        self.email_service = email_service
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        # Argon2id with OWASP recommended parameters
        self.password_hasher = PasswordHasher(
            time_cost=2,
            memory_cost=19456,  # 19 MiB
            parallelism=1,
        )

    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage using SHA-256."""
        return hashlib.sha256(token.encode()).hexdigest()

    def _generate_token(self) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(32)

    def _hash_password(self, password: str) -> str:
        """Hash a password using Argon2id."""
        return self.password_hasher.hash(password)

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            self.password_hasher.verify(password_hash, password)
            return True
        except (VerifyMismatchError, InvalidHashError, HashingError):
            return False

    async def register(
        self,
        username: str,
        email: str,
        password: str,
    ) -> UserEntity:
        """
        Register a new user.

        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password

        Returns:
            Created user entity

        Raises:
            UserAlreadyExistsError: If username or email already exists
        """
        async with self.session_factory() as session:
            # Check for existing user
            existing = await session.execute(
                select(UserEntity).where(
                    (UserEntity.username == username.lower())
                    | (UserEntity.email == email.lower())
                )
            )
            if existing.scalar_one_or_none():
                raise UserAlreadyExistsError()

            # Create user
            user = UserEntity(
                username=username.lower(),
                email=email.lower(),
                password_hash=self._hash_password(password),
                is_verified=False,
                is_active=True,
            )
            session.add(user)
            await session.flush()

            # Create verification token
            token = self._generate_token()
            verification_token = EmailVerificationTokenEntity(
                user_id=user.id,
                token_hash=self._hash_token(token),
                expires_at=datetime.now(UTC)
                + timedelta(hours=self.config.EMAIL_VERIFICATION_EXPIRE_HOURS),
            )
            session.add(verification_token)
            await session.commit()

            # Send verification email (don't wait for result)
            await self.email_service.send_verification_email(
                to=user.email,
                username=user.username,
                token=token,
            )

            self.logger.info("User registered: %s", user.username)
            return user

    async def verify_email(self, token: str) -> UserEntity:
        """
        Verify a user's email address.

        Args:
            token: Email verification token

        Returns:
            Verified user entity

        Raises:
            TokenExpiredError: If token has expired
            InvalidJWTError: If token is invalid
        """
        token_hash = self._hash_token(token)

        async with self.session_factory() as session:
            result = await session.execute(
                select(EmailVerificationTokenEntity).where(
                    EmailVerificationTokenEntity.token_hash == token_hash,
                    EmailVerificationTokenEntity.used_at.is_(None),
                )
            )
            verification = result.scalar_one_or_none()

            if not verification:
                raise InvalidJWTError("Invalid or already used verification token")

            if verification.expires_at < datetime.now(UTC):
                raise TokenExpiredError("verification token")

            # Mark token as used
            verification.used_at = datetime.now(UTC)

            # Mark user as verified
            user_result = await session.execute(
                select(UserEntity).where(UserEntity.id == verification.user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                raise UserNotFoundError()

            user.is_verified = True
            await session.commit()

            self.logger.info("Email verified for user: %s", user.username)
            return user

    async def login(
        self,
        username: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, int]:
        """
        Authenticate a user and return tokens.

        Args:
            username: Username or email
            password: Plain text password
            user_agent: Optional user agent for session tracking
            ip_address: Optional IP address for session tracking

        Returns:
            Tuple of (access_token, refresh_token, expires_in_seconds)

        Raises:
            InvalidCredentialsError: If credentials are invalid
            EmailNotVerifiedError: If email is not verified
            UserInactiveError: If user account is deactivated
        """
        async with self.session_factory() as session:
            # Find user by username or email
            result = await session.execute(
                select(UserEntity).where(
                    (UserEntity.username == username.lower())
                    | (UserEntity.email == username.lower())
                )
            )
            user = result.scalar_one_or_none()

            if not user or not self._verify_password(password, user.password_hash):
                raise InvalidCredentialsError()

            if not user.is_active:
                raise UserInactiveError()

            if not user.is_verified:
                raise EmailNotVerifiedError()

            # Create tokens
            access_result = self.jwt_service.create_access_token(user.id)
            refresh_result = self.jwt_service.create_refresh_token(user.id)

            # Store refresh token
            refresh_token_entity = RefreshTokenEntity(
                user_id=user.id,
                token_hash=self._hash_token(refresh_result.token),
                expires_at=refresh_result.expires_at,
                user_agent=user_agent[:512] if user_agent else None,
                ip_address=ip_address,
            )
            session.add(refresh_token_entity)

            # Update last login
            user.last_login_at = datetime.now(UTC)
            await session.commit()

            self.logger.info("User logged in: %s", user.username)

            expires_in = int(
                (access_result.expires_at - datetime.now(UTC)).total_seconds()
            )
            return access_result.token, refresh_result.token, expires_in

    async def refresh_tokens(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, int]:
        """
        Refresh access token using refresh token.

        Implements token rotation - old refresh token is revoked.

        Args:
            refresh_token: Current refresh token
            user_agent: Optional user agent for session tracking
            ip_address: Optional IP address for session tracking

        Returns:
            Tuple of (new_access_token, new_refresh_token, expires_in_seconds)

        Raises:
            InvalidJWTError: If refresh token is invalid
            TokenExpiredError: If refresh token has expired
        """
        # Decode and validate the refresh token
        payload = self.jwt_service.decode_token(refresh_token, TokenType.REFRESH)
        token_hash = self._hash_token(refresh_token)

        async with self.session_factory() as session:
            # Find the refresh token in DB
            result = await session.execute(
                select(RefreshTokenEntity).where(
                    RefreshTokenEntity.token_hash == token_hash,
                    RefreshTokenEntity.revoked_at.is_(None),
                )
            )
            stored_token = result.scalar_one_or_none()

            if not stored_token:
                raise InvalidJWTError("Refresh token not found or already revoked")

            if stored_token.expires_at < datetime.now(UTC):
                raise TokenExpiredError("refresh token")

            # Verify user exists and is active
            user_result = await session.execute(
                select(UserEntity).where(UserEntity.id == payload.user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user or not user.is_active:
                raise InvalidJWTError("User not found or inactive")

            # Revoke old token (rotation)
            stored_token.revoked_at = datetime.now(UTC)

            # Create new tokens
            access_result = self.jwt_service.create_access_token(user.id)
            new_refresh_result = self.jwt_service.create_refresh_token(user.id)

            # Store new refresh token
            new_refresh_token = RefreshTokenEntity(
                user_id=user.id,
                token_hash=self._hash_token(new_refresh_result.token),
                expires_at=new_refresh_result.expires_at,
                user_agent=user_agent[:512] if user_agent else None,
                ip_address=ip_address,
            )
            session.add(new_refresh_token)
            await session.commit()

            self.logger.debug("Tokens refreshed for user: %s", user.username)

            expires_in = int(
                (access_result.expires_at - datetime.now(UTC)).total_seconds()
            )
            return access_result.token, new_refresh_result.token, expires_in

    async def forgot_password(self, email: str) -> bool:
        """
        Initiate password reset flow.

        Always returns True to prevent email enumeration.

        Args:
            email: Email address

        Returns:
            True (always, to prevent enumeration)
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserEntity).where(UserEntity.email == email.lower())
            )
            user = result.scalar_one_or_none()

            if not user:
                # Don't reveal if email exists
                self.logger.debug("Password reset requested for unknown email")
                return True

            # Invalidate existing reset tokens
            await session.execute(
                update(PasswordResetTokenEntity)
                .where(
                    PasswordResetTokenEntity.user_id == user.id,
                    PasswordResetTokenEntity.used_at.is_(None),
                )
                .values(used_at=datetime.now(UTC))
            )

            # Create new reset token
            token = self._generate_token()
            reset_token = PasswordResetTokenEntity(
                user_id=user.id,
                token_hash=self._hash_token(token),
                expires_at=datetime.now(UTC)
                + timedelta(hours=self.config.PASSWORD_RESET_EXPIRE_HOURS),
            )
            session.add(reset_token)
            await session.commit()

            # Send reset email
            await self.email_service.send_password_reset_email(
                to=user.email,
                username=user.username,
                token=token,
            )

            self.logger.info("Password reset email sent to: %s", user.email)
            return True

    async def reset_password(self, token: str, new_password: str) -> UserEntity:
        """
        Reset user's password.

        Args:
            token: Password reset token
            new_password: New plain text password

        Returns:
            Updated user entity

        Raises:
            TokenExpiredError: If token has expired
            InvalidJWTError: If token is invalid
        """
        token_hash = self._hash_token(token)

        async with self.session_factory() as session:
            result = await session.execute(
                select(PasswordResetTokenEntity).where(
                    PasswordResetTokenEntity.token_hash == token_hash,
                    PasswordResetTokenEntity.used_at.is_(None),
                )
            )
            reset_token = result.scalar_one_or_none()

            if not reset_token:
                raise InvalidJWTError("Invalid or already used reset token")

            if reset_token.expires_at < datetime.now(UTC):
                raise TokenExpiredError("password reset token")

            # Mark token as used
            reset_token.used_at = datetime.now(UTC)

            # Update password
            user_result = await session.execute(
                select(UserEntity).where(UserEntity.id == reset_token.user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                raise UserNotFoundError()

            user.password_hash = self._hash_password(new_password)

            # Revoke all refresh tokens (force re-login)
            refresh_result = await session.execute(
                select(RefreshTokenEntity).where(
                    RefreshTokenEntity.user_id == user.id,
                    RefreshTokenEntity.revoked_at.is_(None),
                )
            )
            for refresh_token_entity in refresh_result.scalars():
                refresh_token_entity.revoked_at = datetime.now(UTC)

            await session.commit()

            self.logger.info("Password reset for user: %s", user.username)
            return user

    async def logout(self, user_id: UUID, refresh_token: str | None = None) -> bool:
        """
        Logout user by revoking refresh tokens.

        Args:
            user_id: User's UUID
            refresh_token: Optional specific refresh token to revoke.
                          If None, revokes all user's refresh tokens.

        Returns:
            True if tokens were revoked
        """
        async with self.session_factory() as session:
            if refresh_token:
                # Revoke specific token
                token_hash = self._hash_token(refresh_token)
                result = await session.execute(
                    select(RefreshTokenEntity).where(
                        RefreshTokenEntity.user_id == user_id,
                        RefreshTokenEntity.token_hash == token_hash,
                        RefreshTokenEntity.revoked_at.is_(None),
                    )
                )
                token_entity = result.scalar_one_or_none()
                if token_entity:
                    token_entity.revoked_at = datetime.now(UTC)
            else:
                # Revoke all tokens
                result = await session.execute(
                    select(RefreshTokenEntity).where(
                        RefreshTokenEntity.user_id == user_id,
                        RefreshTokenEntity.revoked_at.is_(None),
                    )
                )
                for token_entity in result.scalars():
                    token_entity.revoked_at = datetime.now(UTC)

            await session.commit()
            self.logger.debug("Logged out user: %s", user_id)
            return True

    async def resend_verification_email(self, email: str) -> bool:
        """
        Resend verification email.

        Args:
            email: Email address

        Returns:
            True (always, to prevent enumeration)
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserEntity).where(
                    UserEntity.email == email.lower(),
                    UserEntity.is_verified == False,  # noqa: E712
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                # Don't reveal if email exists or is already verified
                return True

            # Invalidate existing verification tokens
            await session.execute(
                update(EmailVerificationTokenEntity)
                .where(
                    EmailVerificationTokenEntity.user_id == user.id,
                    EmailVerificationTokenEntity.used_at.is_(None),
                )
                .values(used_at=datetime.now(UTC))
            )

            # Create new verification token
            token = self._generate_token()
            verification_token = EmailVerificationTokenEntity(
                user_id=user.id,
                token_hash=self._hash_token(token),
                expires_at=datetime.now(UTC)
                + timedelta(hours=self.config.EMAIL_VERIFICATION_EXPIRE_HOURS),
            )
            session.add(verification_token)
            await session.commit()

            # Send verification email
            await self.email_service.send_verification_email(
                to=user.email,
                username=user.username,
                token=token,
            )

            self.logger.info("Verification email resent to: %s", user.email)
            return True

    async def get_user_by_id(self, user_id: UUID) -> UserEntity | None:
        """
        Get user by ID.

        Args:
            user_id: User's UUID

        Returns:
            User entity or None if not found
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(UserEntity).where(UserEntity.id == user_id)
            )
            return result.scalar_one_or_none()
