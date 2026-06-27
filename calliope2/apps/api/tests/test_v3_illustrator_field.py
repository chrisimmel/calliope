"""The `illustrator` field on POST /v3/stories and /v3/stories/{id}/frames.

Tested behavior:
  - request-supplied illustrator is validated (400 if unknown)
  - request override beats storyteller default
  - storyteller default applies if request omits it
  - storytellers without use_illustrator (e.g. `literal`) accept no illustrator
  - storytellers that need an illustrator but have no default and no override
    return 400
  - experimental illustrators require admin (403 otherwise)
  - story's chosen illustrator is persisted in metadata for continuation frames
  - frame-level override beats story default; story default beats nothing
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, update

from calliope2.db.models import Story, User


@pytest.fixture(autouse=True)
def _stub_background_tasks(monkeypatch):
    monkeypatch.setattr(
        "calliope2.api.v3.stories.generate_first_frame", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "calliope2.api.v3.stories.generate_next_frame", AsyncMock(return_value=None)
    )


# ----- POST /v3/stories -----


async def test_create_story_uses_storyteller_default_when_illustrator_omitted(
    client, session
):
    r = await client.post("/v3/stories", json={"storyteller": "fern"})
    assert r.status_code == 202

    story = (await session.execute(select(Story))).scalar_one()
    assert story.metadata_ == {"illustrator": "cinematic_photo"}


async def test_create_story_persists_request_illustrator_override(client, session):
    r = await client.post(
        "/v3/stories", json={"storyteller": "lavender", "illustrator": "charcoal_abstract"}
    )
    assert r.status_code == 202

    story = (await session.execute(select(Story))).scalar_one()
    assert story.metadata_ == {"illustrator": "charcoal_abstract"}


async def test_create_story_400_on_unknown_illustrator(client):
    r = await client.post(
        "/v3/stories", json={"storyteller": "fern", "illustrator": "no_such_thing"}
    )
    assert r.status_code == 400
    assert "no_such_thing" in r.json()["detail"]


async def test_literal_storyteller_accepts_no_illustrator(client, session):
    r = await client.post(
        "/v3/stories", json={"storyteller": "literal"}
    )
    assert r.status_code == 202

    story = (await session.execute(select(Story))).scalar_one()
    # literal has no default illustrator and no use_illustrator step, so
    # metadata stays empty.
    assert story.metadata_ == {}


async def test_storyteller_that_needs_illustrator_but_has_no_default_returns_400(
    client, monkeypatch
):
    """Simulate a storyteller with use_illustrator but no `illustrator:` default,
    and no override in the request."""
    from calliope2.storytellers.runtime import Storyteller

    def fake_load(name: str) -> Storyteller:
        return Storyteller._from_dict(
            {
                "name": name,
                "steps": [
                    {
                        "use_illustrator": {
                            "inputs": {"source": "x"},
                            "out": "frame_image",
                        }
                    }
                ],
                "output": {"image": "frame_image"},
                # No `illustrator:` default
            }
        )

    monkeypatch.setattr(Storyteller, "load", staticmethod(fake_load))
    monkeypatch.setattr(
        "calliope2.api.v3.stories.Storyteller.load", staticmethod(fake_load)
    )
    # list_storytellers reads from disk; we cheat by using a real storyteller name
    # the registry knows about so the existence check passes, then fake_load returns
    # our needs-illustrator shape.

    r = await client.post("/v3/stories", json={"storyteller": "fern"})
    assert r.status_code == 400
    assert "requires an illustrator" in r.json()["detail"]


# ----- POST /v3/stories/{id}/frames -----


async def test_frame_uses_stored_story_illustrator_when_omitted(
    client, session, db_sessionmaker
):
    # Create story with charcoal_abstract pinned
    r = await client.post(
        "/v3/stories",
        json={"storyteller": "lavender", "illustrator": "charcoal_abstract"},
    )
    story_id = r.json()["story_id"]

    # Continuation frame with no illustrator override
    r = await client.post(f"/v3/stories/{story_id}/frames", json={})
    assert r.status_code == 202

    # The background-task stub recorded its args
    from calliope2.api.v3 import stories as stories_module
    args = stories_module.generate_next_frame.await_args.args
    # signature: (task_id, story_id, user_id, inputs, illustrator_override)
    assert args[-1] == "charcoal_abstract"


async def test_frame_override_beats_story_default(client):
    r = await client.post(
        "/v3/stories",
        json={"storyteller": "lavender"},  # default film_noir
    )
    story_id = r.json()["story_id"]

    r = await client.post(
        f"/v3/stories/{story_id}/frames",
        json={"illustrator": "charcoal_abstract"},
    )
    assert r.status_code == 202

    from calliope2.api.v3 import stories as stories_module
    args = stories_module.generate_next_frame.await_args.args
    assert args[-1] == "charcoal_abstract"


async def test_frame_400_on_unknown_illustrator(client):
    r = await client.post("/v3/stories", json={"storyteller": "lavender"})
    story_id = r.json()["story_id"]

    r = await client.post(
        f"/v3/stories/{story_id}/frames", json={"illustrator": "nope"}
    )
    assert r.status_code == 400


# ----- Experimental gating (the storyteller default path) -----


async def test_experimental_illustrator_blocks_non_admin(
    client, db_sessionmaker, monkeypatch, tmp_path
):
    # Set up a tmp illustrator dir with one experimental entry + the real ones
    from calliope2.illustrators import runtime as ill_runtime

    tmp_defs = tmp_path / "defs"
    tmp_defs.mkdir()
    (tmp_defs / "secret.yaml").write_text(
        """
name: secret
description: experimental
outputs: image
inputs: {required: [source]}
experimental: true
steps:
  - generate_image:
      provider: openai
      model: m
      prompt: "{{ source }}"
      out: r
output: r
"""
    )
    for real in ill_runtime.DEFS_DIR.glob("*.yaml"):
        (tmp_defs / real.name).write_text(real.read_text())
    monkeypatch.setattr(ill_runtime, "DEFS_DIR", tmp_defs)

    r = await client.post(
        "/v3/stories", json={"storyteller": "lavender", "illustrator": "secret"}
    )
    assert r.status_code == 403
    assert "experimental" in r.json()["detail"]

    # Promote, retry — succeeds
    await client.get("/v3/storytellers")
    async with db_sessionmaker() as s:
        await s.execute(
            update(User).where(User.firebase_uid == "test-uid-1").values(is_admin=True)
        )
        await s.commit()

    r = await client.post(
        "/v3/stories", json={"storyteller": "lavender", "illustrator": "secret"}
    )
    assert r.status_code == 202
