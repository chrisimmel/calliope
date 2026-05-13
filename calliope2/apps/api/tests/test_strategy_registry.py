"""Smoke tests for strategy discovery and load-time YAML validation."""

import pytest

from calliope2.strategies import (
    StoryStrategy,
    StrategySchemaError,
    UnknownStepType,
    UnknownStrategy,
    list_strategies,
)


def test_list_strategies_returns_all_five_canonical_names():
    assert list_strategies() == [
        "continuous_v1",
        "fern",
        "literal",
        "narcissus",
        "simple_one_frame",
    ]


@pytest.mark.parametrize("name", ["literal", "simple_one_frame", "narcissus", "fern", "continuous_v1"])
def test_each_strategy_loads(name):
    s = StoryStrategy.load(name)
    assert s.name == name
    assert s.description
    assert isinstance(s.steps, list)
    assert s.output  # every strategy declares at least one output channel


def test_load_unknown_strategy_raises():
    with pytest.raises(UnknownStrategy, match="no strategy definition"):
        StoryStrategy.load("does_not_exist")


def test_missing_name_raises():
    with pytest.raises(StrategySchemaError, match="required field 'name'"):
        StoryStrategy._from_dict({"steps": []})


def test_unknown_step_type_raises():
    with pytest.raises(UnknownStepType, match="unknown step type 'mystery'"):
        StoryStrategy._from_dict({"name": "x", "steps": [{"mystery": {}}]})


def test_multi_key_step_raises():
    with pytest.raises(StrategySchemaError, match="single-key dict"):
        StoryStrategy._from_dict(
            {"name": "x", "steps": [{"generate_text": {}, "set": {}}]}
        )
