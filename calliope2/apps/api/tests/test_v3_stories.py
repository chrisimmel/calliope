"""Tests for /v3/stories. Background tasks (frame generation) are not run
during these tests — TestClient's BackgroundTasks runner is only invoked when
the response is awaited synchronously, which httpx.AsyncClient does. We patch
the task functions to no-op so we can assert they would have been enqueued
without actually invoking inference clients."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from calliope2.db.models import Image, Story, StoryFrame, User, Video


@pytest.fixture(autouse=True)
def _stub_background_tasks(monkeypatch):
    """Stop frame-generation tasks from actually running inference."""
    monkeypatch.setattr(
        "calliope2.api.v3.stories.generate_first_frame", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "calliope2.api.v3.stories.generate_next_frame", AsyncMock(return_value=None)
    )


async def test_create_story_persists_row_and_returns_task_id(client, session):
    response = await client.post(
        "/v3/stories",
        json={"storyteller": "fern", "inputs": {"source_image_url": "https://x/i.png"}},
    )
    assert response.status_code == 202
    body = response.json()
    assert isinstance(body["story_id"], int)
    assert body["task_id"]

    story = (await session.execute(select(Story))).scalar_one()
    assert story.id == body["story_id"]
    assert story.storyteller_name == "fern"
    user = (await session.execute(select(User))).scalar_one()
    assert story.owner_id == user.id


async def test_create_story_rejects_unknown_storyteller(client):
    response = await client.post(
        "/v3/stories",
        json={"storyteller": "ghost", "inputs": {}},
    )
    assert response.status_code == 400
    assert "ghost" in response.json()["detail"]


async def test_list_stories_returns_only_owner_stories(client, session, db_sessionmaker):
    response = await client.post(
        "/v3/stories", json={"storyteller": "literal", "title": "Mine"}
    )
    assert response.status_code == 202

    async with db_sessionmaker() as setup:
        other = User(firebase_uid="someone-else", email="o@x")
        setup.add(other)
        await setup.flush()
        setup.add(Story(owner_id=other.id, storyteller_name="literal", title="Theirs"))
        await setup.commit()

    response = await client.get("/v3/stories")
    assert response.status_code == 200
    body = response.json()
    titles = [s["title"] for s in body]
    assert titles == ["Mine"]


async def test_get_story_404_when_not_owner(client, db_sessionmaker):
    async with db_sessionmaker() as setup:
        other = User(firebase_uid="someone-else")
        setup.add(other)
        await setup.flush()
        s = Story(owner_id=other.id, storyteller_name="literal", title="Theirs")
        setup.add(s)
        await setup.commit()
        other_story_id = s.id

    response = await client.get(f"/v3/stories/{other_story_id}")
    assert response.status_code == 404


async def test_get_story_returns_frames_with_image_and_video_urls(
    client, session, db_sessionmaker
):
    create = await client.post(
        "/v3/stories", json={"storyteller": "fern", "title": "S"}
    )
    story_id = create.json()["story_id"]

    async with db_sessionmaker() as setup:
        img = Image(gcs_uri="gs://b/img.png", format="png", width=1024, height=1024)
        vid = Video(gcs_uri="gs://b/v.mp4", format="mp4", duration_seconds=4.0)
        setup.add_all([img, vid])
        await setup.flush()
        setup.add_all([
            StoryFrame(story_id=story_id, number=1, text="frame one", image_id=img.id),
            StoryFrame(story_id=story_id, number=2, text="frame two", video_id=vid.id),
        ])
        await setup.commit()

    response = await client.get(f"/v3/stories/{story_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "S"
    assert body["storyteller_name"] == "fern"
    assert len(body["frames"]) == 2
    f1, f2 = body["frames"]
    assert f1["number"] == 1
    assert f1["text"] == "frame one"
    assert f1["image_url"] == "gs://b/img.png"
    assert f1["video_url"] is None
    assert f2["number"] == 2
    assert f2["video_url"] == "gs://b/v.mp4"
    assert f2["image_url"] is None


async def test_create_frame_404_when_story_missing(client):
    response = await client.post("/v3/stories/9999/frames", json={"inputs": {}})
    assert response.status_code == 404


async def test_create_frame_returns_task_id(client):
    create = await client.post(
        "/v3/stories", json={"storyteller": "continuous_v1", "title": "C"}
    )
    story_id = create.json()["story_id"]

    response = await client.post(
        f"/v3/stories/{story_id}/frames",
        json={"inputs": {"theme": "still life"}},
    )
    assert response.status_code == 202
    assert response.json()["task_id"]
