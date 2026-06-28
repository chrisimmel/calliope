"""Background task layer: run a storyteller, persist the frame, and write status.

This module owns the *content* of the work that's enqueued via
``BackgroundTasks`` from the routers. It opens its own DB session (the
request session is already closed by the time this runs), invokes the
storyteller, writes any produced Image/Video rows + StoryFrame, and
emits status updates to the realtime writer (Firestore in prod, logging
in dev).

GCS upload of generated-bytes images is wired up in the storage phase;
for now, `ImageBlob.url` (a remote URL) is persisted verbatim and
`ImageBlob.data` (raw bytes) is logged as a TODO and skipped.
"""

from __future__ import annotations

import base64
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from calliope2.db.models import Image, Story, StoryFrame, Video
from calliope2.db.session import sessionmaker_for
from calliope2.inference import AudioBlob, ImageBlob
from calliope2.realtime import TaskRecord, TaskType, get_task_writer
from calliope2.storytellers import FrameOutput, run_storyteller
from calliope2.vector import try_embed_text

logger = logging.getLogger(__name__)


def new_task_id() -> str:
    return str(uuid.uuid4())


async def generate_first_frame(
    task_id: str,
    story_id: int,
    user_id: int,
    firebase_uid: str,
    storyteller_name: str,
    inputs: dict[str, Any],
    illustrator_override: str | None = None,
) -> None:
    logger.info(
        "task %s: generating first frame for story %s (storyteller=%s, illustrator=%s)",
        task_id,
        story_id,
        storyteller_name,
        illustrator_override,
    )
    writer = get_task_writer()
    record = TaskRecord(
        task_id=task_id,
        user_id=user_id,
        firebase_uid=firebase_uid,
        story_id=story_id,
        type=TaskType.CREATE_STORY,
        started_at=datetime.now(UTC),
    )
    try:
        await writer.started(record)
        output = await run_storyteller(
            storyteller_name,
            _prepare_inputs(inputs),
            illustrator_override=illustrator_override,
        )
        await _persist_frame(story_id, frame_number=1, output=output)
        await writer.completed(task_id)
    except Exception as e:
        logger.exception("task %s: failed", task_id)
        await writer.failed(task_id, str(e))
        raise


async def generate_next_frame(
    task_id: str,
    story_id: int,
    user_id: int,
    firebase_uid: str,
    inputs: dict[str, Any],
    illustrator_override: str | None = None,
) -> None:
    """Continue a story: load the latest frame, thread previous_text/previous_image, persist a new frame."""
    logger.info("task %s: generating next frame for story %s", task_id, story_id)
    writer = get_task_writer()
    record = TaskRecord(
        task_id=task_id,
        user_id=user_id,
        firebase_uid=firebase_uid,
        story_id=story_id,
        type=TaskType.CREATE_FRAME,
        started_at=datetime.now(UTC),
    )
    await writer.started(record)

    Session = sessionmaker_for()
    async with Session() as session:
        story = await _load_story_with_frames(session, story_id)
        if story is None:
            logger.error("task %s: story %s vanished", task_id, story_id)
            await writer.failed(task_id, f"story {story_id} not found")
            return
        last_frame = max(story.frames, key=lambda f: f.number) if story.frames else None
        next_number = (last_frame.number + 1) if last_frame else 1
        threaded = _prepare_inputs(inputs) | _previous_frame_inputs(last_frame)
        storyteller_name = story.storyteller_name

    if not storyteller_name:
        logger.error("task %s: story %s has no storyteller_name", task_id, story_id)
        await writer.failed(task_id, "story has no storyteller_name")
        return

    try:
        output = await run_storyteller(
            storyteller_name, threaded, illustrator_override=illustrator_override
        )
        await _persist_frame(story_id, frame_number=next_number, output=output)
        await writer.completed(task_id)
    except Exception as e:
        logger.exception("task %s: failed", task_id)
        await writer.failed(task_id, str(e))
        raise


def _prepare_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Coerce caller-supplied API inputs into storyteller-ready shapes.

    ``source_image_url`` (str) → ``source_image`` (ImageBlob). The value may be
    a fetchable ``http(s)`` URL **or** a ``data:`` URL — the web client captures
    photos in-browser and submits them as base64 data URLs (parity with v2), so
    a data URL is decoded to bytes here rather than requiring a hosted URL.
    """
    prepared = dict(inputs)
    if "source_image_url" in prepared:
        prepared["source_image"] = _image_blob_from_input(prepared.pop("source_image_url"))
    if "source_audio_url" in prepared:
        prepared["source_audio"] = _audio_blob_from_input(prepared.pop("source_audio_url"))
    return prepared


def _image_blob_from_input(value: str) -> ImageBlob:
    """Build an ImageBlob from a ``data:`` URL (→ bytes) or a plain URL."""
    data, fmt, url = _decode_media_input(value, default_format="png")
    return ImageBlob(data=data, url=url, format=fmt)


def _audio_blob_from_input(value: str) -> AudioBlob:
    """Build an AudioBlob from a ``data:`` URL (→ bytes) or a plain URL. The web
    client's "Spoken words" capture arrives as a base64 ``data:audio/...`` URL."""
    data, fmt, url = _decode_media_input(value, default_format="webm")
    return AudioBlob(data=data, url=url, format=fmt)


def _decode_media_input(
    value: str, *, default_format: str
) -> tuple[bytes | None, str | None, str | None]:
    """Return ``(data, format, url)`` for a media input that is either a
    ``data:<mime>;base64,<payload>`` URL (decoded to bytes) or a plain URL."""
    if value.startswith("data:"):
        header, _, encoded = value.partition(",")
        # header looks like ``data:image/png;base64`` or ``data:audio/webm;base64``.
        # Browser captures are always base64; reject other encodings explicitly
        # rather than silently mis-decoding a non-base64 payload.
        if ";base64" not in header:
            raise ValueError("only base64-encoded data: URLs are supported")
        mime = header[len("data:") :].split(";")[0]
        fmt = (mime.split("/")[-1] if "/" in mime else "") or default_format
        return base64.b64decode(encoded), fmt, None
    return None, None, value


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


async def _persist_frame(story_id: int, frame_number: int, output: FrameOutput) -> StoryFrame:
    embedding = await try_embed_text(output.text) if output.text else None
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
            embedding=embedding,
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
