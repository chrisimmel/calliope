"""pgvector — extension, embedding column, HNSW index

Revision ID: f2e3d4c5b6a7
Revises: c1a0b2c3d4e5
Create Date: 2025-05-13 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "f2e3d4c5b6a7"
down_revision: Union[str, None] = "c1a0b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "story_frames",
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
    )
    op.create_index(
        "ix_story_frames_embedding",
        "story_frames",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_story_frames_embedding", table_name="story_frames")
    op.drop_column("story_frames", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
