from calliope2.pipeline import (
    MissingVariable,
    PipelineSchemaError,
    UnknownStepType,
)


class IllustratorError(Exception):
    """Base error for the illustrator runtime."""


class UnknownIllustrator(IllustratorError):
    """Raised when a named illustrator has no YAML definition."""


class IllustratorSchemaError(IllustratorError, PipelineSchemaError):
    """Raised when an illustrator YAML is missing required fields or has invalid shape."""


# Re-exported so callers can import everything from one place.
__all__ = [
    "IllustratorError",
    "IllustratorSchemaError",
    "MissingVariable",
    "UnknownIllustrator",
    "UnknownStepType",
]
