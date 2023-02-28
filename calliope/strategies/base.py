from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import Any, Dict

import aiohttp

from calliope.models import (
    FramesRequestParamsModel,
    KeysModel,
    InferenceModelConfigsModel,
    SparrowStateModel,
    # StoryFrameSequenceResponseModel,
    StoryModel,
)
from calliope.models.frame_sequence_response import StoryFrameSequenceResponseModel


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
        aiohttp_session: aiohttp.ClientSession,
    ) -> StoryFrameSequenceResponseModel:
        """
        Requests a sequence of story frames.
        """

    def _get_default_debug_data(
        self, parameters: FramesRequestParamsModel
    ) -> Dict[str, Any]:
        return {
            "parameters": {
                key: value
                for key, value in parameters.dict(exclude_none=True).items()
                # Filter out some undesirable parameters:
                if key
                not in (
                    "client_id",
                    "input_audio",
                    "input_audio_filename",
                    "input_image",
                    "input_image_filename",
                )
                and value
            },
            "generated_at": str(datetime.utcnow()),
        }
