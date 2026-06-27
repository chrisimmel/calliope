"""Storyteller error types.

Some are re-exports of shared pipeline errors so callers can ``except`` a
single type regardless of which pipeline (Storyteller or Illustrator) raised
it. Storyteller-specific errors carry the storyteller name in messages for
clearer diagnosis.
"""

from calliope2.pipeline import (
    MissingVariable,
    PipelineSchemaError,
    UnknownStepType,
)


class StorytellerError(Exception):
    """Base error for the storyteller runtime."""


class UnknownStoryteller(StorytellerError):
    """Raised when a named storyteller has no YAML definition."""


class StorytellerSchemaError(StorytellerError, PipelineSchemaError):
    """Raised when a storyteller YAML is missing required fields or has invalid shape."""


__all__ = [
    "MissingVariable",
    "StorytellerError",
    "StorytellerSchemaError",
    "UnknownStepType",
    "UnknownStoryteller",
]
