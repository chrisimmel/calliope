"""YAML-declared story storytellers.

One runtime class executes any storyteller; specific behaviors are declared in
``defs/<name>.yaml`` and prompts in ``prompts/<name>/*.j2``.
"""

from calliope2.storytellers.errors import (
    MissingVariable,
    StorytellerError,
    StorytellerSchemaError,
    UnknownStepType,
    UnknownStoryteller,
)
from calliope2.storytellers.registry import list_storytellers
from calliope2.storytellers.runtime import FrameOutput, Storyteller, run_storyteller

__all__ = [
    "FrameOutput",
    "MissingVariable",
    "Storyteller",
    "StorytellerError",
    "StorytellerSchemaError",
    "UnknownStepType",
    "UnknownStoryteller",
    "list_storytellers",
    "run_storyteller",
]
