"""`GET /v3/illustrators` — list available Illustrators.

Non-admin users see only ``experimental: false`` illustrators. Admins see
the full list.
"""

from __future__ import annotations

from fastapi import APIRouter

from calliope2.api.v3.schemas import IllustratorOut
from calliope2.auth.dependencies import CurrentUser
from calliope2.illustrators import Illustrator, list_illustrators

router = APIRouter(prefix="/v3/illustrators", tags=["illustrators"])


@router.get("", response_model=list[IllustratorOut])
async def list_all(user: CurrentUser) -> list[IllustratorOut]:
    items: list[IllustratorOut] = []
    for name in list_illustrators():
        ill = Illustrator.load(name)
        if ill.experimental and not user.is_admin:
            continue
        items.append(
            IllustratorOut(
                name=name,
                description=ill.description.strip(),
                outputs=ill.outputs,
                experimental=ill.experimental,
            )
        )
    return items
