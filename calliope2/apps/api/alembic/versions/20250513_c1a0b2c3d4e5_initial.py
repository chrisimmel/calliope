"""initial

Revision ID: c1a0b2c3d4e5
Revises:
Create Date: 2025-05-13 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1a0b2c3d4e5"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("firebase_uid", sa.String(128), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("display_name", sa.String(256), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("firebase_uid", name=op.f("uq_users_firebase_uid")),
    )
    op.create_index(op.f("ix_users_firebase_uid"), "users", ["firebase_uid"])

    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(32), nullable=True),
        sa.Column("gcs_uri", sa.String(1024), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_images")),
    )
    op.create_index(op.f("ix_images_content_hash"), "images", ["content_hash"])

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(32), nullable=True),
        sa.Column("gcs_uri", sa.String(1024), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("frame_rate", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_videos")),
    )

    op.create_table(
        "stories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(256), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("thumbnail_image_id", sa.Integer(), nullable=True),
        sa.Column("storyteller_name", sa.String(128), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_stories_owner_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["thumbnail_image_id"],
            ["images.id"],
            name=op.f("fk_stories_thumbnail_image_id_images"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stories")),
        sa.UniqueConstraint("slug", name=op.f("uq_stories_slug")),
    )
    op.create_index(op.f("ix_stories_owner_id"), "stories", ["owner_id"])
    op.create_index(op.f("ix_stories_slug"), "stories", ["slug"])

    op.create_table(
        "story_frames",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("story_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("image_id", sa.Integer(), nullable=True),
        sa.Column("video_id", sa.Integer(), nullable=True),
        sa.Column("source_image_id", sa.Integer(), nullable=True),
        sa.Column("min_duration_seconds", sa.Float(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            name=op.f("fk_story_frames_story_id_stories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["image_id"],
            ["images.id"],
            name=op.f("fk_story_frames_image_id_images"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
            name=op.f("fk_story_frames_video_id_videos"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_image_id"],
            ["images.id"],
            name=op.f("fk_story_frames_source_image_id_images"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_story_frames")),
    )
    op.create_index(op.f("ix_story_frames_story_id"), "story_frames", ["story_id"])

    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("story_id", sa.Integer(), nullable=False),
        sa.Column("frame_id", sa.Integer(), nullable=True),
        sa.Column("list_name", sa.String(256), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_bookmarks_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            name=op.f("fk_bookmarks_story_id_stories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["frame_id"],
            ["story_frames.id"],
            name=op.f("fk_bookmarks_frame_id_story_frames"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bookmarks")),
    )
    op.create_index(op.f("ix_bookmarks_owner_id"), "bookmarks", ["owner_id"])
    op.create_index(op.f("ix_bookmarks_story_id"), "bookmarks", ["story_id"])


def downgrade() -> None:
    op.drop_table("bookmarks")
    op.drop_table("story_frames")
    op.drop_table("stories")
    op.drop_table("videos")
    op.drop_table("images")
    op.drop_table("users")
