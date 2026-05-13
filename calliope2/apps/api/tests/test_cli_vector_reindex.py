"""Test the reindex command end-to-end against the in-memory DB."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from calliope2.db.models import Story, StoryFrame, User
from calliope2_cli.commands.vector import _reindex


@pytest.fixture
async def session_and_data(db_sessionmaker):
    """Seed three frames: one with text+no-embedding, one with no text, one already embedded."""
    async with db_sessionmaker() as s:
        u = User(firebase_uid="x")
        s.add(u)
        await s.flush()
        story = Story(owner_id=u.id, storyteller_name="literal")
        s.add(story)
        await s.flush()
        s.add_all(
            [
                StoryFrame(story_id=story.id, number=1, text="frame one"),
                StoryFrame(story_id=story.id, number=2, text=None),
                StoryFrame(
                    story_id=story.id, number=3, text="already done",
                    embedding=[0.5] * 1536,
                ),
            ]
        )
        await s.commit()
    return db_sessionmaker


@pytest.fixture(autouse=True)
def _bind_sessionmaker(monkeypatch, db_sessionmaker):
    """Point the CLI at the test sessionmaker instead of production settings."""
    monkeypatch.setattr(
        "calliope2_cli.commands.vector.sessionmaker_for", lambda: db_sessionmaker
    )


@pytest.fixture(autouse=True)
def _stub_embed(monkeypatch):
    monkeypatch.setattr(
        "calliope2_cli.commands.vector.embed_text",
        AsyncMock(return_value=[0.25] * 1536),
    )


async def test_reindex_backfills_only_frames_with_text_and_no_embedding(
    session_and_data, db_sessionmaker
):
    counts = await _reindex(batch_size=10, limit=None, dry_run=False)
    assert counts == {"candidates": 2, "embedded": 1, "skipped_no_text": 1, "failed": 0}

    async with db_sessionmaker() as s:
        rows = (await s.execute(select(StoryFrame).order_by(StoryFrame.number))).scalars().all()
        # Frame 1 newly embedded
        assert rows[0].embedding is not None
        assert len(rows[0].embedding) == 1536
        # Frame 2 still has no embedding (no text to embed)
        assert rows[1].embedding is None
        # Frame 3 unchanged (already had one)
        assert rows[2].embedding[0] == 0.5


async def test_reindex_dry_run_counts_without_writing(session_and_data, db_sessionmaker):
    counts = await _reindex(batch_size=10, limit=None, dry_run=True)
    assert counts["candidates"] == 2
    assert counts["embedded"] == 0

    async with db_sessionmaker() as s:
        frame_one = await s.scalar(
            select(StoryFrame).where(StoryFrame.number == 1)
        )
        assert frame_one.embedding is None


async def test_reindex_records_failures_without_crashing(
    session_and_data, db_sessionmaker, monkeypatch
):
    async def fail(_t):
        raise RuntimeError("provider down")

    monkeypatch.setattr("calliope2_cli.commands.vector.embed_text", fail)
    counts = await _reindex(batch_size=10, limit=None, dry_run=False)
    assert counts["failed"] == 1
    assert counts["embedded"] == 0
