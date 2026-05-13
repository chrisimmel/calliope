"""Generic admin list/get endpoints for users / frames / images / videos / bookmarks."""

from __future__ import annotations

import pytest
from sqlalchemy import update

from calliope2.db.models import Bookmark, Image, Story, StoryFrame, User, Video


@pytest.fixture
async def admin_client(client, db_sessionmaker):
    await client.get("/v3/storytellers")
    async with db_sessionmaker() as s:
        await s.execute(
            update(User).where(User.firebase_uid == "test-uid-1").values(is_admin=True)
        )
        await s.commit()
    return client


async def test_users_list_and_get(admin_client, db_sessionmaker):
    async with db_sessionmaker() as s:
        s.add(User(firebase_uid="other-uid", email="other@x", is_admin=False))
        await s.commit()

    r = await admin_client.get("/v3/admin/users")
    assert r.status_code == 200
    body = r.json()
    emails = {u["email"] for u in body["items"]}
    assert "other@x" in emails
    assert body["page"]["total"] == 2  # admin + other

    user_id = next(u["id"] for u in body["items"] if u["email"] == "other@x")
    r2 = await admin_client.get(f"/v3/admin/users/{user_id}")
    assert r2.status_code == 200
    assert r2.json()["email"] == "other@x"


async def test_users_get_404(admin_client):
    r = await admin_client.get("/v3/admin/users/99999")
    assert r.status_code == 404


async def test_frames_list_filters_by_story(admin_client, db_sessionmaker):
    async with db_sessionmaker() as s:
        u = User(firebase_uid="u-frames")
        s.add(u)
        await s.flush()
        story_a = Story(owner_id=u.id, storyteller_name="literal")
        story_b = Story(owner_id=u.id, storyteller_name="literal")
        s.add_all([story_a, story_b])
        await s.flush()
        s.add_all(
            [
                StoryFrame(story_id=story_a.id, number=1, text="a1"),
                StoryFrame(story_id=story_a.id, number=2, text="a2"),
                StoryFrame(story_id=story_b.id, number=1, text="b1"),
            ]
        )
        await s.commit()
        story_a_id = story_a.id

    r = await admin_client.get("/v3/admin/frames", params={"story_id": story_a_id})
    assert r.status_code == 200
    texts = {f["text"] for f in r.json()["items"]}
    assert texts == {"a1", "a2"}


async def test_images_videos_bookmarks_paginate(admin_client, db_sessionmaker):
    async with db_sessionmaker() as s:
        u = User(firebase_uid="u-media")
        s.add(u)
        await s.flush()
        story = Story(owner_id=u.id, storyteller_name="literal")
        s.add(story)
        await s.flush()
        for i in range(3):
            s.add(Image(gcs_uri=f"gs://b/{i}.png", format="png"))
            s.add(Video(gcs_uri=f"gs://b/{i}.mp4", format="mp4"))
            s.add(Bookmark(owner_id=u.id, story_id=story.id, list_name=f"list-{i}"))
        await s.commit()

    for path, expected_min in (
        ("/v3/admin/images", 3),
        ("/v3/admin/videos", 3),
        ("/v3/admin/bookmarks", 3),
    ):
        r = await admin_client.get(path)
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) >= expected_min


async def test_actions_return_501(admin_client):
    r1 = await admin_client.post("/v3/admin/actions/run-command")
    assert r1.status_code == 501
    r2 = await admin_client.post("/v3/admin/actions/add-thumbnails")
    assert r2.status_code == 501
