"""/v3/search — embed query, dispatch to search_frames, shape the response."""

from __future__ import annotations

from unittest.mock import AsyncMock


async def test_search_returns_serialized_hits(client, monkeypatch):
    from calliope2.vector.search import SearchHit

    monkeypatch.setattr(
        "calliope2.api.v3.search.embed_text",
        AsyncMock(return_value=[0.1] * 1536),
    )
    monkeypatch.setattr(
        "calliope2.api.v3.search.search_frames",
        AsyncMock(
            return_value=[
                SearchHit(
                    frame_id=10, story_id=1, story_title="A",
                    frame_number=1, frame_text="hello",
                    image_url="gs://b/i.png", distance=0.12,
                ),
                SearchHit(
                    frame_id=11, story_id=1, story_title="A",
                    frame_number=2, frame_text="world",
                    image_url=None, distance=0.34,
                ),
            ]
        ),
    )

    response = await client.get("/v3/search", params={"q": "anything"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "anything"
    assert len(body["hits"]) == 2
    assert body["hits"][0] == {
        "frame_id": 10, "story_id": 1, "story_title": "A",
        "frame_number": 1, "frame_text": "hello",
        "image_url": "gs://b/i.png", "distance": 0.12,
    }


async def test_search_502_when_embedding_fails(client, monkeypatch):
    async def boom(_q):
        raise RuntimeError("openai down")

    monkeypatch.setattr("calliope2.api.v3.search.embed_text", boom)
    response = await client.get("/v3/search", params={"q": "x"})
    assert response.status_code == 502
    assert "openai down" in response.json()["detail"]


async def test_search_rejects_empty_query(client):
    response = await client.get("/v3/search", params={"q": ""})
    assert response.status_code == 422


async def test_search_respects_limit_bounds(client, monkeypatch):
    monkeypatch.setattr(
        "calliope2.api.v3.search.embed_text", AsyncMock(return_value=[0.0] * 1536)
    )
    monkeypatch.setattr(
        "calliope2.api.v3.search.search_frames", AsyncMock(return_value=[])
    )
    over = await client.get("/v3/search", params={"q": "x", "limit": 500})
    assert over.status_code == 422
    under = await client.get("/v3/search", params={"q": "x", "limit": 0})
    assert under.status_code == 422
