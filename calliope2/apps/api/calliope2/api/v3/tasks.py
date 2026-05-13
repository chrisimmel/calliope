"""Background task layer: run a storyteller and persist the resulting frame.

This module owns the *content* of the work that's enqueued via
``BackgroundTasks`` from the routers. It opens its own DB session (the
request session is already closed by the time this runs), invokes the
storyteller, and writes any produced Image/Video rows + StoryFrame.

Realtime status writes (Firestore) are stubbed here and wired up in
Phase 5. GCS upload of generated-bytes images is wired up in the storage
phase; for now, `ImageBlob.url` (a remote URL) is persisted verbatim
and `ImageBlob.data` (raw bytes) is logged as a TODO and skipped.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from calliope2.db.models import Image, Story, StoryFrame, Video
from calliope2.db.session import sessionmaker_for
from calliope2.inference import ImageBlob
from calliope2.storytellers import FrameOutput, run_storyteller

logger = logging.getLogger(__name__)


def new_task_id() -> str:
    return str(uuid.uuid4())


async def generate_first_frame(
    task_id: str, story_id: int, storyteller_name: str, inputs: dict[str, Any]
) -> None:
    logger.info(
        "task %s: generating first frame for story %s (storyteller=%s)",
        task_id, story_id, storyteller_name,
    )
    try:
        output = await run_storyteller(storyteller_name, _prepare_inputs(inputs))
        await _persist_frame(story_id, frame_number=1, output=output)
        logger.info("task %s: complete", task_id)
    except Exception:
        logger.exception("task %s: failed", task_id)
        raise


async def generate_next_frame(
    task_id: str, story_id: int, inputs: dict[str, Any]
) -> None:
    """Continue a story: load the latest frame, thread previous_text/previous_image, persist a new frame."""
    logger.info("task %s: generating next frame for story %s", task_id, story_id)
    Session = sessionmaker_for()
    async with Session() as session:
        story = await _load_story_with_frames(session, story_id)
        if story is None:
            logger.error("task %s: story %s vanished", task_id, story_id)
            return
        last_frame = max(story.frames, key=lambda f: f.number) if story.frames else None
        next_number = (last_frame.number + 1) if last_frame else 1
        threaded = _prepare_inputs(inputs) | _previous_frame_inputs(last_frame)
        storyteller_name = story.storyteller_name

    if not storyteller_name:
        logger.error("task %s: story %s has no storyteller_name", task_id, story_id)
        return

    try:
        output = await run_storyteller(storyteller_name, threaded)
        await _persist_frame(story_id, frame_number=next_number, output=output)
        logger.info("task %s: complete", task_id)
    except Exception:
        logger.exception("task %s: failed", task_id)
        raise


def _prepare_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Coerce caller-supplied API inputs into storyteller-ready shapes.

    Today: ``source_image_url`` (str) → ``source_image`` (ImageBlob). Extend
    here when richer input types arrive (uploaded blobs, multi-image refs).
    """
    prepared = dict(inputs)
    if "source_image_url" in prepared:
        prepared["source_image"] = ImageBlob(url=prepared.pop("source_image_url"))
    return prepared


def _previous_frame_inputs(frame: StoryFrame | None) -> dict[str, Any]:
    if frame is None:
        return {"previous_text": "", "previous_image": None}
    previous_image: ImageBlob | None = None
    if frame.image is not None:
        previous_image = ImageBlob(url=frame.image.gcs_uri)
    return {"previous_text": frame.text or "", "previous_image": previous_image}


async def _load_story_with_frames(session, story_id: int) -> Story | None:
    stmt = (
        select(Story)
        .where(Story.id == story_id)
        .options(selectinload(Story.frames).selectinload(StoryFrame.image))
    )
    return await session.scalar(stmt)


async def _persist_frame(
    story_id: int, frame_number: int, output: FrameOutput
) -> StoryFrame:
    Session = sessionmaker_for()
    async with Session() as session:
        image_id = await _persist_image(session, output.image) if output.image else None
        video_id = await _persist_video(session, output.video) if output.video else None
        frame = StoryFrame(
            story_id=story_id,
            number=frame_number,
            text=output.text,
            image_id=image_id,
            video_id=video_id,
        )
        session.add(frame)
        await session.commit()
        await session.refresh(frame)
        return frame


async def _persist_image(session, blob: ImageBlob) -> int | None:
    if blob.url is None:
        # TODO(phase-storage): upload blob.data to GCS, get back a URI.
        logger.warning("generated image has bytes-only payload; skipping persistence")
        return None
    row = Image(gcs_uri=blob.url, width=blob.width, height=blob.height, format=blob.format)
    session.add(row)
    await session.flush()
    return row.id


async def _persist_video(session, blob) -> int | None:
    if blob.url is None:
        logger.warning("generated video has bytes-only payload; skipping persistence")
        return None
    row = Video(
        gcs_uri=blob.url,
        width=blob.width,
        height=blob.height,
        format=blob.format,
        duration_seconds=blob.duration_seconds,
        frame_rate=blob.frame_rate,
    )
    session.add(row)
    await session.flush()
    return row.id
