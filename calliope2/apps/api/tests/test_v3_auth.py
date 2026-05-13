"""Auth: token verification surface + User auto-creation on first sight."""

from __future__ import annotations

from sqlalchemy import select

from calliope2.db.models import User


async def test_missing_bearer_returns_401(app):
    """The HTTPBearer security dependency rejects unauthenticated calls."""
    from httpx import ASGITransport, AsyncClient

    from calliope2.auth.dependencies import get_firebase_claims

    # The fixture installs a claims override; remove it so HTTPBearer runs.
    app.dependency_overrides.pop(get_firebase_claims, None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v3/storytellers")
    assert response.status_code == 401


async def test_user_is_auto_created_on_first_authenticated_request(client, session):
    response = await client.get("/v3/storytellers")
    assert response.status_code == 200

    rows = (await session.execute(select(User))).scalars().all()
    assert len(rows) == 1
    user = rows[0]
    assert user.firebase_uid == "test-uid-1"
    assert user.email == "tester@example.com"
    assert user.display_name == "Tester One"
    assert user.is_admin is False


async def test_existing_user_is_not_duplicated(client, session, db_sessionmaker):
    async with db_sessionmaker() as setup:
        setup.add(
            User(
                firebase_uid="test-uid-1",
                email="prior@example.com",
                display_name="Prior",
                is_admin=True,
            )
        )
        await setup.commit()

    response = await client.get("/v3/storytellers")
    assert response.status_code == 200

    rows = (await session.execute(select(User))).scalars().all()
    assert len(rows) == 1
    # Identity preserved — neither display_name nor is_admin was overwritten by the auth path.
    assert rows[0].display_name == "Prior"
    assert rows[0].is_admin is True


async def test_invalid_token_returns_401(app, monkeypatch):
    """If verify_id_token raises, the dependency surfaces 401."""
    from httpx import ASGITransport, AsyncClient

    from calliope2.auth import firebase
    from calliope2.auth.dependencies import get_firebase_claims

    def _raise(_token):
        raise firebase.fb_auth.InvalidIdTokenError("bad token")

    # Replace the override with one that uses the real dependency path.
    app.dependency_overrides.pop(get_firebase_claims, None)
    monkeypatch.setattr(firebase, "verify_id_token", _raise)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer bogus"},
    ) as ac:
        response = await ac.get("/v3/storytellers")
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"
