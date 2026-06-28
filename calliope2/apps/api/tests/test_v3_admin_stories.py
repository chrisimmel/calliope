"""Admin story browse + detail — cross-user visibility, search filter, pagination."""

from __future__ import annotations

import pytest
from sqlalchemy import update

from calliope2.db.models import Image, Story, StoryFrame, User


@pytest.fixture
async def admin_client(client, db_sessionmaker):
    """Flip the auto-created test user to is_admin=True."""
    await client.get("/v3/storytellers")  # trigger auto-create
    async with db_sessionmaker() as s:
        await s.execute(update(User).where(User.firebase_uid == "test-uid-1").values(is_admin=True))
        await s.commit()
    return client


@pytest.fixture
async def seeded(db_sessionmaker):
    """Seed two users, three stories across them."""
    async with db_sessionmaker() as s:
        alice = User(firebase_uid="alice-uid", email="alice@x", display_name="Alice")
        bob = User(firebase_uid="bob-uid", email="bob@x", display_name="Bob")
        s.add_all([alice, bob])
        await s.flush()
        s.add_all(
            [
                Story(owner_id=alice.id, storyteller_name="fern", title="Alice One"),
                Story(owner_id=alice.id, storyteller_name="fern", title="Alice Two"),
                Story(owner_id=bob.id, storyteller_name="literal", title="Bob Story"),
            ]
        )
        await s.commit()
    return None


async def test_list_stories_sees_every_user(admin_client, seeded):
    r = await admin_client.get("/v3/admin/stories")
    assert r.status_code == 200
    body = r.json()
    titles = {item["title"] for item in body["items"]}
    assert titles == {"Alice One", "Alice Two", "Bob Story"}
    owner_emails = {item["owner_email"] for item in body["items"]}
    assert owner_emails == {"alice@x", "bob@x"}
    assert body["page"]["total"] == 3


async def test_list_stories_filters_by_query(admin_client, seeded):
    r = await admin_client.get("/v3/admin/stories", params={"q": "alice"})
    assert r.status_code == 200
    titles = {item["title"] for item in r.json()["items"]}
    assert titles == {"Alice One", "Alice Two"}


async def test_list_stories_cursor_paginates(admin_client, seeded):
    r = await admin_client.get("/v3/admin/stories", params={"limit": 2})
    body = r.json()
    assert len(body["items"]) == 2
    assert body["page"]["next_cursor"] is not None

    next_cursor = body["page"]["next_cursor"]
    r2 = await admin_client.get("/v3/admin/stories", params={"limit": 2, "cursor": next_cursor})
    body2 = r2.json()
    assert len(body2["items"]) == 1
    assert body2["page"]["next_cursor"] is None


async def test_get_story_includes_frames_and_owner_email(admin_client, db_sessionmaker, seeded):
    # Add a frame with media to one of the seeded stories
    async with db_sessionmaker() as s:
        story_id = (
            (await s.execute(Story.__table__.select().where(Story.title == "Alice One"))).first().id
        )
        img = Image(gcs_uri="gs://b/a.png", format="png", width=512, height=512)
        s.add(img)
        await s.flush()
        s.add(StoryFrame(story_id=story_id, number=1, text="hello", image_id=img.id))
        await s.commit()

    r = await admin_client.get(f"/v3/admin/stories/{story_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Alice One"
    assert body["owner_email"] == "alice@x"
    assert len(body["frames"]) == 1
    assert body["frames"][0]["image_url"] == "https://storage.googleapis.com/b/a.png"
    assert body["frames"][0]["has_embedding"] is False


async def test_get_story_404_when_missing(admin_client):
    r = await admin_client.get("/v3/admin/stories/99999")
    assert r.status_code == 404
