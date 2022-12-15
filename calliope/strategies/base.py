from abc import ABCMeta, abstractmethod

from calliope.models import StoryFrameSequenceResponseModel
from calliope.strategies.parameters import StoryStrategyParams


class StoryStrategy(object, metaclass=ABCMeta):
    """
    Abstract base class for classes that implement story strategies.
    """

    # The name of the strategy.
    strategy_name: str

    @abstractmethod
    async def get_frame_sequence(
        self, parameters: StoryStrategyParams
    ) -> StoryFrameSequenceResponseModel:
        """
        Requests a sequence of story frames.
        """
