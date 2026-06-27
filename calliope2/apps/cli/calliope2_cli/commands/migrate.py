"""``calliope2-cli migrate from-v1`` — one-shot data migration from /calliope/.

**This command is read-only against the legacy DB.** It only issues SELECT
statements. Configure the legacy DB user with read-only grants in production
as defense in depth.

Idempotent: re-running picks up where it left off (legacy IDs are stored in
``metadata->>'legacy_id'`` on new rows; URLs dedupe images/videos).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from calliope2.db.session import sessionmaker_for
from calliope2.migration import migrate_all

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

app = typer.Typer(help="Data migration from the legacy Piccolo DB.", no_args_is_help=True)


@app.command(name="from-v1")
def from_v1(
    source_url: str = typer.Option(
        ...,
        "--source-url",
        envvar="CALLIOPE2_LEGACY_DATABASE_URL",
        help=(
            "Legacy Postgres URL (postgresql+asyncpg://USER:PASS@HOST/DB). "
            "Use a read-only DB role."
        ),
    ),
    dry_run: bool = typer.Option(
        False, help="Read everything, report counts, write nothing."
    ),
    limit: int | None = typer.Option(
        None, help="Cap legacy stories considered (debug / staged runs)."
    ),
    sparrow_map_file: Path | None = typer.Option(
        None,
        "--sparrow-map",
        help=(
            "Optional JSON file mapping legacy sparrow_id → firebase_uid. "
            "Sparrows not in the map become placeholder users with "
            "firebase_uid='legacy:<sparrow_id>'."
        ),
    ),
    user_prefix: str = typer.Option(
        "legacy:",
        help="Prefix for placeholder firebase_uid values for unmapped sparrows.",
    ),
) -> None:
    """Migrate sparrows → users, images, videos, stories, frames, bookmarks.

    Run order is enforced; each phase is independently idempotent.
    """
    sparrow_map = None
    if sparrow_map_file is not None:
        sparrow_map = json.loads(sparrow_map_file.read_text())

    stats = asyncio.run(
        _run(
            source_url=source_url,
            dry_run=dry_run,
            limit=limit,
            sparrow_map=sparrow_map,
            user_prefix=user_prefix,
        )
    )
    mode = "DRY RUN" if dry_run else "APPLIED"
    typer.echo(f"=== {mode} ===")
    typer.echo(stats.summary())


async def _run(
    *,
    source_url: str,
    dry_run: bool,
    limit: int | None,
    sparrow_map: dict[str, str] | None,
    user_prefix: str,
):
    legacy_engine = _legacy_engine(source_url)
    try:
        new_sessionmaker = sessionmaker_for()
        return await migrate_all(
            legacy_engine,
            new_sessionmaker,
            dry_run=dry_run,
            limit=limit,
            sparrow_map=sparrow_map,
            user_prefix=user_prefix,
        )
    finally:
        await legacy_engine.dispose()


def _legacy_engine(url: str) -> AsyncEngine:
    from sqlalchemy.ext.asyncio import create_async_engine

    # The engine is used exclusively for SELECTs; ``isolation_level='AUTOCOMMIT'``
    # is fine and avoids long-lived implicit transactions.
    return create_async_engine(url, future=True, isolation_level="AUTOCOMMIT")
