"""Runtime tests: each step executor + variable threading, with mocked clients."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from calliope2.inference import ImageBlob, VideoBlob
from calliope2.strategies import (
    FrameOutput,
    MissingVariable,
    StoryStrategy,
    StrategySchemaError,
    run_strategy,
)


@pytest.fixture
def mock_client() -> MagicMock:
    c = MagicMock()
    c.text = AsyncMock()
    c.image = AsyncMock()
    c.video = AsyncMock()
    c.analyze_image = AsyncMock()
    c.embed = AsyncMock()
    return c


@pytest.fixture
def patch_get_client(monkeypatch, mock_client):
    """Patch get_client at the runtime import site so every step uses our mock."""
    monkeypatch.setattr(
        "calliope2.strategies.runtime.get_client", lambda _name: mock_client
    )
    return mock_client


async def test_literal_strategy_runs_without_inference(patch_get_client):
    out = await run_strategy("literal", {"source_text": "A still afternoon."})
    assert out == FrameOutput(text="A still afternoon.")
    patch_get_client.text.assert_not_called()
    patch_get_client.image.assert_not_called()


async def test_simple_one_frame_calls_text_then_image(patch_get_client):
    patch_get_client.text.return_value = "the heat hangs"
    patch_get_client.image.return_value = ImageBlob(data=b"\x89PNG", format="png")

    out = await run_strategy("simple_one_frame", {"theme": "summer"})

    assert out.text == "the heat hangs"
    assert out.image is not None
    assert out.video is None

    patch_get_client.text.assert_awaited_once()
    text_kwargs = patch_get_client.text.await_args.kwargs
    assert text_kwargs["model"] == "gpt-4o-mini"
    text_prompt = patch_get_client.text.await_args.args[0]
    assert "summer" in text_prompt

    patch_get_client.image.assert_awaited_once()
    image_prompt = patch_get_client.image.await_args.args[0]
    assert image_prompt == "the heat hangs"


async def test_fern_threads_scene_into_narration(patch_get_client):
    patch_get_client.analyze_image.return_value = "a quiet kitchen, late afternoon"
    patch_get_client.text.return_value = "Sun on the linoleum."
    patch_get_client.image.return_value = ImageBlob(url="https://x.com/i.png")

    out = await run_strategy(
        "fern", {"source_image": ImageBlob(url="https://x.com/src.png")}
    )

    assert out.text == "Sun on the linoleum."
    narrate_prompt = patch_get_client.text.await_args.args[0]
    assert "a quiet kitchen, late afternoon" in narrate_prompt

    illustrate_prompt = patch_get_client.image.await_args.args[0]
    assert "Sun on the linoleum." in illustrate_prompt


async def test_narcissus_returns_image_only(patch_get_client):
    patch_get_client.analyze_image.return_value = "blue light, single chair"
    patch_get_client.image.return_value = ImageBlob(url="https://x.com/i.png")

    out = await run_strategy(
        "narcissus", {"source_image": ImageBlob(url="https://x.com/src.png")}
    )

    assert out.text is None
    assert out.image is not None


async def test_continuous_v1_branches_on_previous_text(patch_get_client):
    patch_get_client.text.return_value = "next paragraph"
    patch_get_client.image.return_value = ImageBlob(url="https://x.com/i.png")

    await run_strategy("continuous_v1", {"previous_text": "earlier paragraph"})
    continue_prompt = patch_get_client.text.await_args.args[0]
    assert "continuing a multi-frame narrative" in continue_prompt
    assert "earlier paragraph" in continue_prompt

    patch_get_client.text.reset_mock()
    await run_strategy("continuous_v1", {"previous_text": ""})
    new_prompt = patch_get_client.text.await_args.args[0]
    assert "Begin a new multi-frame narrative" in new_prompt


async def test_generate_video_dispatches_to_client(patch_get_client):
    patch_get_client.video.return_value = VideoBlob(
        url="https://x.com/v.mp4", duration_seconds=4.0
    )
    yaml_dict = {
        "name": "video_demo",
        "steps": [
            {
                "generate_video": {
                    "provider": "replicate",
                    "model": "google/veo-2",
                    "prompt": "{{ topic }}",
                    "out": "frame_video",
                }
            }
        ],
        "output": {"video": "frame_video"},
    }
    strategy = StoryStrategy._from_dict(yaml_dict)
    out = await strategy.run({"topic": "a long shore"})
    assert out.video is not None
    patch_get_client.video.assert_awaited_once()
    assert patch_get_client.video.await_args.args[0] == "a long shore"


async def test_analyze_image_missing_input_raises(patch_get_client):
    with pytest.raises(MissingVariable, match="source_image"):
        await run_strategy("fern", inputs={})


async def test_analyze_image_input_must_be_image_blob(patch_get_client):
    with pytest.raises(StrategySchemaError, match="must be an ImageBlob"):
        await run_strategy("fern", {"source_image": "not an image"})


async def test_missing_required_step_field_raises(patch_get_client):
    yaml_dict = {
        "name": "broken",
        "steps": [{"generate_text": {"provider": "openai", "out": "x"}}],
    }
    strategy = StoryStrategy._from_dict(yaml_dict)
    with pytest.raises(StrategySchemaError, match="requires field 'model'"):
        await strategy.run({})


async def test_missing_template_file_raises(patch_get_client):
    yaml_dict = {
        "name": "broken",
        "steps": [
            {
                "generate_text": {
                    "provider": "openai",
                    "model": "m",
                    "prompt": "prompts/does/not/exist.j2",
                    "out": "x",
                }
            }
        ],
    }
    strategy = StoryStrategy._from_dict(yaml_dict)
    with pytest.raises(StrategySchemaError, match="prompt template not found"):
        await strategy.run({})


async def test_inline_template_renders_without_loader(patch_get_client):
    patch_get_client.text.return_value = "ok"
    yaml_dict = {
        "name": "inline",
        "steps": [
            {
                "generate_text": {
                    "provider": "openai",
                    "model": "m",
                    "prompt": "Hello {{ who }}.",
                    "out": "result",
                }
            }
        ],
        "output": {"text": "result"},
    }
    out = await StoryStrategy._from_dict(yaml_dict).run({"who": "world"})
    assert out.text == "ok"
    assert patch_get_client.text.await_args.args[0] == "Hello world."


async def test_set_step_supports_jinja_in_value(patch_get_client):
    yaml_dict = {
        "name": "settest",
        "steps": [
            {"set": {"value": "{{ a }} + {{ b }}", "out": "c"}},
            {"set": {"value": "{{ c }} = sum", "out": "d"}},
        ],
        "output": {"text": "d"},
    }
    out = await StoryStrategy._from_dict(yaml_dict).run({"a": "1", "b": "2"})
    assert out.text == "1 + 2 = sum"
