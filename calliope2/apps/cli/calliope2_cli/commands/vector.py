"""``calliope2-cli vector ...`` — pgvector index maintenance."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import typer
from sqlalchemy import select

from calliope2.db.models import StoryFrame
from calliope2.db.session import sessionmaker_for
from calliope2.vector import embed_text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

app = typer.Typer(help="Vector index maintenance.", no_args_is_help=True)


@app.command()
def reindex(
    batch_size: int = typer.Option(50, help="Frames embedded per DB commit."),
    limit: int | None = typer.Option(None, help="Cap total frames processed (debug)."),
    dry_run: bool = typer.Option(False, help="Count candidates without embedding."),
) -> None:
    """Backfill embeddings for story frames where ``embedding IS NULL``."""
    counts = asyncio.run(_reindex(batch_size=batch_size, limit=limit, dry_run=dry_run))
    typer.echo(
        f"candidates={counts['candidates']} embedded={counts['embedded']} "
        f"skipped_no_text={counts['skipped_no_text']} failed={counts['failed']}"
    )


async def _reindex(*, batch_size: int, limit: int | None, dry_run: bool) -> dict[str, int]:
    Session = sessionmaker_for()
    counts = {"candidates": 0, "embedded": 0, "skipped_no_text": 0, "failed": 0}
    async with Session() as session:
        candidates = await _load_candidates(session, limit=limit)
        counts["candidates"] = len(candidates)
        if dry_run:
            return counts

        pending = 0
        for frame in candidates:
            if not frame.text:
                counts["skipped_no_text"] += 1
                continue
            try:
                frame.embedding = await embed_text(frame.text)
                counts["embedded"] += 1
                pending += 1
            except Exception:
                counts["failed"] += 1
                continue
            if pending >= batch_size:
                await session.commit()
                pending = 0
        if pending:
            await session.commit()
    return counts


async def _load_candidates(
    session: AsyncSession, *, limit: int | None
) -> list[StoryFrame]:
    stmt = (
        select(StoryFrame)
        .where(StoryFrame.embedding.is_(None))
        .order_by(StoryFrame.id)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list((await session.execute(stmt)).scalars().all())
