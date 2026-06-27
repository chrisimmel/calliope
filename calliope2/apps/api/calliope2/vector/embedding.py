"""Embedding helper — wraps the configured inference client.

A thin async function so callers don't have to thread embedding model and
provider through every call site. The provider/model come from settings.
"""

from __future__ import annotations

import logging

from calliope2.inference import get_client
from calliope2.settings import get_settings

logger = logging.getLogger(__name__)


async def embed_text(text: str) -> list[float]:
    """Return an embedding for ``text`` using the configured provider/model."""
    settings = get_settings()
    client = get_client(settings.embedding_provider)
    result = await client.embed(text, model=settings.embedding_model)
    if len(result) != settings.embedding_dim:
        raise ValueError(
            f"embedding dimension mismatch: expected {settings.embedding_dim}, "
            f"got {len(result)} — check CALLIOPE2_EMBEDDING_MODEL / CALLIOPE2_EMBEDDING_DIM"
        )
    return result


async def try_embed_text(text: str) -> list[float] | None:
    """Best-effort embed: catches failures and returns None (logged).

    Used by the frame-persistence path where missing an embedding is
    acceptable — the reindex CLI catches up later.
    """
    try:
        return await embed_text(text)
    except Exception:
        logger.exception("embedding failed; will be backfilled via reindex")
        return None
