"""Admin story browse + detail — replaces Thoth's Jinja views with JSON.

The frontend is the new React Admin SPA at ``apps/web/admin/``; these
endpoints return JSON it can render. All routes require ``is_admin=True``.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from calliope2.api.v3.admin.schemas import (
    AdminFrameOut,
    AdminStoryDetailOut,
    AdminStoryOut,
    PageMeta,
    PaginatedStoriesOut,
)
from calliope2.api.v3.media_urls import to_media_url
from calliope2.auth.dependencies import AdminUser, SessionDep
from calliope2.db.models import Story, StoryFrame, User

router = APIRouter(prefix="/v3/admin/stories", tags=["admin"])


@router.get("", response_model=PaginatedStoriesOut)
async def list_stories(
    user: AdminUser,
    session: SessionDep,
    cursor: int | None = Query(None, description="Last id of the previous page"),
    limit: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, description="Substring match on title (case-insensitive)"),
) -> PaginatedStoriesOut:
    stmt = (
        select(Story, User.email.label("owner_email"))
        .join(User, Story.owner_id == User.id)
        .order_by(Story.id.desc())
        .limit(limit + 1)
    )
    if cursor is not None:
        stmt = stmt.where(Story.id < cursor)
    if q:
        stmt = stmt.where(Story.title.ilike(f"%{q}%"))

    rows = (await session.execute(stmt)).all()
    has_more = len(rows) > limit
    page = rows[:limit]
    items = [
        AdminStoryOut(
            id=row[0].id,
            owner_id=row[0].owner_id,
            owner_email=row[1],
            slug=row[0].slug,
            title=row[0].title,
            storyteller_name=row[0].storyteller_name,
            created_at=row[0].created_at,
            updated_at=row[0].updated_at,
        )
        for row in page
    ]
    total = await session.scalar(select(func.count()).select_from(Story))
    return PaginatedStoriesOut(
        items=items,
        page=PageMeta(
            next_cursor=items[-1].id if (has_more and items) else None,
            total=total,
        ),
    )


@router.get("/{story_id}", response_model=AdminStoryDetailOut)
async def get_story(story_id: int, user: AdminUser, session: SessionDep) -> AdminStoryDetailOut:
    stmt = (
        select(Story, User.email.label("owner_email"))
        .join(User, Story.owner_id == User.id)
        .where(Story.id == story_id)
        .options(
            selectinload(Story.frames).selectinload(StoryFrame.image),
            selectinload(Story.frames).selectinload(StoryFrame.video),
            selectinload(Story.frames).selectinload(StoryFrame.source_image),
        )
    )
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="story not found")
    story, owner_email = row
    return AdminStoryDetailOut(
        id=story.id,
        owner_id=story.owner_id,
        owner_email=owner_email,
        slug=story.slug,
        title=story.title,
        storyteller_name=story.storyteller_name,
        metadata=story.metadata_,
        created_at=story.created_at,
        updated_at=story.updated_at,
        frames=[_serialize_frame(f) for f in sorted(story.frames, key=lambda f: f.number)],
    )


def _serialize_frame(frame: StoryFrame) -> AdminFrameOut:
    return AdminFrameOut(
        id=frame.id,
        story_id=frame.story_id,
        number=frame.number,
        text=frame.text,
        image_url=to_media_url(frame.image.gcs_uri) if frame.image is not None else None,
        video_url=to_media_url(frame.video.gcs_uri) if frame.video is not None else None,
        source_image_url=(
            to_media_url(frame.source_image.gcs_uri) if frame.source_image is not None else None
        ),
        has_embedding=frame.embedding is not None,
        created_at=frame.created_at,
    )
