"""Admin-wide semantic search — Thoth's /thoth/search successor.

Same machinery as /v3/search but unscoped (admin sees content from every
user). Each hit carries owner info.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from calliope2.api.v3.admin.schemas import AdminSearchHitOut, AdminSearchResponse
from calliope2.auth.dependencies import AdminUser, SessionDep
from calliope2.db.models import Story, User
from calliope2.vector import embed_text, search_frames

router = APIRouter(prefix="/v3/admin/search", tags=["admin"])


@router.get("", response_model=AdminSearchResponse)
async def admin_search(
    user: AdminUser,
    session: SessionDep,
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
) -> AdminSearchResponse:
    try:
        embedding = await embed_text(q)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"embedding service failed: {e}",
        ) from e

    hits = await search_frames(session, embedding, owner_id=None, limit=limit)
    if not hits:
        return AdminSearchResponse(query=q, hits=[])

    story_ids = {h.story_id for h in hits}
    owner_rows = (
        await session.execute(
            select(Story.id, Story.owner_id, User.email)
            .join(User, Story.owner_id == User.id)
            .where(Story.id.in_(story_ids))
        )
    ).all()
    owners = {row[0]: (row[1], row[2]) for row in owner_rows}

    return AdminSearchResponse(
        query=q,
        hits=[
            AdminSearchHitOut(
                frame_id=h.frame_id,
                story_id=h.story_id,
                story_title=h.story_title,
                owner_id=owners.get(h.story_id, (None, None))[0],
                owner_email=owners.get(h.story_id, (None, None))[1],
                frame_number=h.frame_number,
                frame_text=h.frame_text,
                image_url=h.image_url,
                distance=h.distance,
            )
            for h in hits
        ],
    )
