from datetime import datetime
import os

import aiohttp
from fastapi import HTTPException

from calliope.models import (
    FramesRequestParamsModel,
    KeysModel,
    InferenceModelConfigsModel,
    SparrowStateModel,
    StoryFrameModel,
    StoryFrameSequenceResponseModel,
    StoryModel,
)
from calliope.strategies.base import DEFAULT_MIN_DURATION_SECONDS, StoryStrategy
from calliope.strategies.registry import StoryStrategyRegistry
from calliope.utils.google import get_media_file, is_google_cloud_run_environment
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class ShowThisFrameStrategy(StoryStrategy):
    """
    A strategy that simply shows a single frame with given image and text.
    """

    strategy_name = "show_this_frame"

    async def get_frame_sequence(
        self,
        parameters: FramesRequestParamsModel,
        inference_model_configs: InferenceModelConfigsModel,
        keys: KeysModel,
        sparrow_state: SparrowStateModel,
        story: StoryModel,
        aiohttp_session: aiohttp.ClientSession,
    ) -> StoryFrameSequenceResponseModel:

        debug_data = self._get_default_debug_data(parameters)
        errors = []

        if parameters.input_image_filename:
            self._get_file(parameters.input_image_filename)
            image = get_image_attributes(parameters.input_image_filename)
        else:
            image = None

        text = parameters.input_text

        frame = StoryFrameModel(
            image=image,
            source_image=image,
            text=text,
            # TODO: Parameterize min_duration_seconds for this strategy.
            min_duration_seconds=DEFAULT_MIN_DURATION_SECONDS,
            metadata={
                **debug_data,
                "errors": errors,
            },
        )
        last_frame = story.frames[-1] if len(story.frames) else None
        if (
            not last_frame
            or last_frame.image != frame.image
            or last_frame.text != frame.text
        ):
            # Add the frame to the story only if it differs from the story's last frame.
            story.frames.append(frame)
            story.text = story.text + "\n" + text

        return StoryFrameSequenceResponseModel(
            frames=[frame], debug_data=debug_data, errors=errors
        )

    def _get_file(self, filename: str) -> None:
        """
        Retrieves the file from Google Cloud Storage if needed, and verifies that it exists.
        """
        if is_google_cloud_run_environment():
            try:
                get_media_file(filename, filename)
            except Exception as e:
                raise HTTPException(
                    status_code=404, detail=f"Error retrieving file {filename}: {e}"
                )

        if not os.path.isfile(filename):
            raise HTTPException(
                status_code=404, detail=f"Media file not found: {filename}"
            )
