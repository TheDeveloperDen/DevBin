"""Custom exception classes for DevBin backend."""


class DevBinException(Exception):
    """Base exception for all DevBin errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class PasteNotFoundError(DevBinException):
    """Raised when a paste does not exist."""

    def __init__(self, paste_id: str):
        super().__init__(
            message=f"Paste with ID '{paste_id}' not found",
            status_code=404,
        )
        self.paste_id = paste_id


class PasteExpiredError(DevBinException):
    """Raised when attempting to access an expired paste."""

    def __init__(self, paste_id: str):
        super().__init__(
            message=f"Paste with ID '{paste_id}' has expired",
            status_code=404,
        )
        self.paste_id = paste_id


class InvalidTokenError(DevBinException):
    """Raised when an invalid or incorrect token is provided."""

    def __init__(self, operation: str = "access"):
        super().__init__(
            message=f"Invalid or incorrect token for {operation}",
            status_code=404,  # Use 404 to avoid leaking information
        )
        self.operation = operation


class UnauthorizedError(DevBinException):
    """Raised when authentication is required but not provided or invalid."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
        )
        self.www_authenticate = "Bearer"  # For WWW-Authenticate header


class StorageError(DevBinException):
    """Raised when storage backend operations fail."""

    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(
            message=f"Storage error during {operation}: {message}",
            status_code=500,
        )
        self.operation = operation


class StorageQuotaExceededError(DevBinException):
    """Raised when storage quota is exceeded."""

    def __init__(self, required_mb: float, available_mb: float):
        super().__init__(
            message=f"Insufficient storage: required {required_mb:.2f}MB, available {available_mb:.2f}MB",
            status_code=507,  # HTTP 507 Insufficient Storage
        )
        self.required_mb = required_mb
        self.available_mb = available_mb


class ContentTooLargeError(DevBinException):
    """Raised when content exceeds maximum allowed size."""

    def __init__(self, content_size: int, max_size: int):
        super().__init__(
            message=f"Content size {content_size} bytes exceeds maximum {max_size} bytes",
            status_code=413,  # HTTP 413 Payload Too Large
        )
        self.content_size = content_size
        self.max_size = max_size


class CompressionError(DevBinException):
    """Raised when compression or decompression fails."""

    def __init__(self, message: str, operation: str = "compression"):
        super().__init__(
            message=f"{operation.capitalize()} error: {message}",
            status_code=500,
        )
        self.operation = operation


class DatabaseError(DevBinException):
    """Raised when database operations fail."""

    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(
            message=f"Database error during {operation}: {message}",
            status_code=500,
        )
        self.operation = operation


class CacheError(DevBinException):
    """Raised when cache operations fail (non-critical)."""

    def __init__(self, message: str, operation: str = "unknown"):
        super().__init__(
            message=f"Cache error during {operation}: {message}",
            status_code=500,
        )
        self.operation = operation


# ─────────────────────────────────────────────────────────────────────────────
# Authentication Exceptions
# ─────────────────────────────────────────────────────────────────────────────


class UserNotFoundError(DevBinException):
    """Raised when a user does not exist."""

    def __init__(self, identifier: str = "user"):
        super().__init__(
            message=f"User '{identifier}' not found",
            status_code=404,
        )
        self.identifier = identifier


class UserAlreadyExistsError(DevBinException):
    """Raised when attempting to create a user that already exists."""

    def __init__(self, field: str = "username or email"):
        super().__init__(
            message=f"User with this {field} already exists",
            status_code=409,
        )
        self.field = field


class EmailNotVerifiedError(DevBinException):
    """Raised when user attempts to login without verified email."""

    def __init__(self):
        super().__init__(
            message="Email address has not been verified",
            status_code=403,
        )


class InvalidCredentialsError(DevBinException):
    """Raised when login credentials are invalid."""

    def __init__(self):
        super().__init__(
            message="Invalid username or password",
            status_code=401,
        )


class TokenExpiredError(DevBinException):
    """Raised when a token has expired."""

    def __init__(self, token_type: str = "token"):
        super().__init__(
            message=f"The {token_type} has expired",
            status_code=401,
        )
        self.token_type = token_type


class InvalidJWTError(DevBinException):
    """Raised when JWT token is invalid or malformed."""

    def __init__(self, reason: str = "Invalid token"):
        super().__init__(
            message=reason,
            status_code=401,
        )
        self.reason = reason


class PasswordValidationError(DevBinException):
    """Raised when password does not meet requirements."""

    def __init__(self, requirements: list[str]):
        message = "Password does not meet requirements: " + ", ".join(requirements)
        super().__init__(
            message=message,
            status_code=400,
        )
        self.requirements = requirements


class UserInactiveError(DevBinException):
    """Raised when user account is deactivated."""

    def __init__(self):
        super().__init__(
            message="User account is inactive",
            status_code=403,
        )
