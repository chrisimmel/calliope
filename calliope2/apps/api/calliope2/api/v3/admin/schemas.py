"""Pydantic response schemas for the /v3/admin/* endpoints.

Distinct from the user-facing /v3 schemas because the admin views show
cross-user data: every story/frame row carries owner info so admins can
see whose content is whose.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AdminUserOut(_Out):
    id: int
    firebase_uid: str
    email: str | None = None
    display_name: str | None = None
    is_admin: bool
    created_at: datetime


class AdminStoryOut(_Out):
    id: int
    owner_id: int
    owner_email: str | None = None
    slug: str | None = None
    title: str | None = None
    storyteller_name: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminFrameOut(BaseModel):
    id: int
    story_id: int
    number: int
    text: str | None = None
    image_url: str | None = None
    video_url: str | None = None
    source_image_url: str | None = None
    has_embedding: bool
    created_at: datetime


class AdminStoryDetailOut(AdminStoryOut):
    metadata: dict[str, Any] | None = None
    frames: list[AdminFrameOut] = Field(default_factory=list)


class AdminImageOut(_Out):
    id: int
    gcs_uri: str
    width: int | None = None
    height: int | None = None
    format: str | None = None
    content_hash: str | None = None
    created_at: datetime


class AdminVideoOut(_Out):
    id: int
    gcs_uri: str
    width: int | None = None
    height: int | None = None
    format: str | None = None
    duration_seconds: float | None = None
    frame_rate: float | None = None
    created_at: datetime


class AdminBookmarkOut(_Out):
    id: int
    owner_id: int
    story_id: int
    frame_id: int | None = None
    list_name: str | None = None
    comments: str | None = None
    is_public: bool
    created_at: datetime


class AdminSearchHitOut(BaseModel):
    frame_id: int
    story_id: int
    story_title: str | None = None
    owner_id: int | None = None
    owner_email: str | None = None
    frame_number: int
    frame_text: str | None = None
    image_url: str | None = None
    distance: float


class AdminSearchResponse(BaseModel):
    query: str
    hits: list[AdminSearchHitOut] = Field(default_factory=list)


class PageMeta(BaseModel):
    """Cursor pagination metadata. ``next_cursor`` is the id of the last row in the page."""

    next_cursor: int | None = None
    total: int | None = None


class PaginatedStoriesOut(BaseModel):
    items: list[AdminStoryOut]
    page: PageMeta


class PaginatedUsersOut(BaseModel):
    items: list[AdminUserOut]
    page: PageMeta


class PaginatedFramesOut(BaseModel):
    items: list[AdminFrameOut]
    page: PageMeta


class PaginatedImagesOut(BaseModel):
    items: list[AdminImageOut]
    page: PageMeta


class PaginatedVideosOut(BaseModel):
    items: list[AdminVideoOut]
    page: PageMeta


class PaginatedBookmarksOut(BaseModel):
    items: list[AdminBookmarkOut]
    page: PageMeta
