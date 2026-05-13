"""`GET /v3/storytellers` — list available YAML storytellers."""

from __future__ import annotations

from fastapi import APIRouter

from calliope2.api.v3.schemas import StorytellerOut
from calliope2.auth.dependencies import CurrentUser
from calliope2.storytellers import Storyteller, list_storytellers

router = APIRouter(prefix="/v3/storytellers", tags=["storytellers"])


@router.get("", response_model=list[StorytellerOut])
async def list_all(user: CurrentUser) -> list[StorytellerOut]:
    return [
        StorytellerOut(name=name, description=Storyteller.load(name).description.strip())
        for name in list_storytellers()
    ]
