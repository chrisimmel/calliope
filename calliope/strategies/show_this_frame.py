import os
from typing import Any, Dict, List, Optional

import aiohttp
from fastapi import HTTPException

from calliope.intel.location import get_local_situation_text
from calliope.models import (
    FramesRequestParamsModel,
    FullLocationMetadata,
    KeysModel,
)
from calliope.models.frame_sequence_response import StoryFrameSequenceResponseModel
from calliope.strategies.base import StoryStrategy
from calliope.strategies.registry import StoryStrategyRegistry
from calliope.tables import (
    SparrowState,
    Story,
    StrategyConfig,
)
from calliope.utils.google import get_media_file, is_google_cloud_run_environment
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class ShowThisFrameStrategy(StoryStrategy):
    """
    A strategy that simply shows a single frame with given image and text.
    """

    strategy_name = "show-this-frame"

    async def get_frame_sequence(
        self,
        parameters: FramesRequestParamsModel,
        image_analysis: Optional[Dict[str, Any]],
        location_metadata: FullLocationMetadata,
        strategy_config: StrategyConfig,
        keys: KeysModel,
        sparrow_state: SparrowState,
        story: Story,
        aiohttp_session: aiohttp.ClientSession,
    ) -> StoryFrameSequenceResponseModel:
        situation = get_local_situation_text(
            image_analysis, location_metadata
        )
        debug_data = self._get_default_debug_data(
            parameters, strategy_config, situation
        )
        errors: List[str] = []

        if parameters.input_image_filename:
            self._get_file(parameters.input_image_filename)
            image = get_image_attributes(parameters.input_image_filename)
        else:
            image = None

        text = parameters.input_text or ""

        frames = await story.get_frames(max_frames=-1, include_images=True)
        last_frame = frames[0] if frames and len(frames) else None
        if not last_frame or last_frame.image != image or last_frame.text != text:
            # Create a new frame only if it differs from the story's last frame.
            frame_number = await story.get_num_frames()
            text = text + "\n"
            frame = await self._add_frame(
                story,
                image,
                text,
                frame_number,
                debug_data,
                errors,
            )
        else:
            frame = last_frame

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
