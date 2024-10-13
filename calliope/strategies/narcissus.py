import sys
import traceback
from typing import Any, Dict, List, Optional

import httpx
from rich import print

from calliope.inference import (
    text_to_text_inference,
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
from calliope.tables import (
    SparrowState,
    Story,
)
from calliope.tables.model_config import StrategyConfig
from calliope.utils.file import create_sequential_filename
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class NarcissusStrategy(StoryStrategy):
    """
    A distorting mirror. Creates an image directly from the description of the input text.
    Returns no text.
    """

    strategy_name = "narcissus"

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

        print(f"{parameters=}")
        output_image_style = (
            parameters.output_image_style or "A watercolor, paper texture."
        )
        situation = get_local_situation_text(image_analysis, location_metadata)
        debug_data = self._get_default_debug_data(parameters, strategy_config, situation)
        errors: List[str] = []
        description = ""
        image = None
        frame_number = await story.get_num_frames()
        if not story.title:
            story.title = "This is You"

        if image_analysis:
            description = image_analysis.get("description") or ""
            debug_data["i_see"] = description

        if parameters.input_text:
            if description:
                description = f"{description}. {parameters.input_text}"
            else:
                description = parameters.input_text
        if not description:
            description = situation

        print(f"{description=} {strategy_config.text_to_text_model_config=}")

        text = description
        if text:
            image_prompt = output_image_style + " " + text
            print(f"Image prompt: {image_prompt}")

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
                image = get_image_attributes(output_image_filename_png)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))

        text = text + "\n"
        frame = await self._add_frame(
            story,
            image,
            "",  # text,
            frame_number,
            debug_data,
            errors,
        )

        return StoryFrameSequenceResponseModel(
            frames=[frame], debug_data=debug_data, errors=errors
        )
