"""Runtime tests: each step executor + variable threading, with mocked clients."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from calliope2.inference import AudioBlob, ImageBlob, VideoBlob
from calliope2.storytellers import (
    FrameOutput,
    MissingVariable,
    Storyteller,
    StorytellerSchemaError,
    run_storyteller,
)


@pytest.fixture
def mock_client() -> MagicMock:
    c = MagicMock()
    c.text = AsyncMock()
    c.image = AsyncMock()
    c.video = AsyncMock()
    c.analyze_image = AsyncMock()
    c.transcribe = AsyncMock()
    c.embed = AsyncMock()
    return c


@pytest.fixture
def patch_get_client(monkeypatch, mock_client):
    """Patch get_client at the shared dispatch site (calliope2.pipeline) so every
    step in both Storyteller and Illustrator runtimes uses our mock."""
    monkeypatch.setattr("calliope2.pipeline.get_client", lambda _name: mock_client)
    return mock_client


async def test_literal_storyteller_runs_without_inference(patch_get_client):
    out = await run_storyteller("literal", {"source_text": "A still afternoon."})
    assert out == FrameOutput(text="A still afternoon.")
    patch_get_client.text.assert_not_called()
    patch_get_client.image.assert_not_called()


async def test_simple_one_frame_calls_text_then_illustrator(patch_get_client):
    patch_get_client.text.return_value = "the heat hangs"
    patch_get_client.image.return_value = ImageBlob(data=b"\x89PNG", format="png")

    out = await run_storyteller("simple_one_frame", {"theme": "summer"})

    assert out.text == "the heat hangs"
    assert out.image is not None
    assert out.video is None

    patch_get_client.text.assert_awaited_once()
    text_kwargs = patch_get_client.text.await_args.kwargs
    assert text_kwargs["model"] == "gpt-4o"
    text_prompt = patch_get_client.text.await_args.args[0]
    assert "summer" in text_prompt

    # simple_one_frame's default illustrator is cinematic_photo; the rendered
    # image prompt is "<style> <source>" where source is the frame text.
    patch_get_client.image.assert_awaited_once()
    image_prompt = patch_get_client.image.await_args.args[0]
    assert "the heat hangs" in image_prompt
    assert "cinematic photo" in image_prompt  # the cinematic_photo style


async def test_fern_threads_previous_text_into_narration(patch_get_client):
    patch_get_client.text.return_value = "Sun on the linoleum."
    patch_get_client.image.return_value = ImageBlob(url="https://x.com/i.png")

    out = await run_storyteller(
        "fern",
        {"previous_text": "She set the kettle on.", "situation": "Late autumn."},
    )

    assert out.text == "Sun on the linoleum."
    narrate_prompt = patch_get_client.text.await_args.args[0]
    assert "She set the kettle on." in narrate_prompt
    assert "Late autumn." in narrate_prompt

    illustrate_prompt = patch_get_client.image.await_args.args[0]
    assert "Sun on the linoleum." in illustrate_prompt


async def test_lavender_uses_gpt_4o_and_film_noir_by_default(patch_get_client):
    patch_get_client.text.return_value = "the room held its breath"
    patch_get_client.image.return_value = ImageBlob(url="https://x.com/i.png")

    await run_storyteller("lavender", {"previous_text": "She set the kettle."})

    assert patch_get_client.text.await_args.kwargs["model"] == "gpt-4o"
    image_prompt = patch_get_client.image.await_args.args[0]
    # film_noir style is prepended to the source (frame_text)
    assert "film noir" in image_prompt
    assert "the room held its breath" in image_prompt


async def test_lavender_with_charcoal_override_recreates_tamarisk(patch_get_client):
    patch_get_client.text.return_value = "wind off the marsh"
    patch_get_client.image.return_value = ImageBlob(url="https://x.com/i.png")

    await run_storyteller(
        "lavender",
        {"previous_text": "earlier"},
        illustrator_override="charcoal_abstract",
    )
    image_prompt = patch_get_client.image.await_args.args[0]
    assert "watercolor" in image_prompt or "charcoal" in image_prompt.lower()


async def test_narcissus_returns_image_only(patch_get_client):
    patch_get_client.analyze_image.return_value = "blue light, single chair"
    patch_get_client.image.return_value = ImageBlob(url="https://x.com/i.png")

    out = await run_storyteller(
        "narcissus", {"source_image": ImageBlob(url="https://x.com/src.png")}
    )

    assert out.text is None
    assert out.image is not None
    # Narcissus's period_photo illustrator received the analyze_image output
    image_prompt = patch_get_client.image.await_args.args[0]
    assert "blue light, single chair" in image_prompt


async def test_echo_transcribes_audio_then_narrates(patch_get_client):
    patch_get_client.transcribe.return_value = "I left the door open for the rain."
    patch_get_client.text.return_value = "Mara watched the water cross the sill."
    patch_get_client.image.return_value = ImageBlob(url="https://x.com/i.png")

    out = await run_storyteller("echo", {"source_audio": AudioBlob(data=b"OggS", format="webm")})

    assert out.text == "Mara watched the water cross the sill."
    assert out.image is not None
    patch_get_client.transcribe.assert_awaited_once()
    # The transcript reaches the narration prompt.
    narrate_prompt = patch_get_client.text.await_args.args[0]
    assert "I left the door open for the rain." in narrate_prompt


async def test_transcribe_missing_input_raises(patch_get_client):
    with pytest.raises(MissingVariable, match="source_audio"):
        await run_storyteller("echo", inputs={})


async def test_transcribe_input_must_be_audio_blob(patch_get_client):
    with pytest.raises(StorytellerSchemaError, match="must be an AudioBlob"):
        await run_storyteller("echo", {"source_audio": "not audio"})


async def test_generate_video_dispatches_to_client(patch_get_client):
    patch_get_client.video.return_value = VideoBlob(url="https://x.com/v.mp4", duration_seconds=4.0)
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
    storyteller = Storyteller._from_dict(yaml_dict)
    out = await storyteller.run({"topic": "a long shore"})
    assert out.video is not None
    patch_get_client.video.assert_awaited_once()
    assert patch_get_client.video.await_args.args[0] == "a long shore"


async def test_analyze_image_missing_input_raises(patch_get_client):
    # Narcissus is the in-tree storyteller with an analyze_image step;
    # source_image is required.
    with pytest.raises(MissingVariable, match="source_image"):
        await run_storyteller("narcissus", inputs={})


async def test_analyze_image_input_must_be_image_blob(patch_get_client):
    with pytest.raises(StorytellerSchemaError, match="must be an ImageBlob"):
        await run_storyteller("narcissus", {"source_image": "not an image"})


async def test_missing_required_step_field_raises(patch_get_client):
    yaml_dict = {
        "name": "broken",
        "steps": [{"generate_text": {"provider": "openai", "out": "x"}}],
    }
    storyteller = Storyteller._from_dict(yaml_dict)
    with pytest.raises(StorytellerSchemaError, match="requires field 'model'"):
        await storyteller.run({})


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
    storyteller = Storyteller._from_dict(yaml_dict)
    with pytest.raises(StorytellerSchemaError, match="prompt template not found"):
        await storyteller.run({})


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
    out = await Storyteller._from_dict(yaml_dict).run({"who": "world"})
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
    out = await Storyteller._from_dict(yaml_dict).run({"a": "1", "b": "2"})
    assert out.text == "1 + 2 = sum"
