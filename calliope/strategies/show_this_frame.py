from calliope.models import (
    FramesRequestParamsModel,
    StoryFrameModel,
    StoryFrameSequenceResponseModel,
)
from calliope.strategies.base import StoryStrategy
from calliope.strategies.registry import StoryStrategyRegistry
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class ShowThisFrameStrategy(StoryStrategy):
    """
    A strategy that simply shows a single frame with given image and text.
    """

    strategy_name = "show_this_frame"

    async def get_frame_sequence(
        self, parameters: FramesRequestParamsModel
    ) -> StoryFrameSequenceResponseModel:

        debug_data = {}
        errors = []

        image = (
            get_image_attributes(parameters.input_image_filename)
            if parameters.input_image_filename
            else None
        )
        text = parameters.input_text

        frame = StoryFrameModel(
            image=image,
            text=text,
        )

        return StoryFrameSequenceResponseModel(
            frames=[frame], debug_data=debug_data, errors=errors
        )
