"""Smoke tests for storyteller discovery and load-time YAML validation."""

import pytest

from calliope2.storytellers import (
    Storyteller,
    StorytellerSchemaError,
    UnknownStepType,
    UnknownStoryteller,
    list_storytellers,
)


def test_list_storytellers_returns_canonical_names():
    # Phase 10: continuous_v1 was the precursor to fern and is dropped;
    # lavender is added as a separate text-model variant. echo is the
    # spoken-word (audio-seed) storyteller.
    assert list_storytellers() == [
        "echo",
        "fern",
        "lavender",
        "literal",
        "narcissus",
        "simple_one_frame",
    ]


@pytest.mark.parametrize(
    "name", ["literal", "simple_one_frame", "narcissus", "fern", "lavender", "echo"]
)
def test_each_storyteller_loads(name):
    s = Storyteller.load(name)
    assert s.name == name
    assert s.description
    assert isinstance(s.steps, list)
    assert s.output  # every storyteller declares at least one output channel


def test_load_unknown_storyteller_raises():
    with pytest.raises(UnknownStoryteller, match="no storyteller definition"):
        Storyteller.load("does_not_exist")


def test_missing_name_raises():
    with pytest.raises(StorytellerSchemaError, match="required field 'name'"):
        Storyteller._from_dict({"steps": []})


def test_unknown_step_type_raises():
    with pytest.raises(UnknownStepType, match="unknown step type 'mystery'"):
        Storyteller._from_dict({"name": "x", "steps": [{"mystery": {}}]})


def test_multi_key_step_raises():
    with pytest.raises(StorytellerSchemaError, match="single-key dict"):
        Storyteller._from_dict({"name": "x", "steps": [{"generate_text": {}, "set": {}}]})
