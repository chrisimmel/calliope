import os

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
from calliope.strategies.base import StoryStrategy
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
    ) -> StoryFrameSequenceResponseModel:

        debug_data = {}
        errors = []

        if parameters.input_image_filename:
            self._get_file(parameters.input_image_filename)
            image = get_image_attributes(parameters.input_image_filename)
        else:
            image = None

        text = parameters.input_text

        frame = StoryFrameModel(
            image=image,
            text=text,
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
            base_filename = os.path.basename(filename)
            try:
                get_media_file(base_filename, filename)
            except Exception as e:
                raise HTTPException(
                    status_code=404, detail=f"Error retrieving file {filename}: {e}"
                )

        if not os.path.isfile(filename):
            raise HTTPException(
                status_code=404, detail=f"Media file not found: {filename}"
            )
