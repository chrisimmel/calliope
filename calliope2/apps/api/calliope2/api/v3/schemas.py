"""Pydantic request and response schemas for /v3 endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Out(BaseModel):
    """Base for response models that read from SQLAlchemy rows."""

    model_config = ConfigDict(from_attributes=True)


class StorytellerOut(BaseModel):
    name: str
    description: str
    illustrator: str | None = None  # default illustrator; may be None
    experimental: bool = False  # hidden from the picker unless ?x=1


class IllustratorOut(BaseModel):
    name: str
    description: str
    outputs: str  # "image" | "video"
    experimental: bool = False


class StoryCreateRequest(BaseModel):
    storyteller: str
    illustrator: str | None = None  # override the storyteller's default
    inputs: dict[str, Any] = Field(default_factory=dict)
    title: str | None = None


class StoryCreateResponse(BaseModel):
    story_id: int
    task_id: str


class FrameCreateRequest(BaseModel):
    illustrator: str | None = None  # override the story's chosen illustrator
    inputs: dict[str, Any] = Field(default_factory=dict)


class FrameCreateResponse(BaseModel):
    task_id: str


class FrameOut(BaseModel):
    id: int
    number: int
    text: str | None = None
    image_url: str | None = None
    video_url: str | None = None
    situation: str | None = None  # from frame metadata; used as image alt text
    created_at: datetime


class StoryOut(_Out):
    id: int
    slug: str | None = None
    title: str | None = None
    storyteller_name: str | None = None
    created_at: datetime
    updated_at: datetime
    # Derived fields for the library/viewer UI.
    frame_count: int = 0
    thumbnail_url: str | None = None
    is_read_only: bool = False  # true when the requester isn't the owner
    is_bookmarked: bool = False  # the requester has bookmarked this story
    # Latest generation status, when known. Usually left None: the client
    # derives live status from the Firestore task docs instead.
    status: str | None = None


class StoryDetailOut(StoryOut):
    frames: list[FrameOut] = Field(default_factory=list)


class BookmarkCreateRequest(BaseModel):
    story_id: int
    frame_id: int | None = None
    list_name: str | None = None
    comments: str | None = None
    is_public: bool = False


class BookmarkOut(_Out):
    id: int
    story_id: int
    frame_id: int | None = None
    list_name: str | None = None
    comments: str | None = None
    is_public: bool
    created_at: datetime


class SearchHitOut(BaseModel):
    frame_id: int
    story_id: int
    story_title: str | None = None
    frame_number: int
    frame_text: str | None = None
    image_url: str | None = None
    distance: float


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHitOut] = Field(default_factory=list)
