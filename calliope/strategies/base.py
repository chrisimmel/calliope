from abc import ABCMeta, abstractmethod

from calliope.models import (
    FramesRequestParamsModel,
    KeysModel,
    InferenceModelConfigsModel,
    SparrowStateModel,
    StoryFrameSequenceResponseModel,
    StoryModel,
)


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
