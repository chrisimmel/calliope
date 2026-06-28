"""Durable media storage + the persist fallback in the task layer."""

from unittest.mock import AsyncMock

from sqlalchemy import select

from calliope2.api.v3 import tasks as task_mod
from calliope2.db.models import Image, Video
from calliope2.inference import ImageBlob, VideoBlob
from calliope2.storage.media_store import persist_media


async def test_persist_media_returns_none_without_bucket():
    # No CALLIOPE2_GCS_BUCKET configured in tests → fail-safe None, no raise.
    assert await persist_media(data=b"x", url=None, kind="image", fmt="png") is None
    assert await persist_media(data=None, url="https://x/y.png", kind="image", fmt="png") is None


async def test_persist_image_falls_back_to_provider_url(db_sessionmaker, monkeypatch):
    # Storage unconfigured → keep the provider URL (today's behavior).
    monkeypatch.setattr(task_mod, "persist_media", AsyncMock(return_value=None))
    async with db_sessionmaker() as s:
        img_id = await task_mod._persist_image(
            s, ImageBlob(url="https://replicate.delivery/x.png", format="png")
        )
        await s.commit()
    async with db_sessionmaker() as s:
        row = (await s.execute(select(Image).where(Image.id == img_id))).scalar_one()
        assert row.gcs_uri == "https://replicate.delivery/x.png"


async def test_persist_image_uses_durable_uri_when_stored(db_sessionmaker, monkeypatch):
    monkeypatch.setattr(
        task_mod,
        "persist_media",
        AsyncMock(return_value="gs://bucket/media/v3/abc.png"),
    )
    async with db_sessionmaker() as s:
        img_id = await task_mod._persist_image(
            s, ImageBlob(url="https://replicate.delivery/expires.png", format="png")
        )
        await s.commit()
    async with db_sessionmaker() as s:
        row = (await s.execute(select(Image).where(Image.id == img_id))).scalar_one()
        assert row.gcs_uri == "gs://bucket/media/v3/abc.png"


async def test_persist_video_uses_durable_uri_when_stored(db_sessionmaker, monkeypatch):
    monkeypatch.setattr(
        task_mod,
        "persist_media",
        AsyncMock(return_value="gs://bucket/media/v3/clip.mp4"),
    )
    async with db_sessionmaker() as s:
        vid_id = await task_mod._persist_video(
            s, VideoBlob(url="https://replicate.delivery/v.mp4", format="mp4")
        )
        await s.commit()
    async with db_sessionmaker() as s:
        row = (await s.execute(select(Video).where(Video.id == vid_id))).scalar_one()
        assert row.gcs_uri == "gs://bucket/media/v3/clip.mp4"
