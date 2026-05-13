"""Provider registry — `get_client(name)` returns a configured client."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from calliope2.inference.openai_compatible import OpenAICompatibleClient
from calliope2.inference.replicate_client import ReplicateClient
from calliope2.settings import get_settings

if TYPE_CHECKING:
    from calliope2.inference.protocol import InferenceClient


@lru_cache(maxsize=8)
def get_client(name: str) -> InferenceClient:
    """Return a provider client by string key.

    Recognized keys: ``openai``, ``anthropic``, ``openrouter``, ``replicate``.
    Additional OpenAI-compatible providers can be added without code change
    by setting ``CALLIOPE2_OPENAI_BASE_URL`` and using ``openai``.
    """
    settings = get_settings()

    if name == "openai":
        return OpenAICompatibleClient(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            provider="openai",
        )
    if name == "anthropic":
        return OpenAICompatibleClient(
            api_key=settings.anthropic_api_key.get_secret_value(),
            base_url=settings.anthropic_base_url,
            provider="anthropic",
        )
    if name == "openrouter":
        return OpenAICompatibleClient(
            api_key=settings.openrouter_api_key.get_secret_value(),
            base_url=settings.openrouter_base_url,
            provider="openrouter",
        )
    if name == "replicate":
        return ReplicateClient(api_token=settings.replicate_api_token.get_secret_value())

    raise ValueError(
        f"unknown inference provider {name!r}; "
        "expected one of: openai, anthropic, openrouter, replicate"
    )
