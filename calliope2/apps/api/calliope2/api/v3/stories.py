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
from calliope2.illustrators import Illustrator, UnknownIllustrator
from calliope2.storytellers import Storyteller, UnknownStoryteller

router = APIRouter(prefix="/v3/stories", tags=["stories"])


@router.post("", response_model=StoryCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_story(
    body: StoryCreateRequest,
    user: CurrentUser,
    session: SessionDep,
    background: BackgroundTasks,
) -> StoryCreateResponse:
    try:
        storyteller = Storyteller.load(body.storyteller)
    except UnknownStoryteller:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown storyteller {body.storyteller!r}",
        ) from None

    illustrator_name = _resolve_and_check_illustrator(
        request_illustrator=body.illustrator,
        storyteller=storyteller,
        user=user,
    )

    story = Story(
        owner_id=user.id,
        title=body.title,
        storyteller_name=body.storyteller,
        metadata_={"illustrator": illustrator_name} if illustrator_name else {},
    )
    session.add(story)
    await session.commit()
    await session.refresh(story)

    task_id = new_task_id()
    background.add_task(
        generate_first_frame,
        task_id, story.id, user.id, body.storyteller, body.inputs,
        illustrator_name,
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

    # Resolve illustrator override: per-frame request → story default → storyteller default.
    illustrator_name: str | None = body.illustrator
    if illustrator_name is None:
        illustrator_name = (story.metadata_ or {}).get("illustrator")
    if illustrator_name is not None:
        try:
            ill = Illustrator.load(illustrator_name)
        except UnknownIllustrator:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"unknown illustrator {illustrator_name!r}",
            ) from None
        if ill.experimental and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"illustrator {illustrator_name!r} is experimental (admin only)",
            )

    task_id = new_task_id()
    background.add_task(
        generate_next_frame, task_id, story.id, user.id, body.inputs, illustrator_name,
    )
    return FrameCreateResponse(task_id=task_id)


def _resolve_and_check_illustrator(
    *,
    request_illustrator: str | None,
    storyteller: Storyteller,
    user,
) -> str | None:
    """Determine the illustrator to use for this story and validate it.

    Returns the resolved illustrator name (may be None for storytellers that
    don't use one, e.g. ``literal``). Raises HTTPException on bad input.
    """
    name = request_illustrator or storyteller.illustrator
    if storyteller.uses_illustrator and name is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"storyteller {storyteller.name!r} requires an illustrator: pass "
                f"`illustrator` in the request body or add a default `illustrator:` "
                f"to the YAML"
            ),
        )
    if name is None:
        return None
    try:
        ill = Illustrator.load(name)
    except UnknownIllustrator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown illustrator {name!r}",
        ) from None
    if ill.experimental and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"illustrator {name!r} is experimental (admin only)",
        )
    return name


def _serialize_frame(frame: StoryFrame) -> FrameOut:
    return FrameOut(
        id=frame.id,
        number=frame.number,
        text=frame.text,
        image_url=frame.image.gcs_uri if frame.image is not None else None,
        video_url=frame.video.gcs_uri if frame.video is not None else None,
        created_at=frame.created_at,
    )
