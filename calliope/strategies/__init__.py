import enum

from .base import StoryStrategy
from .continuous_v0 import ContinuousStoryV0Strategy
from .continuous_v1 import ContinuousStoryV1Strategy
from .lavender import LavenderStrategy
from .literal import LiteralStrategy
from .show_this_frame import ShowThisFrameStrategy
from .simple_one_frame import SimpleOneFrameStoryStrategy
from .registry import StoryStrategyRegistry

StrategyName = enum.Enum(
    "StrategyName",
    {name: name for name in StoryStrategyRegistry.get_all_strategy_names()},
)

__all__ = [
    "ContinuousStoryV0Strategy",
    "ContinuousStoryV1Strategy",
    "LavenderStrategy",
    "LiteralStrategy",
    "ShowThisFrameStrategy",
    "SimpleOneFrameStoryStrategy",
    "StoryStrategy",
    "StoryStrategyRegistry",
    "StrategyName",
]
