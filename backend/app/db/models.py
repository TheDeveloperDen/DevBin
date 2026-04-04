from sqlalchemy import (
    TIMESTAMP,
    UUID,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base

UUID_DEFAULT = text("gen_random_uuid()")


class PasteEntity(Base):
    __tablename__ = "pastes"
    __table_args__ = (
        Index("idx_pastes_expires_at", "expires_at"),
        Index("idx_pastes_deleted_at", "deleted_at"),
        Index("idx_pastes_created_at", "created_at"),
        Index("idx_pastes_user_id", "user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=UUID_DEFAULT)
    title = Column(String(255), nullable=False)
    content_path = Column(String, nullable=False)
    content_language = Column(String, nullable=False, server_default="plain_text")
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    content_size = Column(Integer, nullable=False)
    is_compressed = Column(Boolean, nullable=False, server_default="false")
    original_size = Column(Integer, nullable=True)

    creator_ip = Column(String)
    creator_user_agent = Column(String)

    edit_token = Column(String)
    last_updated_at = Column(TIMESTAMP(timezone=True))

    delete_token = Column(String)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user = relationship("UserEntity", back_populates="pastes")

    def __repr__(self):
        return f"<Paste(id={self.id}, title='{self.title}')>"

    def __str__(self):
        return self.title


# ─────────────────────────────────────────────────────────────────────────────
# Authentication Models
# ─────────────────────────────────────────────────────────────────────────────


class UserEntity(Base):
    """User account for authentication."""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
        Index("idx_users_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=UUID_DEFAULT)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    is_verified = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    last_login_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    email_verification_tokens = relationship(
        "EmailVerificationTokenEntity",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_reset_tokens = relationship(
        "PasswordResetTokenEntity", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "RefreshTokenEntity", back_populates="user", cascade="all, delete-orphan"
    )
    pastes = relationship("PasteEntity", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class EmailVerificationTokenEntity(Base):
    """Token for email verification."""

    __tablename__ = "email_verification_tokens"
    __table_args__ = (
        Index("idx_email_verification_tokens_user_id", "user_id"),
        Index("idx_email_verification_tokens_expires_at", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=UUID_DEFAULT)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationship
    user = relationship("UserEntity", back_populates="email_verification_tokens")

    def __repr__(self):
        return f"<EmailVerificationToken(id={self.id}, user_id={self.user_id})>"


class PasswordResetTokenEntity(Base):
    """Token for password reset."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("idx_password_reset_tokens_user_id", "user_id"),
        Index("idx_password_reset_tokens_expires_at", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=UUID_DEFAULT)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationship
    user = relationship("UserEntity", back_populates="password_reset_tokens")

    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id})>"


class RefreshTokenEntity(Base):
    """JWT refresh token for session management."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index("idx_refresh_tokens_expires_at", "expires_at"),
        Index("idx_refresh_tokens_revoked_at", "revoked_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=UUID_DEFAULT)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # Session tracking
    user_agent = Column(String(512))
    ip_address = Column(String(45))  # IPv6 max length

    # Relationship
    user = relationship("UserEntity", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"
