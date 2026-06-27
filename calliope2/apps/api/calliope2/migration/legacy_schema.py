"""SQLAlchemy Core ``Table`` definitions for the legacy Piccolo schema.

Used **read-only** by the data migration. Hand-written rather than reflected
because reflection requires a live DB to introspect (we want offline testing
against SQLite in-memory). The shape matches ``/calliope/tables/*.py`` as of
the cutover.

Columns are typed permissively — the migration reads, never writes via these
tables — and uses ``JSON`` rather than ``JSONB`` so SQLite test backends work
alongside Postgres production.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

legacy_metadata = MetaData()

LegacySparrowState = Table(
    "sparrowstate",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("sparrow_id", String(256), unique=True, index=True, nullable=False),
    Column("date_created", DateTime(timezone=True)),
    Column("date_updated", DateTime(timezone=True)),
)

LegacyImage = Table(
    "image",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("url", String(2048), nullable=False),
    Column("width", Integer),
    Column("height", Integer),
    Column("format", String(50)),
    Column("date_created", DateTime(timezone=True)),
    Column("date_updated", DateTime(timezone=True)),
)

LegacyVideo = Table(
    "video",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("url", String(2048), nullable=False),
    Column("width", Integer),
    Column("height", Integer),
    Column("format", String(50)),
    Column("duration_seconds", Float),
    Column("frame_rate", Float),
    Column("date_created", DateTime(timezone=True)),
    Column("date_updated", DateTime(timezone=True)),
)

LegacyStory = Table(
    "story",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("cuid", String(64), unique=True),
    Column("title", Text),
    Column("slug", String(256)),
    Column("strategy_name", String(128)),
    Column("created_for_sparrow_id", String(256)),
    Column("thumbnail_image", Integer, ForeignKey("image.id")),
    Column("state_props", JSON),
    Column("date_created", DateTime(timezone=True)),
    Column("date_updated", DateTime(timezone=True)),
)

LegacyStoryFrame = Table(
    "storyframe",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("story", Integer, ForeignKey("story.id")),
    Column("number", Integer),
    Column("text", Text),
    Column("image", Integer, ForeignKey("image.id")),
    Column("video", Integer, ForeignKey("video.id")),
    Column("source_image", Integer, ForeignKey("image.id")),
    Column("min_duration_seconds", Integer),
    Column("trigger_condition", JSON),
    Column("metadata", JSON),
    Column("indexed_for_search", Boolean),
    Column("date_created", DateTime(timezone=True)),
    Column("date_updated", DateTime(timezone=True)),
)

LegacyBookmarkList = Table(
    "bookmarklist",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(256), nullable=False),
    Column("descriiption", Text),  # legacy typo, preserved
    Column("sparrow", Integer, ForeignKey("sparrowstate.id")),
    Column("is_public", Boolean),
    Column("date_created", DateTime(timezone=True)),
    Column("date_updated", DateTime(timezone=True)),
)

LegacyStoryBookmark = Table(
    "storybookmark",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("story", Integer, ForeignKey("story.id")),
    Column("sparrow", Integer, ForeignKey("sparrowstate.id")),
    Column("list", Integer, ForeignKey("bookmarklist.id")),
    Column("comments", Text),
    Column("date_created", DateTime(timezone=True)),
    Column("date_updated", DateTime(timezone=True)),
)

LegacyStoryFrameBookmark = Table(
    "storyframebookmark",
    legacy_metadata,
    Column("id", Integer, primary_key=True),
    Column("frame", Integer, ForeignKey("storyframe.id")),
    Column("sparrow", Integer, ForeignKey("sparrowstate.id")),
    Column("comments", Text),
    Column("date_created", DateTime(timezone=True)),
    Column("date_updated", DateTime(timezone=True)),
)
