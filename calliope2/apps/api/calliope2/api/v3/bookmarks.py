"""/v3/bookmarks endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select

from calliope2.api.v3.schemas import BookmarkCreateRequest, BookmarkOut
from calliope2.auth.dependencies import CurrentUser, SessionDep
from calliope2.db.models import Bookmark, Story, StoryFrame

router = APIRouter(prefix="/v3/bookmarks", tags=["bookmarks"])


@router.post("", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    body: BookmarkCreateRequest,
    user: CurrentUser,
    session: SessionDep,
) -> BookmarkOut:
    story = await session.scalar(
        select(Story).where(Story.id == body.story_id, Story.owner_id == user.id)
    )
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="story not found")

    if body.frame_id is not None:
        frame = await session.scalar(
            select(StoryFrame).where(
                StoryFrame.id == body.frame_id, StoryFrame.story_id == body.story_id
            )
        )
        if frame is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="frame not found in this story",
            )

    bm = Bookmark(
        owner_id=user.id,
        story_id=body.story_id,
        frame_id=body.frame_id,
        list_name=body.list_name,
        comments=body.comments,
        is_public=body.is_public,
    )
    session.add(bm)
    await session.commit()
    await session.refresh(bm)
    return BookmarkOut.model_validate(bm)


@router.get("", response_model=list[BookmarkOut])
async def list_bookmarks(user: CurrentUser, session: SessionDep) -> list[BookmarkOut]:
    stmt = (
        select(Bookmark)
        .where(Bookmark.owner_id == user.id)
        .order_by(Bookmark.created_at.desc())
    )
    result = await session.execute(stmt)
    return [BookmarkOut.model_validate(b) for b in result.scalars().all()]


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(bookmark_id: int, user: CurrentUser, session: SessionDep) -> None:
    result = await session.execute(
        delete(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.owner_id == user.id)
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="bookmark not found")
