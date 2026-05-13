import pytest

from calliope2.inference import (
    InferenceClient,
    OpenAICompatibleClient,
    ReplicateClient,
    get_client,
)
from calliope2.inference.registry import get_client as _registry_fn


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    _registry_fn.cache_clear()
    yield
    _registry_fn.cache_clear()


def test_get_client_returns_openai_compatible_for_known_providers():
    for name in ("openai", "anthropic", "openrouter"):
        client = get_client(name)
        assert isinstance(client, OpenAICompatibleClient)
        assert client.provider == name


def test_get_client_returns_replicate():
    client = get_client("replicate")
    assert isinstance(client, ReplicateClient)
    assert client.provider == "replicate"


def test_get_client_unknown_provider_raises():
    with pytest.raises(ValueError, match="unknown inference provider"):
        get_client("bogus")


def test_clients_satisfy_protocol():
    assert isinstance(OpenAICompatibleClient(api_key="x"), InferenceClient)
    assert isinstance(ReplicateClient(api_token="x"), InferenceClient)
