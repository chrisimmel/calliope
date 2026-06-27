"""Embedding helper: delegates to the configured inference client; try_ swallows errors."""

from __future__ import annotations

from unittest.mock import AsyncMock

from calliope2.vector import embed_text, try_embed_text


async def test_embed_text_calls_configured_provider(monkeypatch):
    mock_client = AsyncMock()
    mock_client.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

    def fake_get_client(name: str):
        assert name == "openai"
        return mock_client

    from calliope2.settings import Settings, get_settings

    monkeypatch.setattr(
        "calliope2.vector.embedding.get_settings",
        lambda: Settings(embedding_provider="openai", embedding_model="m", embedding_dim=3),
    )
    monkeypatch.setattr("calliope2.vector.embedding.get_client", fake_get_client)
    get_settings.cache_clear()

    result = await embed_text("hello")
    assert result == [0.1, 0.2, 0.3]
    mock_client.embed.assert_awaited_once_with("hello", model="m")


async def test_try_embed_text_returns_none_on_error(monkeypatch):
    async def boom(_text):
        raise RuntimeError("embed service down")

    monkeypatch.setattr("calliope2.vector.embedding.embed_text", boom)
    result = await try_embed_text("hello")
    assert result is None
