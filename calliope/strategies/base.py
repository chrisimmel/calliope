from abc import ABCMeta, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence

import aiohttp

from calliope.models import (
    FramesRequestParamsModel,
    KeysModel,
    InferenceModelConfigsModel,
)
from calliope.models.frame_sequence_response import StoryFrameSequenceResponseModel
from calliope.storage.state_manager import put_story
from calliope.tables import (
    Image,
    SparrowState,
    Story,
    StoryFrame,
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
        sparrow_state: SparrowState,
        story: Story,
        aiohttp_session: aiohttp.ClientSession,
    ) -> StoryFrameSequenceResponseModel:
        """
        Requests a sequence of story frames.
        """

    async def _add_frame(
        self,
        story: Story,
        image: Optional[Image],
        text: Optional[str],
        frame_number: int,
        debug_data: Dict[str, Any],
        errors: Sequence[str],
    ) -> StoryFrame:
        """
        Adds a new frame to a story and persists everything.
        """
        if image:
            image.date_updated = datetime.now(timezone.utc)
            await image.save().run()
        frame = StoryFrame(
            story=story.id,
            number=frame_number,
            image=image,
            source_image=image,
            text=text,
            min_duration_seconds=DEFAULT_MIN_DURATION_SECONDS,
            metadata={
                **debug_data,
                "errors": errors,
            },
        )
        frame.date_updated = datetime.now(timezone.utc)
        await frame.save().run()

        story_updated = False
        if not story.title:
            story.title = await story.compute_title()
            print(f"Computed story title: '{story.title}'")
            story_updated = True

        if not story.thumbnail_image:
            thumbnail_image = await story.compute_thumbnail()
            # This doesn't actually generate a new image file, so we don't need
            # to push an image to GCS.
            if thumbnail_image:
                # But we do need to save to the database.
                await thumbnail_image.save().run()

                story.thumbnail_image = thumbnail_image
                story_updated = True
                print(f"Computed story thumbnail: '{thumbnail_image}'")

        if story_updated:
            await put_story(story)

        return frame

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
