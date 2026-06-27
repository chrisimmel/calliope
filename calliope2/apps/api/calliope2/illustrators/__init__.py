"""YAML-declared illustrators.

A sibling to Storytellers. An Illustrator is a YAML-declared pipeline that
turns typed inputs into one media channel (image OR video). Storytellers
invoke them via the ``use_illustrator`` step. See
``docs/concepts/illustrators.md``.
"""

from calliope2.illustrators.errors import (
    IllustratorError,
    IllustratorSchemaError,
    MissingVariable,
    UnknownIllustrator,
    UnknownStepType,
)
from calliope2.illustrators.registry import list_illustrators
from calliope2.illustrators.runtime import Illustrator, run_illustrator

__all__ = [
    "Illustrator",
    "IllustratorError",
    "IllustratorSchemaError",
    "MissingVariable",
    "UnknownIllustrator",
    "UnknownStepType",
    "list_illustrators",
    "run_illustrator",
]
