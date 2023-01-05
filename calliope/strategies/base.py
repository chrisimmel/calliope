from abc import ABCMeta, abstractmethod

from calliope.models import (
    FramesRequestParamsModel,
    KeysModel,
    InferenceModelConfigsModel,
    SparrowStateModel,
    StoryFrameSequenceResponseModel,
    StoryModel,
)


# By default, we ask each frame to be displayed for at
# least 20 seconds.
DEFAULT_MIN_DURATION_SECONDS = 20


class StoryStrategy(object, metaclass=ABCMeta):
    """
    Abstract base class for classes that implement story strategies.
    """

    # The name of the strategy.
    strategy_name: str

    @abstractmethod
    async def get_frame_sequence(
        self,
        parameters: FramesRequestParamsModel,
        inference_model_configs: InferenceModelConfigsModel,
        keys: KeysModel,
        sparrow_state: SparrowStateModel,
        story: StoryModel,
    ) -> StoryFrameSequenceResponseModel:
        """
        Requests a sequence of story frames.
        """
