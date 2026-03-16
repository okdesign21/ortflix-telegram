"""Pydantic models for Ortflix Telegram Bot."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MediaInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    media_type: Optional[str] = Field(None, alias="media_type")
    tmdb_id: Optional[int] = Field(None, alias="tmdbId")
    tvdb_id: Optional[int] = Field(None, alias="tvdbId")
    status: Optional[str] = None
    status_4k: Optional[str] = Field(None, alias="status4k")


class RequestInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: Optional[str] = Field(None, alias="request_id")
    requested_by_username: Optional[str] = Field("Someone", alias="requestedBy_username")
    requested_by_email: Optional[str] = Field(None, alias="requestedBy_email")
    requested_by_avatar: Optional[str] = Field(None, alias="requestedBy_avatar")


class OverseerrWebhook(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    notification_type: str
    event: Optional[str] = None
    subject: Optional[str] = "Unknown title"
    message: Optional[str] = None
    image: Optional[str] = None
    media: Optional[MediaInfo] = None
    request: Optional[RequestInfo] = None


class CorruptedFileInfo(BaseModel):
    path: str
    size: str
    error: str


class MediaIntegrityWebhook(BaseModel):
    notification_type: str
    summary_message: Optional[str] = "Media integrity check alert"
    count: int = 0
    files: list[CorruptedFileInfo] = Field(default_factory=list)
