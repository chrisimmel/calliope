from datetime import datetime
import sys, traceback

import aiohttp

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


from calliope.inference import (
    image_file_to_text_inference,
    text_to_image_file_inference,
)
from calliope.utils.file import create_sequential_filename
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class LiteralStrategy(StoryStrategy):
    """
    Takes the input_text as the prompt to generate an image in a single frame. Echos back the text.
    """

    strategy_name = "literal"

    async def get_frame_sequence(
        self,
        parameters: FramesRequestParamsModel,
        inference_model_configs: InferenceModelConfigsModel,
        keys: KeysModel,
        sparrow_state: SparrowStateModel,
        story: StoryModel,
        aiohttp_session: aiohttp.ClientSession,
    ) -> StoryFrameSequenceResponseModel:
        client_id = parameters.client_id
        debug_data = self._get_default_debug_data(parameters)
        errors = []
        frames = []

        input_text = parameters.input_text

        prompts = input_text.split("|") if input_text else []

        if parameters.input_image_filename:
            try:
                caption = await image_file_to_text_inference(
                    aiohttp_session,
                    parameters.input_image_filename,
                    inference_model_configs,
                    keys,
                )
                debug_data["i_see"] = caption
                prompts.append(caption)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))

        for prompt in prompts:
            image = None

            try:
                output_image_filename_png = create_sequential_filename(
                    "media", client_id, "out", "png", story
                )
                await text_to_image_file_inference(
                    aiohttp_session,
                    prompt,
                    output_image_filename_png,
                    inference_model_configs,
                    keys,
                    parameters.output_image_width,
                    parameters.output_image_height,
                )

                output_image_filename = output_image_filename_png
                image = get_image_attributes(output_image_filename)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))

            frame = StoryFrameModel(
                image=image,
                source_image=image,
                text=prompt,
                min_duration_seconds=DEFAULT_MIN_DURATION_SECONDS,
                metadata={
                    **debug_data,
                    "errors": errors,
                },
            )
            frames.append(frame)

            story.frames.append(frame)
            story.text = story.text + "\n" + prompt

        return StoryFrameSequenceResponseModel(
            frames=frames, debug_data=debug_data, errors=errors
        )
