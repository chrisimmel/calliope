"""Admin actions — ports of Piccolo Admin's custom forms.

Both endpoints are stubbed for the initial Phase 8 release; the legacy
"Run Command" was arbitrary shell execution against the prod box and
warrants a careful, allowlisted rewrite before being re-enabled. "Add
Thumbnails" is straightforward operationally but depends on storage
wiring that isn't in place yet.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from calliope2.auth.dependencies import AdminUser

router = APIRouter(prefix="/v3/admin/actions", tags=["admin"])


@router.post("/run-command", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def run_command(user: AdminUser) -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="run-command is not implemented; legacy form was unsafe by design",
    )


@router.post("/add-thumbnails", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def add_thumbnails(user: AdminUser) -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="add-thumbnails depends on the storage phase",
    )
