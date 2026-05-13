"""Non-admins get 403 on /v3/admin/*; admins get through."""

from __future__ import annotations

from sqlalchemy import update

from calliope2.db.models import User


async def test_non_admin_blocked_from_admin_routes(client):
    # The fixture's auto-created User has is_admin=False by default.
    # Hit any admin route to confirm 403.
    for path in (
        "/v3/admin/stories",
        "/v3/admin/users",
        "/v3/admin/search?q=x",
    ):
        r = await client.get(path)
        assert r.status_code == 403, f"{path}: {r.status_code} {r.text}"


async def test_admin_user_passes_the_gate(client, session, db_sessionmaker):
    # Materialize the user, then flip is_admin.
    await client.get("/v3/storytellers")  # forces auto-create
    async with db_sessionmaker() as s:
        await s.execute(
            update(User).where(User.firebase_uid == "test-uid-1").values(is_admin=True)
        )
        await s.commit()

    r = await client.get("/v3/admin/stories")
    assert r.status_code == 200
    assert r.json() == {"items": [], "page": {"next_cursor": None, "total": 0}}
