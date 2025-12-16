from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from pydantic import UUID4, BaseModel, Field, field_validator

from app.config import config


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
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            else:
                v = v.astimezone(timezone.utc)
            # Compare with timezone-aware current time
            now = datetime.now(timezone.utc)
            if v < now:
                raise ValueError("expires_in must be in the future")
        return v


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


class LegacyPasteResponse(BaseModel):
    content: str | None = Field(
        description="The content of the legacy paste, possible null if the content couldnt be read.",
    )
