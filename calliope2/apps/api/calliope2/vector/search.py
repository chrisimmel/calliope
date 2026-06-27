"""Cosine-distance search over ``StoryFrame.embedding``.

Uses pgvector's ``cosine_distance`` operator (``<=>``) on the HNSW-indexed
column. Filters to frames owned by the requesting user. Frames without an
embedding (NULL column) are skipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from calliope2.db.models import Image, Story, StoryFrame

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class SearchHit:
    frame_id: int
    story_id: int
    story_title: str | None
    frame_number: int
    frame_text: str | None
    image_url: str | None
    distance: float


async def search_frames(
    session: AsyncSession,
    embedding: Sequence[float],
    *,
    owner_id: int | None = None,
    limit: int = 20,
) -> list[SearchHit]:
    """Cosine-distance search over ``StoryFrame.embedding``.

    When ``owner_id`` is provided, results are restricted to that user. Pass
    ``None`` for admin-wide search.
    """
    distance = StoryFrame.embedding.cosine_distance(list(embedding))
    stmt = (
        select(
            StoryFrame.id,
            StoryFrame.story_id,
            StoryFrame.number,
            StoryFrame.text,
            Story.title,
            Image.gcs_uri,
            distance.label("distance"),
        )
        .join(Story, StoryFrame.story_id == Story.id)
        .outerjoin(Image, StoryFrame.image_id == Image.id)
        .where(StoryFrame.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    if owner_id is not None:
        stmt = stmt.where(Story.owner_id == owner_id)
    rows = (await session.execute(stmt)).all()
    return [
        SearchHit(
            frame_id=row.id,
            story_id=row.story_id,
            story_title=row.title,
            frame_number=row.number,
            frame_text=row.text,
            image_url=row.gcs_uri,
            distance=float(row.distance),
        )
        for row in rows
    ]
