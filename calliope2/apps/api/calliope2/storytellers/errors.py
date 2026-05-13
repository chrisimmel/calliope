class StorytellerError(Exception):
    """Base error for the storyteller runtime."""


class UnknownStoryteller(StorytellerError):
    """Raised when a named storyteller has no YAML definition."""


class UnknownStepType(StorytellerError):
    """Raised when a storyteller YAML uses a step type the runtime doesn't know."""


class StorytellerSchemaError(StorytellerError):
    """Raised when a storyteller YAML is missing required fields or has invalid shape."""


class MissingVariable(StorytellerError):
    """Raised when a step references a context variable that hasn't been produced."""
