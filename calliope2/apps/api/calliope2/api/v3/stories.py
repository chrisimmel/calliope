"""/v3/stories endpoints — create, list, fetch, continue."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from calliope2.api.v3.schemas import (
    FrameCreateRequest,
    FrameCreateResponse,
    FrameOut,
    StoryCreateRequest,
    StoryCreateResponse,
    StoryDetailOut,
    StoryOut,
)
from calliope2.api.v3.tasks import generate_first_frame, generate_next_frame, new_task_id
from calliope2.auth.dependencies import CurrentUser, SessionDep
from calliope2.db.models import Story, StoryFrame
from calliope2.storytellers import list_storytellers

router = APIRouter(prefix="/v3/stories", tags=["stories"])


@router.post("", response_model=StoryCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_story(
    body: StoryCreateRequest,
    user: CurrentUser,
    session: SessionDep,
    background: BackgroundTasks,
) -> StoryCreateResponse:
    if body.storyteller not in list_storytellers():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown storyteller {body.storyteller!r}",
        )
    story = Story(
        owner_id=user.id,
        title=body.title,
        storyteller_name=body.storyteller,
    )
    session.add(story)
    await session.commit()
    await session.refresh(story)

    task_id = new_task_id()
    background.add_task(
        generate_first_frame, task_id, story.id, user.id, body.storyteller, body.inputs
    )
    return StoryCreateResponse(story_id=story.id, task_id=task_id)


@router.get("", response_model=list[StoryOut])
async def list_stories(user: CurrentUser, session: SessionDep) -> list[StoryOut]:
    stmt = (
        select(Story)
        .where(Story.owner_id == user.id)
        .order_by(Story.created_at.desc())
    )
    result = await session.execute(stmt)
    return [StoryOut.model_validate(s) for s in result.scalars().all()]


@router.get("/{story_id}", response_model=StoryDetailOut)
async def get_story(story_id: int, user: CurrentUser, session: SessionDep) -> StoryDetailOut:
    stmt = (
        select(Story)
        .where(Story.id == story_id, Story.owner_id == user.id)
        .options(
            selectinload(Story.frames).selectinload(StoryFrame.image),
            selectinload(Story.frames).selectinload(StoryFrame.video),
        )
    )
    story = await session.scalar(stmt)
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="story not found")

    return StoryDetailOut(
        id=story.id,
        slug=story.slug,
        title=story.title,
        storyteller_name=story.storyteller_name,
        created_at=story.created_at,
        updated_at=story.updated_at,
        frames=[_serialize_frame(f) for f in sorted(story.frames, key=lambda f: f.number)],
    )


@router.post(
    "/{story_id}/frames",
    response_model=FrameCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_frame(
    story_id: int,
    body: FrameCreateRequest,
    user: CurrentUser,
    session: SessionDep,
    background: BackgroundTasks,
) -> FrameCreateResponse:
    story = await session.scalar(
        select(Story).where(Story.id == story_id, Story.owner_id == user.id)
    )
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="story not found")

    task_id = new_task_id()
    background.add_task(generate_next_frame, task_id, story.id, user.id, body.inputs)
    return FrameCreateResponse(task_id=task_id)


def _serialize_frame(frame: StoryFrame) -> FrameOut:
    return FrameOut(
        id=frame.id,
        number=frame.number,
        text=frame.text,
        image_url=frame.image.gcs_uri if frame.image is not None else None,
        video_url=frame.video.gcs_uri if frame.video is not None else None,
        created_at=frame.created_at,
    )
