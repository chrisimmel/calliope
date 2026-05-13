"""Generic admin list/get for the reduced model surface.

Replaces Piccolo Admin's read paths for ``User``, ``StoryFrame``, ``Image``,
``Video``, ``Bookmark``. Writes (PATCH/DELETE) are deferred — the Phase 8
goal is the visibility piece (Thoth + Piccolo Admin browse); mutation
endpoints can be layered on once the UI calls for them.

(Story list/detail lives in a sibling router because it joins with User
for owner_email and eager-loads frames.)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from calliope2.api.v3.admin.schemas import (
    AdminBookmarkOut,
    AdminFrameOut,
    AdminImageOut,
    AdminUserOut,
    AdminVideoOut,
    PageMeta,
    PaginatedBookmarksOut,
    PaginatedFramesOut,
    PaginatedImagesOut,
    PaginatedUsersOut,
    PaginatedVideosOut,
)
from calliope2.auth.dependencies import AdminUser, SessionDep
from calliope2.db.models import Bookmark, Image, StoryFrame, User, Video

router = APIRouter(prefix="/v3/admin", tags=["admin"])


def _cursor_clause(model, cursor: int | None):
    return [] if cursor is None else [model.id < cursor]


# ----- Users -----


@router.get("/users", response_model=PaginatedUsersOut)
async def list_users(
    user: AdminUser,
    session: SessionDep,
    cursor: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> PaginatedUsersOut:
    stmt = (
        select(User)
        .where(*_cursor_clause(User, cursor))
        .order_by(User.id.desc())
        .limit(limit + 1)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    items = [AdminUserOut.model_validate(u) for u in rows[:limit]]
    total = await session.scalar(select(func.count()).select_from(User))
    return PaginatedUsersOut(
        items=items,
        page=PageMeta(next_cursor=items[-1].id if (has_more and items) else None, total=total),
    )


@router.get("/users/{user_id}", response_model=AdminUserOut)
async def get_user(user_id: int, user: AdminUser, session: SessionDep) -> AdminUserOut:
    row = await session.get(User, user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return AdminUserOut.model_validate(row)


# ----- Frames -----


@router.get("/frames", response_model=PaginatedFramesOut)
async def list_frames(
    user: AdminUser,
    session: SessionDep,
    cursor: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    story_id: int | None = Query(None),
) -> PaginatedFramesOut:
    stmt = (
        select(StoryFrame)
        .where(*_cursor_clause(StoryFrame, cursor))
        .order_by(StoryFrame.id.desc())
        .limit(limit + 1)
    )
    if story_id is not None:
        stmt = stmt.where(StoryFrame.story_id == story_id)
    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    items = [_frame_to_out(f) for f in rows[:limit]]
    total = await session.scalar(select(func.count()).select_from(StoryFrame))
    return PaginatedFramesOut(
        items=items,
        page=PageMeta(next_cursor=items[-1].id if (has_more and items) else None, total=total),
    )


# ----- Images -----


@router.get("/images", response_model=PaginatedImagesOut)
async def list_images(
    user: AdminUser,
    session: SessionDep,
    cursor: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> PaginatedImagesOut:
    stmt = (
        select(Image)
        .where(*_cursor_clause(Image, cursor))
        .order_by(Image.id.desc())
        .limit(limit + 1)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    items = [AdminImageOut.model_validate(i) for i in rows[:limit]]
    total = await session.scalar(select(func.count()).select_from(Image))
    return PaginatedImagesOut(
        items=items,
        page=PageMeta(next_cursor=items[-1].id if (has_more and items) else None, total=total),
    )


# ----- Videos -----


@router.get("/videos", response_model=PaginatedVideosOut)
async def list_videos(
    user: AdminUser,
    session: SessionDep,
    cursor: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> PaginatedVideosOut:
    stmt = (
        select(Video)
        .where(*_cursor_clause(Video, cursor))
        .order_by(Video.id.desc())
        .limit(limit + 1)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    items = [AdminVideoOut.model_validate(v) for v in rows[:limit]]
    total = await session.scalar(select(func.count()).select_from(Video))
    return PaginatedVideosOut(
        items=items,
        page=PageMeta(next_cursor=items[-1].id if (has_more and items) else None, total=total),
    )


# ----- Bookmarks -----


@router.get("/bookmarks", response_model=PaginatedBookmarksOut)
async def list_bookmarks(
    user: AdminUser,
    session: SessionDep,
    cursor: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> PaginatedBookmarksOut:
    stmt = (
        select(Bookmark)
        .where(*_cursor_clause(Bookmark, cursor))
        .order_by(Bookmark.id.desc())
        .limit(limit + 1)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    items = [AdminBookmarkOut.model_validate(b) for b in rows[:limit]]
    total = await session.scalar(select(func.count()).select_from(Bookmark))
    return PaginatedBookmarksOut(
        items=items,
        page=PageMeta(next_cursor=items[-1].id if (has_more and items) else None, total=total),
    )


def _frame_to_out(frame: StoryFrame) -> AdminFrameOut:
    return AdminFrameOut(
        id=frame.id,
        story_id=frame.story_id,
        number=frame.number,
        text=frame.text,
        image_url=None,  # lazy-load: list view doesn't expand media relations
        video_url=None,
        source_image_url=None,
        has_embedding=frame.embedding is not None,
        created_at=frame.created_at,
    )
