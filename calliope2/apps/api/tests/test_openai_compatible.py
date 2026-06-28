import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from calliope2.inference import (
    AudioBlob,
    ImageBlob,
    InferenceError,
    OpenAICompatibleClient,
    UnsupportedOperation,
)


def _stub_openai_client() -> MagicMock:
    """Build a MagicMock shaped like AsyncOpenAI for these tests."""
    client = MagicMock()
    client.chat.completions.create = AsyncMock()
    client.chat.completions.parse = AsyncMock()
    client.embeddings.create = AsyncMock()
    client.images.generate = AsyncMock()
    client.audio.transcriptions.create = AsyncMock()
    return client


@pytest.fixture
def stub() -> MagicMock:
    return _stub_openai_client()


@pytest.fixture
def client(stub: MagicMock) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(api_key="test", client=stub)


async def test_text_returns_message_content(client, stub):
    stub.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="hello world"))]
    )
    result = await client.text("hi", model="gpt-test")
    assert result == "hello world"
    stub.chat.completions.create.assert_awaited_once()
    kwargs = stub.chat.completions.create.await_args.kwargs
    assert kwargs["model"] == "gpt-test"
    assert kwargs["messages"][-1] == {"role": "user", "content": "hi"}


async def test_text_with_system_prompt_prepends_system_message(client, stub):
    stub.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
    )
    await client.text("hi", model="m", system="be brief")
    messages = stub.chat.completions.create.await_args.kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "be brief"}


async def test_text_with_schema_uses_parse_and_returns_pydantic(client, stub):
    class Recipe(BaseModel):
        name: str
        steps: list[str]

    expected = Recipe(name="toast", steps=["bread", "heat"])
    stub.chat.completions.parse.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=expected))]
    )
    result = await client.text("make a recipe", model="m", schema=Recipe)
    assert result == expected
    stub.chat.completions.parse.assert_awaited_once()
    assert stub.chat.completions.parse.await_args.kwargs["response_format"] is Recipe


async def test_embed_returns_vector(client, stub):
    stub.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])]
    )
    result = await client.embed("hello", model="text-embedding-3-small")
    assert result == [0.1, 0.2, 0.3]
    stub.embeddings.create.assert_awaited_once_with(model="text-embedding-3-small", input="hello")


async def test_image_decodes_b64_into_image_blob(client, stub):
    raw = b"\x89PNG fake bytes"
    stub.images.generate.return_value = SimpleNamespace(
        data=[SimpleNamespace(b64_json=base64.b64encode(raw).decode("ascii"))]
    )
    blob = await client.image("a cat", model="gpt-image-1", size="1024x1024")
    assert isinstance(blob, ImageBlob)
    assert blob.data == raw
    assert blob.format == "png"
    kwargs = stub.images.generate.await_args.kwargs
    assert kwargs["model"] == "gpt-image-1"
    assert kwargs["size"] == "1024x1024"
    assert kwargs["response_format"] == "b64_json"


async def test_image_rejects_refs(client):
    with pytest.raises(UnsupportedOperation, match="reference images"):
        await client.image("a cat", model="m", refs=[ImageBlob(url="http://x")])


async def test_video_always_unsupported(client):
    with pytest.raises(UnsupportedOperation, match="video"):
        await client.video("a clip", model="m")


async def test_analyze_image_sends_data_uri_when_no_url(client, stub):
    stub.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="a cat"))]
    )
    blob = ImageBlob(data=b"\x89PNG", format="png")
    result = await client.analyze_image(blob, "what is this?", model="gpt-4o-mini")
    assert result == "a cat"
    msg = stub.chat.completions.create.await_args.kwargs["messages"][0]
    image_part = msg["content"][1]
    assert image_part["type"] == "image_url"
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")


async def test_analyze_image_passes_through_url(client, stub):
    stub.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
    )
    blob = ImageBlob(url="https://example.com/x.png")
    await client.analyze_image(blob, "describe", model="m")
    msg = stub.chat.completions.create.await_args.kwargs["messages"][0]
    assert msg["content"][1]["image_url"]["url"] == "https://example.com/x.png"


async def test_transcribe_sends_bytes_and_returns_text(client, stub):
    stub.audio.transcriptions.create.return_value = SimpleNamespace(text="a remembered afternoon")
    audio = AudioBlob(data=b"OggS bytes", format="webm")
    result = await client.transcribe(audio, model="whisper-1")
    assert result == "a remembered afternoon"
    kwargs = stub.audio.transcriptions.create.await_args.kwargs
    assert kwargs["model"] == "whisper-1"
    filename, payload = kwargs["file"]
    assert filename == "audio.webm"
    assert payload == b"OggS bytes"
    assert "prompt" not in kwargs  # omitted when not provided


async def test_transcribe_forwards_prompt_when_given(client, stub):
    stub.audio.transcriptions.create.return_value = SimpleNamespace(text="ok")
    await client.transcribe(
        AudioBlob(data=b"x", format="mp4"), model="whisper-1", prompt="names: Abigail"
    )
    assert stub.audio.transcriptions.create.await_args.kwargs["prompt"] == "names: Abigail"


async def test_transcribe_requires_bytes(client):
    with pytest.raises(InferenceError, match="audio bytes"):
        await client.transcribe(AudioBlob(url="https://x/clip.mp3"), model="whisper-1")
