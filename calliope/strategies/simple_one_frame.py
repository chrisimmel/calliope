import sys, traceback
from typing import Any, Dict, Optional

import aiohttp

from calliope.inference import (
    caption_to_prompt,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)
from calliope.models import (
    FramesRequestParamsModel,
    KeysModel,
)
from calliope.models.frame_sequence_response import StoryFrameSequenceResponseModel
from calliope.strategies.base import DEFAULT_MIN_DURATION_SECONDS, StoryStrategy
from calliope.strategies.registry import StoryStrategyRegistry
from calliope.tables import (
    SparrowState,
    Story,
)
from calliope.tables.model_config import StrategyConfig
from calliope.utils.file import create_sequential_filename
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class SimpleOneFrameStoryStrategy(StoryStrategy):
    """
    The strategy of the original /story/ endpoint.
    Returns a single frame based on input parameters. Doesn't attempt story continuation.
    """

    strategy_name = "simple-one-frame"

    async def get_frame_sequence(
        self,
        parameters: FramesRequestParamsModel,
        image_analysis: Optional[Dict[str, Any]],
        strategy_config: Optional[StrategyConfig],
        keys: KeysModel,
        sparrow_state: SparrowState,
        story: Story,
        aiohttp_session: aiohttp.ClientSession,
    ) -> StoryFrameSequenceResponseModel:
        client_id = parameters.client_id

        output_image_style = (
            parameters.output_image_style or "A watercolor, paper texture."
        )
        debug_data = self._get_default_debug_data(parameters)
        errors = []
        description = ""
        image = None
        frame_number = await story.get_num_frames()

        if image_analysis:
            description = image_analysis.get("description") if image_analysis else None
            debug_data["i_see"] = description

        if parameters.input_text:
            if description:
                description = f"{description}. {parameters.input_text}"
            else:
                description = parameters.input_text

        print(f"{description=} {strategy_config.text_to_text_model_config=}")

        text = await text_to_extended_text_inference(
            aiohttp_session, description, strategy_config.text_to_text_model_config, keys
        )
        if not text or text.isspace():
            text = description

        prompt_template = output_image_style + " {x}"
        print(text)

        if text:
            image_prompt = caption_to_prompt(text, prompt_template)

            try:
                output_image_filename_png = create_sequential_filename(
                    "media", client_id, "out", "png", story.cuid, frame_number
                )

                await text_to_image_file_inference(
                    aiohttp_session,
                    image_prompt,
                    output_image_filename_png,
                    strategy_config.text_to_image_model_config,
                    keys,
                    parameters.output_image_width,
                    parameters.output_image_height,
                )
                image = get_image_attributes(output_image_filename_png)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))

        text = text + "\n"
        frame = await self._add_frame(
            story,
            image,
            text,
            frame_number,
            debug_data,
            errors,
        )

        return StoryFrameSequenceResponseModel(
            frames=[frame], debug_data=debug_data, errors=errors
        )
