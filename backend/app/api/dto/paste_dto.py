from datetime import UTC, datetime
from enum import Enum

from pydantic import UUID4, BaseModel, Field, field_validator

from app.config import config


class _Unset(BaseModel):
    pass


UNSET = _Unset()


class PasteContentLanguage(str, Enum):
    plain_text = "plain_text"


class CreatePaste(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
        description="The title of the paste",
    )
    content: str = Field(
        min_length=1,
        max_length=config.MAX_CONTENT_LENGTH,
        description="The content of the paste",
    )
    content_language: PasteContentLanguage = Field(
        description="The language of the content",
        default=PasteContentLanguage.plain_text,
        examples=[PasteContentLanguage.plain_text],
    )
    expires_at: datetime | None = Field(
        None,
        description="The datetime the Paste should expire (None = Never) Note: No guarantee given!",
    )

    @field_validator("expires_at")
    def validate_expires_at(cls, v):
        if v is not None:
            # Ensure timezone-aware datetime
            v = v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)
            # Compare with timezone-aware current time
            now = datetime.now(UTC)
            if v < now:
                raise ValueError("expires_in must be in the future")
        return v


class EditPaste(BaseModel):
    title: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="The title of the paste",
    )
    content: str | None = Field(
        None,
        min_length=1,
        max_length=config.MAX_CONTENT_LENGTH,
        description="The content of the paste",
    )
    content_language: PasteContentLanguage | None = Field(
        None,
        description="The language of the content",
        examples=[PasteContentLanguage.plain_text],
    )
    expires_at: datetime | None | _Unset = Field(
        default=UNSET,
        description="The expiration datetime. Explicitly set to null to remove expiration.",
    )

    def is_expires_at_set(self) -> bool:
        """Check if expires_at was explicitly provided (including None)."""
        return not isinstance(self.expires_at, _Unset)


class PasteResponse(BaseModel):
    id: UUID4 = Field(
        description="The unique identifier of the paste",
    )
    title: str = Field(
        description="The title of the paste",
    )
    content: str | None = Field(
        description="The content of the paste, possible null if the content couldnt be read.",
    )
    content_language: PasteContentLanguage = Field(
        description="The language of the content",
    )
    expires_at: datetime | None = Field(
        None,
        description="The number of hours until the paste expires (0 = never) Note: No guarantee given!",
    )
    created_at: datetime = Field(
        description="The creation timestamp of the paste",
    )
    last_updated_at: datetime | None = Field(
        description="The last time the paste was updated (null = never)",
    )


class CreatePasteResponse(PasteResponse):
    edit_token: str = Field(
        description="The token to edit the paste",
    )

    delete_token: str = Field(
        description="The token to delete the paste",
    )


class LegacyPasteResponse(BaseModel):
    content: str | None = Field(
        description="The content of the legacy paste, possible null if the content couldnt be read.",
    )
