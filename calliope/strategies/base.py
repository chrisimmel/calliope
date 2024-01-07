from abc import ABCMeta, abstractmethod
from datetime import datetime, timezone
from statistics import mode
from typing import Any, cast, Dict, Optional, Sequence

import httpx

from calliope.models import (
    FramesRequestParamsModel,
    FullLocationMetadata,
    KeysModel,
)
from calliope.models.frame_sequence_response import StoryFrameSequenceResponseModel
from calliope.storage.state_manager import put_story
from calliope.tables import (
    Image,
    ModelConfig,
    PromptTemplate,
    SparrowState,
    Story,
    StoryFrame,
    StrategyConfig,
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
        image_analysis: Optional[Dict[str, Any]],
        location_metadata: FullLocationMetadata,
        strategy_config: StrategyConfig,
        keys: KeysModel,
        sparrow_state: SparrowState,
        story: Story,
        httpx_client: httpx.AsyncClient,
    ) -> StoryFrameSequenceResponseModel:
        """
        Generates, stores, and returns a new sequence of story frames based on API
        parameters, the sparrow state, and the story context. This is the core method
        of every story strategy.

        Args:
            parameters: the parsed API parameters.
            image_analysis: the analysis of the input image, if any.
            strategy_config: the persisted configuration of the strategy.
            keys: API keys and secrets.
            sparrow_state: the persisted Sparrow (client) state.
            story: the story up to now.
            httpx_client: the async HTTP session.

        Returns:
            A sequence of new frames that have been added to the story.
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

        Args:
            story: the story up to now.
            image: the image for this frame, if any.
            text: the text for this frame, if any.
            frame_number: the sequence number of this frame.
            debug_data: any debug data to be logged with the frame.
            errors: any non-fatal errors that occurred while generating the frame.

        Returns:
            the new frame.
        """
        if image:
            image.date_updated = datetime.now(timezone.utc)
            await image.save().run()
        frame = StoryFrame(
            story=story.id,  # type: ignore[attr-defined]
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
        self,
        parameters: FramesRequestParamsModel,
        strategy_config: StrategyConfig,
        situation: str,
    ) -> Dict[str, Any]:
        """
        Composes the default dictionary of debug data for a frame request.
        Strategies are encouraged to enhance this dictionary with their own
        supplemental data.

        Args:
            parameters: the parsed API parameters.

        Returns:
            a dictionary with the default debug data.
        """
        text_to_text_model_config = cast(
            ModelConfig, strategy_config.text_to_text_model_config
        )
        text_to_image_model_config = cast(
            ModelConfig, strategy_config.text_to_image_model_config
        )
        prompt_template = (
            cast(PromptTemplate, text_to_text_model_config.prompt_template)
            if text_to_text_model_config else None
        )

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
            "situation": situation,
            "strategy_config": strategy_config.slug,
            "text_to_text_model_config": (
                text_to_text_model_config.slug if text_to_text_model_config else None
            ),
            "text_to_image_model_config": (
                text_to_image_model_config.slug if text_to_image_model_config else None
            ),
            "prompt_template": prompt_template.slug if prompt_template else None,
        }

    async def get_seed_prompt(self, strategy_config: StrategyConfig) -> str:
        if strategy_config.seed_prompt_template:
            if isinstance(strategy_config.seed_prompt_template, int):
                strategy_config.seed_prompt_template = (
                    await strategy_config.get_related(
                        StrategyConfig.seed_prompt_template
                    )
                )
            return cast(str, strategy_config.seed_prompt_template.text or "")

        return ""
