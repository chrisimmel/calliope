"""YAML-declared story strategies.

One runtime class executes any strategy; specific behaviors are declared in
``defs/<name>.yaml`` and prompts in ``prompts/<name>/*.j2``.
"""

from calliope2.strategies.errors import (
    MissingVariable,
    StrategyError,
    StrategySchemaError,
    UnknownStepType,
    UnknownStrategy,
)
from calliope2.strategies.registry import list_strategies
from calliope2.strategies.runtime import FrameOutput, StoryStrategy, run_strategy

__all__ = [
    "FrameOutput",
    "MissingVariable",
    "StoryStrategy",
    "StrategyError",
    "StrategySchemaError",
    "UnknownStepType",
    "UnknownStrategy",
    "list_strategies",
    "run_strategy",
]
