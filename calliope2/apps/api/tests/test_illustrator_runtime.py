"""Illustrator runtime: schema validation, input contract, run loop."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from calliope2.illustrators import (
    Illustrator,
    IllustratorSchemaError,
    MissingVariable,
    UnknownIllustrator,
)
from calliope2.inference import ImageBlob, VideoBlob


@pytest.fixture
def mock_client() -> MagicMock:
    c = MagicMock()
    c.image = AsyncMock()
    c.video = AsyncMock()
    c.text = AsyncMock()
    c.analyze_image = AsyncMock()
    return c


@pytest.fixture
def patch_get_client(monkeypatch, mock_client):
    monkeypatch.setattr("calliope2.pipeline.get_client", lambda _name: mock_client)
    return mock_client


# ----- Schema validation -----


def test_load_unknown_raises():
    with pytest.raises(UnknownIllustrator, match="no illustrator definition"):
        Illustrator.load("does_not_exist")


def test_missing_name_raises():
    with pytest.raises(IllustratorSchemaError, match="required field 'name'"):
        Illustrator._from_dict(
            {"outputs": "image", "output": "result", "steps": []}
        )


def test_invalid_outputs_value():
    with pytest.raises(IllustratorSchemaError, match="`outputs` must be one of"):
        Illustrator._from_dict(
            {"name": "x", "outputs": "audio", "output": "r", "steps": []}
        )


def test_output_var_required():
    with pytest.raises(IllustratorSchemaError, match="requires `output: <var_name>`"):
        Illustrator._from_dict(
            {"name": "x", "outputs": "image", "steps": []}
        )


def test_inputs_must_be_dict():
    with pytest.raises(IllustratorSchemaError, match="`inputs` must be a dict"):
        Illustrator._from_dict(
            {
                "name": "x",
                "outputs": "image",
                "output": "r",
                "inputs": ["source"],   # wrong shape
                "steps": [],
            }
        )


def test_validate_inputs_catches_missing_required():
    ill = Illustrator._from_dict(
        {
            "name": "x",
            "outputs": "image",
            "output": "r",
            "inputs": {"required": ["source"]},
            "steps": [],
        }
    )
    with pytest.raises(IllustratorSchemaError, match="missing required inputs"):
        ill.validate_inputs({})


# ----- Run loop -----


async def test_image_illustrator_returns_image_blob(patch_get_client):
    patch_get_client.image.return_value = ImageBlob(url="https://x/i.png")
    ill = Illustrator._from_dict(
        {
            "name": "test",
            "outputs": "image",
            "inputs": {"required": ["source"]},
            "style": "in the style of Hokusai,",
            "steps": [
                {
                    "generate_image": {
                        "provider": "openai",
                        "model": "gpt-image-1",
                        "prompt": "{{ style }} {{ source }}",
                        "out": "result",
                    }
                }
            ],
            "output": "result",
        }
    )
    blob = await ill.run({"source": "a wave"})
    assert isinstance(blob, ImageBlob)
    rendered = patch_get_client.image.await_args.args[0]
    assert rendered == "in the style of Hokusai, a wave"


async def test_style_passes_through_as_variable_when_set(patch_get_client):
    patch_get_client.image.return_value = ImageBlob(url="https://x/i.png")
    ill = Illustrator._from_dict(
        {
            "name": "test",
            "outputs": "image",
            "inputs": {"required": ["source"]},
            "style": "moody,",
            "steps": [
                {
                    "generate_image": {
                        "provider": "openai",
                        "model": "m",
                        "prompt": "{{ style }} {{ source }}",
                        "out": "result",
                    }
                }
            ],
            "output": "result",
        }
    )
    await ill.run({"source": "fog"})
    assert patch_get_client.image.await_args.args[0] == "moody, fog"


async def test_caller_can_override_style_via_input(patch_get_client):
    patch_get_client.image.return_value = ImageBlob(url="https://x/i.png")
    ill = Illustrator._from_dict(
        {
            "name": "test",
            "outputs": "image",
            "inputs": {"required": ["source"], "optional": ["style"]},
            "style": "default style,",
            "steps": [
                {
                    "generate_image": {
                        "provider": "openai",
                        "model": "m",
                        "prompt": "{{ style }} {{ source }}",
                        "out": "result",
                    }
                }
            ],
            "output": "result",
        }
    )
    await ill.run({"source": "x", "style": "overridden,"})
    assert patch_get_client.image.await_args.args[0] == "overridden, x"


async def test_video_illustrator_returns_video_blob(patch_get_client):
    patch_get_client.video.return_value = VideoBlob(
        url="https://x/v.mp4", duration_seconds=4.0
    )
    ill = Illustrator._from_dict(
        {
            "name": "motion",
            "outputs": "video",
            "inputs": {"required": ["source"]},
            "steps": [
                {
                    "generate_video": {
                        "provider": "replicate",
                        "model": "google/veo-2",
                        "prompt": "{{ source }}",
                        "out": "result",
                    }
                }
            ],
            "output": "result",
        }
    )
    blob = await ill.run({"source": "a long shore"})
    assert isinstance(blob, VideoBlob)
    assert blob.duration_seconds == 4.0


async def test_run_rejects_missing_required_inputs():
    ill = Illustrator._from_dict(
        {
            "name": "x",
            "outputs": "image",
            "inputs": {"required": ["source"]},
            "steps": [],
            "output": "source",
        }
    )
    with pytest.raises(IllustratorSchemaError, match="missing required inputs"):
        await ill.run({})


async def test_output_must_be_produced(patch_get_client):
    """Declared output var never assigned → clear schema error."""
    patch_get_client.image.return_value = ImageBlob(url="https://x/i.png")
    ill = Illustrator._from_dict(
        {
            "name": "x",
            "outputs": "image",
            "inputs": {"required": ["source"]},
            "steps": [
                {
                    "generate_image": {
                        "provider": "openai",
                        "model": "m",
                        "prompt": "{{ source }}",
                        "out": "frame_image",   # written here, but...
                    }
                }
            ],
            "output": "result",     # ... declared as 'result'
        }
    )
    with pytest.raises(IllustratorSchemaError, match="output variable 'result'"):
        await ill.run({"source": "x"})


async def test_analyze_image_in_illustrator_pulls_from_inputs(patch_get_client):
    patch_get_client.analyze_image.return_value = "soft light"
    patch_get_client.image.return_value = ImageBlob(url="https://x/i.png")
    ill = Illustrator._from_dict(
        {
            "name": "x",
            "outputs": "image",
            "inputs": {"required": ["source_image"]},
            "steps": [
                {
                    "analyze_image": {
                        "provider": "openai",
                        "model": "gpt-4o",
                        "input": "source_image",
                        "prompt": "describe this",
                        "out": "scene",
                    }
                },
                {
                    "generate_image": {
                        "provider": "openai",
                        "model": "gpt-image-1",
                        "prompt": "{{ scene }}",
                        "out": "result",
                    }
                },
            ],
            "output": "result",
        }
    )
    blob = await ill.run({"source_image": ImageBlob(url="https://x/in.png")})
    assert isinstance(blob, ImageBlob)
    # Second step received the analyze_image output
    assert patch_get_client.image.await_args.args[0] == "soft light"


async def test_missing_variable_in_analyze_image(patch_get_client):
    ill = Illustrator._from_dict(
        {
            "name": "x",
            "outputs": "image",
            "inputs": {"required": ["other_var"]},
            "steps": [
                {
                    "analyze_image": {
                        "provider": "openai",
                        "model": "m",
                        "input": "missing_var",
                        "prompt": "x",
                        "out": "scene",
                    }
                }
            ],
            "output": "scene",
        }
    )
    with pytest.raises(MissingVariable, match="missing_var"):
        await ill.run({"other_var": "x"})
