from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class PasteContentLanguage(str, Enum):
    plain_text = "Plain Text"


class PasteCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
        description="The title of the paste",
    )
    content: str = Field(
        min_length=1,
        max_length=10000,
        description="The content of the paste",
    )
    content_language: PasteContentLanguage = Field(
        description="The language of the content",
        default=PasteContentLanguage.plain_text
    )
    expires_at: datetime | None = Field(None,
                                        description="The datetime the Paste should expire (None = Never) Note: No guarantee given!")

    @field_validator('expires_at')
    def validate_expires_in(cls, v):
        if v is not None and v <= datetime.now():
            raise ValueError('expires_in must be in the future')
        return v


class PasteResponse(BaseModel):
    id: str = Field(
        description="The unique identifier of the paste",
    )
    title: str = Field(
        description="The title of the paste",
    )
    content_url: str = Field(
        description="The url to the content of the paste",
    )
    expires_at: datetime | None = Field(None,
                                        description="The number of hours until the paste expires (0 = never) Note: No guarantee given!")
    created_at: datetime = Field(
        description="The creation timestamp of the paste",
    )
