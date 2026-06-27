"""The `use_illustrator` step type — Storyteller composition with Illustrators.

Resolution order tested:
  1. params['name'] (pins the illustrator)
  2. illustrator_override passed to run()
  3. storyteller's `illustrator:` default
  4. raise StorytellerSchemaError if none of the above
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from calliope2.illustrators import Illustrator, UnknownIllustrator
from calliope2.inference import ImageBlob
from calliope2.storytellers import Storyteller, StorytellerSchemaError


@pytest.fixture
def mock_client() -> MagicMock:
    c = MagicMock()
    c.text = AsyncMock()
    c.image = AsyncMock()
    return c


@pytest.fixture
def patch_get_client(monkeypatch, mock_client):
    monkeypatch.setattr("calliope2.pipeline.get_client", lambda _name: mock_client)
    return mock_client


@pytest.fixture
def patch_illustrator_load(monkeypatch):
    """Stub Illustrator.load to return whichever illustrator name was asked for.

    Returns a recorder dict so tests can assert which name was loaded.
    """
    loaded: dict[str, str] = {"last": ""}

    def fake_load(name: str) -> Illustrator:
        loaded["last"] = name
        return Illustrator._from_dict(
            {
                "name": name,
                "description": f"fake {name}",
                "outputs": "image",
                "inputs": {"required": ["source"]},
                "style": f"{name}-style,",
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

    monkeypatch.setattr(Illustrator, "load", staticmethod(fake_load))
    return loaded


# ----- Resolution order -----


async def test_default_illustrator_is_used_when_step_omits_name(
    patch_get_client, patch_illustrator_load
):
    patch_get_client.text.return_value = "a quiet kitchen"
    patch_get_client.image.return_value = ImageBlob(url="https://x/i.png")

    s = Storyteller._from_dict(
        {
            "name": "demo",
            "illustrator": "film_noir",
            "steps": [
                {
                    "generate_text": {
                        "provider": "openai",
                        "model": "gpt-4o",
                        "prompt": "write something",
                        "out": "frame_text",
                    }
                },
                {
                    "use_illustrator": {
                        "inputs": {"source": "{{ frame_text }}"},
                        "out": "frame_image",
                    }
                },
            ],
            "output": {"text": "frame_text", "image": "frame_image"},
        }
    )
    out = await s.run({})
    assert out.text == "a quiet kitchen"
    assert isinstance(out.image, ImageBlob)
    assert patch_illustrator_load["last"] == "film_noir"
    # Source was rendered with the frame_text in scope
    assert "a quiet kitchen" in patch_get_client.image.await_args.args[0]


async def test_request_override_beats_default(patch_get_client, patch_illustrator_load):
    patch_get_client.text.return_value = "x"
    patch_get_client.image.return_value = ImageBlob(url="https://x/i.png")

    s = Storyteller._from_dict(
        {
            "name": "demo",
            "illustrator": "film_noir",
            "steps": [
                {
                    "generate_text": {
                        "provider": "openai", "model": "m", "prompt": "x",
                        "out": "frame_text",
                    }
                },
                {
                    "use_illustrator": {
                        "inputs": {"source": "{{ frame_text }}"},
                        "out": "frame_image",
                    }
                },
            ],
            "output": {"image": "frame_image"},
        }
    )
    await s.run({}, illustrator_override="charcoal_abstract")
    assert patch_illustrator_load["last"] == "charcoal_abstract"


async def test_pinned_name_in_step_beats_override(patch_get_client, patch_illustrator_load):
    patch_get_client.image.return_value = ImageBlob(url="https://x/i.png")

    s = Storyteller._from_dict(
        {
            "name": "demo",
            "illustrator": "film_noir",
            "steps": [
                {
                    "use_illustrator": {
                        "name": "period_photo",   # pinned in YAML
                        "inputs": {"source": "x"},
                        "out": "frame_image",
                    }
                }
            ],
            "output": {"image": "frame_image"},
        }
    )
    await s.run({}, illustrator_override="ignored")
    assert patch_illustrator_load["last"] == "period_photo"


async def test_no_default_no_override_no_pin_raises(patch_get_client, patch_illustrator_load):
    s = Storyteller._from_dict(
        {
            "name": "demo",
            "steps": [
                {
                    "use_illustrator": {
                        "inputs": {"source": "x"},
                        "out": "frame_image",
                    }
                }
            ],
            "output": {"image": "frame_image"},
        }
    )
    with pytest.raises(StorytellerSchemaError, match="no illustrator name"):
        await s.run({})


async def test_unknown_illustrator_surfaces_as_unknown_illustrator(monkeypatch, patch_get_client):
    def fake_load(name: str):
        raise UnknownIllustrator(f"no such: {name}")

    monkeypatch.setattr(Illustrator, "load", staticmethod(fake_load))

    s = Storyteller._from_dict(
        {
            "name": "demo",
            "illustrator": "missing",
            "steps": [
                {
                    "use_illustrator": {
                        "inputs": {"source": "x"},
                        "out": "frame_image",
                    }
                }
            ],
            "output": {"image": "frame_image"},
        }
    )
    with pytest.raises(UnknownIllustrator, match="missing"):
        await s.run({})


# ----- Input shape -----


async def test_inputs_must_be_dict(patch_get_client, patch_illustrator_load):
    s = Storyteller._from_dict(
        {
            "name": "demo",
            "illustrator": "x",
            "steps": [
                {
                    "use_illustrator": {
                        "inputs": "not a dict",
                        "out": "frame_image",
                    }
                }
            ],
            "output": {"image": "frame_image"},
        }
    )
    with pytest.raises(StorytellerSchemaError, match="`inputs` must be a dict"):
        await s.run({})


async def test_inputs_strings_are_jinja_rendered(patch_get_client, patch_illustrator_load):
    patch_get_client.image.return_value = ImageBlob(url="https://x/i.png")
    s = Storyteller._from_dict(
        {
            "name": "demo",
            "illustrator": "x",
            "steps": [
                {
                    "set": {
                        "value": "rendered string",
                        "out": "var",
                    }
                },
                {
                    "use_illustrator": {
                        "inputs": {"source": "the value is {{ var }}"},
                        "out": "frame_image",
                    }
                },
            ],
            "output": {"image": "frame_image"},
        }
    )
    await s.run({})
    # The illustrator's image prompt is "<style> <source>". The source param
    # we set was a Jinja template referencing `var`; the rendered value is
    # what makes it through into the illustrator.
    rendered = patch_get_client.image.await_args.args[0]
    assert "the value is rendered string" in rendered
