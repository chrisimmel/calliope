from abc import ABCMeta, abstractmethod

from calliope.models import StoryFrameSequenceResponseModel
from calliope.strategies.parameters import StoryParameters


class StoryStrategy(object, metaclass=ABCMeta):
    """
    Abstract base class for classes that implement story strategies.
    """

    # The name of the strategy.
    strategy_name: str

    @abstractmethod
    def get_frame_sequence(
        self, parameters: StoryParameters
    ) -> StoryFrameSequenceResponseModel:
        """
        Requests a sequence of story frames.
        """
