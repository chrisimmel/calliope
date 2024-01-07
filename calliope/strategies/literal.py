import sys
import traceback
from typing import Any, Dict, Optional

import httpx

from calliope.inference import (
    text_to_image_file_inference,
)
from calliope.intel.location import get_local_situation_text
from calliope.models import (
    FramesRequestParamsModel,
    FullLocationMetadata,
    KeysModel,
)
from calliope.models.frame_sequence_response import StoryFrameSequenceResponseModel
from calliope.strategies.base import StoryStrategy
from calliope.strategies.registry import StoryStrategyRegistry
from calliope.tables import SparrowState, Story, StrategyConfig
from calliope.utils.file import create_sequential_filename
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class LiteralStrategy(StoryStrategy):
    """
    Takes the input_text and/or input image analysis as the prompt to generate an
    output image in a single frame. Echos back the input text.

    Is useful mainly for testing image understanding and generation, or for generating
    a short, fixed frame sequence based on a sequence of input prompts separated by "|".
    """

    strategy_name = "literal"

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
        client_id = parameters.client_id
        output_image_style = (
            parameters.output_image_style or "A watercolor, paper texture."
        )
        situation = get_local_situation_text(
            image_analysis, location_metadata
        )
        debug_data = self._get_default_debug_data(
            parameters, strategy_config, situation
        )
        errors = []
        frames = []

        input_text = parameters.input_text
        prompts = input_text.split("|") if input_text else []

        if image_analysis:
            description = image_analysis.get("description")
            if description:
                prompts.append(description)
            debug_data["i_see"] = description

        for prompt in prompts:
            frame_number = await story.get_num_frames()
            image_prompt = output_image_style + " " + (prompt or "")
            print(f'Image prompt: "{image_prompt}"')

            image = None

            try:
                output_image_filename_png = create_sequential_filename(
                    "media", client_id, "out", "png", story.cuid, frame_number
                )
                await text_to_image_file_inference(
                    httpx_client,
                    image_prompt,
                    output_image_filename_png,
                    strategy_config.text_to_image_model_config,
                    keys,
                    parameters.output_image_width,
                    parameters.output_image_height,
                )

                output_image_filename = output_image_filename_png
                image = get_image_attributes(output_image_filename)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))

            text = prompt + "\n"

            frame = await self._add_frame(
                story,
                image,
                text,
                frame_number,
                debug_data,
                errors,
            )
            frames.append(frame)

        return StoryFrameSequenceResponseModel(
            frames=frames, debug_data=debug_data, errors=errors
        )
