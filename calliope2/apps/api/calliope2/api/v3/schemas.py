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


class StoryCreateRequest(BaseModel):
    storyteller: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    title: str | None = None


class StoryCreateResponse(BaseModel):
    story_id: int
    task_id: str


class FrameCreateRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)


class FrameCreateResponse(BaseModel):
    task_id: str


class FrameOut(BaseModel):
    id: int
    number: int
    text: str | None = None
    image_url: str | None = None
    video_url: str | None = None
    created_at: datetime


class StoryOut(_Out):
    id: int
    slug: str | None = None
    title: str | None = None
    storyteller_name: str | None = None
    created_at: datetime
    updated_at: datetime


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
