class StrategyError(Exception):
    """Base error for the strategy runtime."""


class UnknownStrategy(StrategyError):
    """Raised when a named strategy has no YAML definition."""


class UnknownStepType(StrategyError):
    """Raised when a strategy YAML uses a step type the runtime doesn't know."""


class StrategySchemaError(StrategyError):
    """Raised when a strategy YAML is missing required fields or has invalid shape."""


class MissingVariable(StrategyError):
    """Raised when a step references a context variable that hasn't been produced."""
