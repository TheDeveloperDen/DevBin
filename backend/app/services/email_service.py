"""Email service for sending authentication emails."""

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import Config


class EmailService:
    """Service for sending authentication-related emails."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def _is_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(self.config.SMTP_HOST and self.config.SMTP_PORT)

    async def _send_email(self, to: str, subject: str, html_content: str) -> bool:
        """
        Send an email using SMTP.

        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML email body

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self._is_configured():
            self.logger.warning(
                "SMTP not configured. Email to %s with subject '%s' not sent. "
                "Set APP_SMTP_HOST and APP_SMTP_PORT to enable email.",
                to,
                subject,
            )
            # In development, log the email content for testing
            if self.config.ENVIRONMENT == "dev":
                self.logger.info("Email content (dev mode):\n%s", html_content)
            return False

        message = EmailMessage()
        message["From"] = (
            f"{self.config.SMTP_FROM_NAME} <{self.config.SMTP_FROM_EMAIL}>"
        )
        message["To"] = to
        message["Subject"] = subject
        message.set_content(html_content, subtype="html")

        try:
            await aiosmtplib.send(
                message,
                hostname=self.config.SMTP_HOST,
                port=self.config.SMTP_PORT,
                username=self.config.SMTP_USERNAME or None,
                password=self.config.SMTP_PASSWORD or None,
                start_tls=self.config.SMTP_USE_TLS,
            )
            self.logger.info("Email sent to %s: %s", to, subject)
            return True

        except aiosmtplib.SMTPException as e:
            self.logger.error("Failed to send email to %s: %s", to, str(e))
            return False

    def _build_verification_url(self, token: str) -> str:
        """Build the email verification URL."""
        base = self.config.FRONTEND_URL.rstrip("/")
        path = self.config.EMAIL_VERIFY_PATH.lstrip("/")
        return f"{base}/{path}?token={token}"

    def _build_password_reset_url(self, token: str) -> str:
        """Build the password reset URL."""
        base = self.config.FRONTEND_URL.rstrip("/")
        path = self.config.PASSWORD_RESET_PATH.lstrip("/")
        return f"{base}/{path}?token={token}"

    async def send_verification_email(self, to: str, username: str, token: str) -> bool:
        """
        Send email verification email.

        Args:
            to: Recipient email address
            username: User's username
            token: Verification token

        Returns:
            True if email was sent successfully
        """
        verification_url = self._build_verification_url(token)

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Verify Your Email - DevBin</title>
</head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #333;">Welcome to DevBin, {username}!</h1>
    <p style="color: #666; font-size: 16px;">
        Thank you for registering. Please verify your email address by clicking the button below:
    </p>
    <p style="text-align: center; margin: 30px 0;">
        <a href="{verification_url}"
           style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
            Verify Email Address
        </a>
    </p>
    <p style="color: #666; font-size: 14px;">
        Or copy and paste this link into your browser:<br>
        <a href="{verification_url}" style="color: #007bff;">{verification_url}</a>
    </p>
    <p style="color: #999; font-size: 12px;">
        This link will expire in {self.config.EMAIL_VERIFICATION_EXPIRE_HOURS} hours.
        If you didn't create an account, you can safely ignore this email.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="color: #999; font-size: 12px;">
        DevBin - Share code snippets easily
    </p>
</body>
</html>
"""

        return await self._send_email(
            to=to,
            subject="Verify Your Email - DevBin",
            html_content=html_content,
        )

    async def send_password_reset_email(
        self, to: str, username: str, token: str
    ) -> bool:
        """
        Send password reset email.

        Args:
            to: Recipient email address
            username: User's username
            token: Password reset token

        Returns:
            True if email was sent successfully
        """
        reset_url = self._build_password_reset_url(token)

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reset Your Password - DevBin</title>
</head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #333;">Password Reset Request</h1>
    <p style="color: #666; font-size: 16px;">
        Hi {username}, we received a request to reset your password.
        Click the button below to create a new password:
    </p>
    <p style="text-align: center; margin: 30px 0;">
        <a href="{reset_url}"
           style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
            Reset Password
        </a>
    </p>
    <p style="color: #666; font-size: 14px;">
        Or copy and paste this link into your browser:<br>
        <a href="{reset_url}" style="color: #007bff;">{reset_url}</a>
    </p>
    <p style="color: #999; font-size: 12px;">
        This link will expire in {self.config.PASSWORD_RESET_EXPIRE_HOURS} hour(s).
        If you didn't request a password reset, you can safely ignore this email.
        Your password will remain unchanged.
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="color: #999; font-size: 12px;">
        DevBin - Share code snippets easily
    </p>
</body>
</html>
"""

        return await self._send_email(
            to=to,
            subject="Reset Your Password - DevBin",
            html_content=html_content,
        )
