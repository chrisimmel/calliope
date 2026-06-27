"""GET /v3/search?q=... — pgvector semantic search across the user's frames."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status

logger = logging.getLogger(__name__)

from calliope2.api.v3.schemas import SearchHitOut, SearchResponse
from calliope2.auth.dependencies import CurrentUser, SessionDep
from calliope2.vector import embed_text, search_frames

router = APIRouter(prefix="/v3/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    user: CurrentUser,
    session: SessionDep,
    q: str = Query(..., min_length=1, description="Free-text search query"),
    limit: int = Query(20, ge=1, le=100),
) -> SearchResponse:
    try:
        embedding = await embed_text(q)
    except Exception as e:
        logger.exception("embedding failed for search query")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="embedding service unavailable",
        ) from e

    hits = await search_frames(session, embedding, owner_id=user.id, limit=limit)
    return SearchResponse(
        query=q,
        hits=[
            SearchHitOut(
                frame_id=h.frame_id,
                story_id=h.story_id,
                story_title=h.story_title,
                frame_number=h.frame_number,
                frame_text=h.frame_text,
                image_url=h.image_url,
                distance=h.distance,
            )
            for h in hits
        ],
    )
