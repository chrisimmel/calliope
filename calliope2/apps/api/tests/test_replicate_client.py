from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from replicate.helpers import FileOutput

from calliope2.inference import (
    ImageBlob,
    ReplicateClient,
    UnsupportedOperation,
    VideoBlob,
)
from calliope2.inference.errors import InferenceError


def _file_output(url: str) -> FileOutput:
    """Construct a FileOutput around a fake URL without making HTTP calls."""
    return FileOutput(url=url, client=SimpleNamespace())


@pytest.fixture
def stub() -> MagicMock:
    c = MagicMock()
    c.async_run = AsyncMock()
    return c


@pytest.fixture
def client(stub: MagicMock) -> ReplicateClient:
    return ReplicateClient(api_token="test", client=stub)


async def test_image_returns_blob_with_url_from_file_output(client, stub):
    stub.async_run.return_value = _file_output("https://r2.example.com/img.png")
    blob = await client.image("a cat", model="black-forest-labs/flux-schnell")
    assert isinstance(blob, ImageBlob)
    assert blob.url == "https://r2.example.com/img.png"
    assert blob.format == "png"


async def test_image_unwraps_list_output(client, stub):
    stub.async_run.return_value = [_file_output("https://r2.example.com/a.png")]
    blob = await client.image("a cat", model="m")
    assert blob.url == "https://r2.example.com/a.png"


async def test_image_accepts_plain_string_url(client, stub):
    stub.async_run.return_value = "https://r2.example.com/b.png"
    blob = await client.image("a cat", model="m")
    assert blob.url == "https://r2.example.com/b.png"


async def test_image_passes_ref_url_as_image_input(client, stub):
    stub.async_run.return_value = _file_output("https://r2.example.com/out.png")
    await client.image(
        "a continuation", model="m", refs=[ImageBlob(url="https://x.com/ref.png")]
    )
    inputs = stub.async_run.await_args.kwargs["input"]
    assert inputs["image"] == "https://x.com/ref.png"


async def test_image_ref_without_url_raises(client):
    with pytest.raises(InferenceError, match="URL-addressable"):
        await client.image("a cat", model="m", refs=[ImageBlob(data=b"raw")])


async def test_video_returns_blob_with_duration(client, stub):
    stub.async_run.return_value = _file_output("https://r2.example.com/v.mp4")
    blob = await client.video("a clip", model="google/veo-2", duration_seconds=4.0)
    assert isinstance(blob, VideoBlob)
    assert blob.url == "https://r2.example.com/v.mp4"
    assert blob.format == "mp4"
    assert blob.duration_seconds == 4.0


async def test_empty_list_output_raises(client, stub):
    stub.async_run.return_value = []
    with pytest.raises(InferenceError, match="empty output list"):
        await client.image("a cat", model="m")


async def test_unrecognized_output_type_raises(client, stub):
    stub.async_run.return_value = 42
    with pytest.raises(InferenceError, match="unrecognized output type"):
        await client.image("a cat", model="m")


async def test_text_embed_analyze_image_unsupported(client):
    with pytest.raises(UnsupportedOperation):
        await client.text("hi")
    with pytest.raises(UnsupportedOperation):
        await client.embed("hi")
    with pytest.raises(UnsupportedOperation):
        await client.analyze_image(ImageBlob(url="x"), "describe")
