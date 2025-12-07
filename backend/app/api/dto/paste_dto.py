from datetime import datetime

from pydantic import BaseModel, Field


class PasteCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
        description="The title of the paste",
    )
    content: str = Field(
        min_length=1,
        description="The content of the paste",
    )
    expires_in_hours: int = Field(0,
                                  ge=0,
                                  le=8760,
                                  description="The number of hours until the paste expires (0 = never) Note: No guarantee given!")


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
