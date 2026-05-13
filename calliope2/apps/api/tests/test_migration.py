"""Round-trip migration tests with two in-memory SQLite DBs.

The legacy schema is created from ``legacy_metadata`` and seeded with sample
rows. The new schema comes from the project's ``Base.metadata`` (with the
existing Vector → TEXT / JSONB → JSON compile overrides from conftest). After
``migrate_all`` runs we assert counts on ``MigrationStats`` and verify the
new-side rows look right.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from calliope2.db.models import Bookmark, Image, Story, StoryFrame, User
from calliope2.migration import migrate_all
from calliope2.migration.legacy_schema import (
    LegacyBookmarkList,
    LegacyImage,
    LegacySparrowState,
    LegacyStory,
    LegacyStoryBookmark,
    LegacyStoryFrame,
    LegacyStoryFrameBookmark,
    LegacyVideo,
    legacy_metadata,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


NOW = datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
async def legacy_engine() -> AsyncEngine:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(legacy_metadata.create_all)
    yield engine
    await engine.dispose()


async def _seed_legacy(engine: AsyncEngine) -> None:
    """Two sparrows; two images, one video; two stories; three frames; bookmarks."""
    async with engine.begin() as c:
        await c.execute(
            LegacySparrowState.insert(),
            [
                {"id": 1, "sparrow_id": "alice", "date_created": NOW, "date_updated": NOW},
                {"id": 2, "sparrow_id": "hardware-bob", "date_created": NOW, "date_updated": NOW},
            ],
        )
        await c.execute(
            LegacyImage.insert(),
            [
                {
                    "id": 10, "url": "gs://b/a.png", "width": 1024, "height": 1024,
                    "format": "image/png", "date_created": NOW, "date_updated": NOW,
                },
                {
                    "id": 11, "url": "gs://b/b.png", "width": 512, "height": 512,
                    "format": "image/png", "date_created": NOW, "date_updated": NOW,
                },
            ],
        )
        await c.execute(
            LegacyVideo.insert(),
            [
                {
                    "id": 20, "url": "gs://b/v.mp4", "width": 1280, "height": 720,
                    "format": "video/mp4", "duration_seconds": 4.0, "frame_rate": 24.0,
                    "date_created": NOW, "date_updated": NOW,
                },
            ],
        )
        await c.execute(
            LegacyStory.insert(),
            [
                {
                    "id": 100, "cuid": "abc123", "title": "Alice Story",
                    "slug": "alice-story", "strategy_name": "fern",
                    "created_for_sparrow_id": "alice",
                    "thumbnail_image": 10, "state_props": {"setting": "kitchen"},
                    "date_created": NOW, "date_updated": NOW,
                },
                {
                    "id": 101, "cuid": "def456", "title": "Hardware Story",
                    "slug": "hardware-story", "strategy_name": "literal",
                    "created_for_sparrow_id": "hardware-bob",
                    "thumbnail_image": None, "state_props": None,
                    "date_created": NOW, "date_updated": NOW,
                },
            ],
        )
        await c.execute(
            LegacyStoryFrame.insert(),
            [
                {
                    "id": 200, "story": 100, "number": 0, "text": "Frame zero",
                    "image": 10, "video": None, "source_image": None,
                    "min_duration_seconds": 3, "trigger_condition": None,
                    "metadata": {"k": "v"}, "indexed_for_search": False,
                    "date_created": NOW, "date_updated": NOW,
                },
                {
                    "id": 201, "story": 100, "number": 1, "text": "Frame one",
                    "image": 11, "video": 20, "source_image": 10,
                    "min_duration_seconds": 5, "trigger_condition": None,
                    "metadata": None, "indexed_for_search": True,
                    "date_created": NOW, "date_updated": NOW,
                },
                {
                    "id": 202, "story": 101, "number": 0, "text": "HW frame",
                    "image": None, "video": None, "source_image": None,
                    "min_duration_seconds": 1, "trigger_condition": None,
                    "metadata": None, "indexed_for_search": False,
                    "date_created": NOW, "date_updated": NOW,
                },
            ],
        )
        await c.execute(
            LegacyBookmarkList.insert(),
            [
                {
                    "id": 300, "name": "favorites", "descriiption": "fav stories",
                    "sparrow": 1, "is_public": False,
                    "date_created": NOW, "date_updated": NOW,
                },
            ],
        )
        await c.execute(
            LegacyStoryBookmark.insert(),
            [
                {
                    "id": 400, "story": 100, "sparrow": 1, "list": 300,
                    "comments": "great", "date_created": NOW, "date_updated": NOW,
                },
            ],
        )
        await c.execute(
            LegacyStoryFrameBookmark.insert(),
            [
                {
                    "id": 500, "frame": 201, "sparrow": 1, "comments": "this one",
                    "date_created": NOW, "date_updated": NOW,
                },
            ],
        )


# ----- Full-run round trip -----


async def test_migrate_round_trip(legacy_engine, db_sessionmaker):
    await _seed_legacy(legacy_engine)
    stats = await migrate_all(legacy_engine, db_sessionmaker)

    # Two sparrows → two placeholder users
    assert stats.users_created == 2
    # Two images, one video
    assert stats.images_created == 2
    assert stats.videos_created == 1
    # Two stories — both migrate because each sparrow_id is mapped to a placeholder user
    assert stats.stories_created == 2
    assert stats.stories_skipped_no_owner == 0
    # Three frames
    assert stats.frames_created == 3
    # One story bookmark + one frame bookmark
    assert stats.bookmarks_created == 2

    async with db_sessionmaker() as s:
        users = (await s.execute(select(User))).scalars().all()
        assert {u.firebase_uid for u in users} == {"legacy:alice", "legacy:hardware-bob"}
        assert all(u.display_name in {"alice", "hardware-bob"} for u in users)

        alice = next(u for u in users if u.firebase_uid == "legacy:alice")
        alice_story = await s.scalar(
            select(Story).where(Story.owner_id == alice.id)
        )
        assert alice_story.title == "Alice Story"
        assert alice_story.storyteller_name == "fern"
        # Timestamp preserved through migration (SQLite drops tz info on read,
        # so compare as naive — Postgres in prod preserves the tz).
        assert alice_story.created_at.replace(tzinfo=None) == NOW.replace(tzinfo=None)
        # legacy_id marker preserved for idempotency
        assert alice_story.metadata_["legacy_id"] == 100
        assert alice_story.metadata_["legacy_cuid"] == "abc123"
        assert alice_story.metadata_["state_props"] == {"setting": "kitchen"}

        # Frame FKs resolve to migrated images/videos
        frames = (await s.execute(select(StoryFrame).order_by(StoryFrame.number))).scalars().all()
        f_zero = next(f for f in frames if f.text == "Frame zero")
        assert f_zero.image_id is not None
        f_one = next(f for f in frames if f.text == "Frame one")
        assert f_one.image_id is not None
        assert f_one.video_id is not None
        assert f_one.source_image_id is not None

        # Bookmarks: one story-level (with list_name), one frame-level
        bookmarks = (await s.execute(select(Bookmark))).scalars().all()
        assert len(bookmarks) == 2
        list_bm = next(b for b in bookmarks if b.list_name == "favorites")
        assert list_bm.comments == "great"
        assert list_bm.frame_id is None
        frame_bm = next(b for b in bookmarks if b.list_name is None)
        assert frame_bm.comments == "this one"
        assert frame_bm.frame_id is not None


# ----- Dry run writes nothing -----


async def test_dry_run_counts_without_writing(legacy_engine, db_sessionmaker):
    await _seed_legacy(legacy_engine)
    stats = await migrate_all(legacy_engine, db_sessionmaker, dry_run=True)

    assert stats.users_created == 2
    assert stats.images_created == 2
    assert stats.videos_created == 1
    assert stats.stories_created == 2
    assert stats.frames_created == 3
    assert stats.bookmarks_created == 2

    async with db_sessionmaker() as s:
        assert (await s.scalar(select(User))) is None
        assert (await s.scalar(select(Image))) is None
        assert (await s.scalar(select(Story))) is None


# ----- Idempotency -----


async def test_second_run_skips_existing(legacy_engine, db_sessionmaker):
    await _seed_legacy(legacy_engine)
    await migrate_all(legacy_engine, db_sessionmaker)
    stats = await migrate_all(legacy_engine, db_sessionmaker)

    # All existing rows skipped on second run
    assert stats.users_created == 0
    assert stats.users_skipped_existing == 2
    assert stats.images_created == 0
    assert stats.images_skipped_existing == 2
    assert stats.videos_created == 0
    assert stats.videos_skipped_existing == 1
    assert stats.stories_created == 0
    assert stats.stories_skipped_existing == 2
    assert stats.frames_created == 0
    assert stats.frames_skipped_existing == 3
    assert stats.bookmarks_created == 0
    assert stats.bookmarks_skipped_existing == 2


# ----- sparrow_map overrides placeholder firebase_uids -----


async def test_sparrow_map_attaches_to_real_firebase_uid(legacy_engine, db_sessionmaker):
    await _seed_legacy(legacy_engine)
    sparrow_map = {"alice": "real-firebase-uid-alice"}
    await migrate_all(legacy_engine, db_sessionmaker, sparrow_map=sparrow_map)

    async with db_sessionmaker() as s:
        users = (await s.execute(select(User))).scalars().all()
        fb_uids = {u.firebase_uid for u in users}
        assert fb_uids == {"real-firebase-uid-alice", "legacy:hardware-bob"}


# ----- Limit + read-only verification -----


async def test_limit_caps_stories_considered(legacy_engine, db_sessionmaker):
    await _seed_legacy(legacy_engine)
    stats = await migrate_all(legacy_engine, db_sessionmaker, limit=1)
    assert stats.stories_created == 1
    # Frames whose parent story wasn't migrated are skipped
    assert stats.frames_skipped_orphan_story >= 1


async def test_migration_does_not_write_to_legacy(legacy_engine, db_sessionmaker):
    """After a full run, the legacy tables remain byte-for-byte identical."""
    await _seed_legacy(legacy_engine)

    async with legacy_engine.connect() as c:
        before_stories = (await c.execute(select(LegacyStory))).all()
        before_frames = (await c.execute(select(LegacyStoryFrame))).all()
        before_sparrows = (await c.execute(select(LegacySparrowState))).all()

    await migrate_all(legacy_engine, db_sessionmaker)

    async with legacy_engine.connect() as c:
        after_stories = (await c.execute(select(LegacyStory))).all()
        after_frames = (await c.execute(select(LegacyStoryFrame))).all()
        after_sparrows = (await c.execute(select(LegacySparrowState))).all()

    assert before_stories == after_stories
    assert before_frames == after_frames
    assert before_sparrows == after_sparrows
