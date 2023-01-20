from datetime import datetime
import sys, traceback
from typing import List

import aiohttp

from calliope.inference import (
    caption_to_prompt,
    image_file_to_text_inference,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)
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
from calliope.utils.file import create_sequential_filename
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class ContinuousStoryV1Strategy(StoryStrategy):
    """
    Tries to keep a story going, carrying context from a previous frame, if any,
    to a new frame. This works in the manner of an "Exquisite Corpse" exercise,
    where each generation blindly adds something new to the story, based only on
    the step immediately precedent.

    Spread our wings and try larger prompts tuned for GPT-3.

    Returns a single frame.
    """

    strategy_name = "continuous_v1"

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

        output_image_style = parameters.output_image_style or "A watercolor of"
        debug_data = self._get_default_debug_data(parameters)
        errors = []
        caption = ""
        prompt = None
        text = None
        image = None

        if parameters.input_image_filename:
            caption = "Along the riverrun"
            try:
                caption = await image_file_to_text_inference(
                    aiohttp_session,
                    parameters.input_image_filename,
                    inference_model_configs,
                    keys,
                )
                debug_data["i_see"] = caption
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))
        if parameters.input_text:
            if caption:
                caption = f"{caption}. {parameters.input_text}"
            else:
                caption = parameters.input_text

        last_text = story.text
        if last_text:
            last_text_tokens = story.text.split()
            # last_text_tokens = last_text_tokens[int(len(last_text_tokens) / 2) :]
            last_text_tokens = last_text_tokens[-500:]
            last_text = " ".join(last_text_tokens)

            text = f"Continue this story about {caption}: {last_text}"
        else:
            text = f"Begin a long, dreamy, bittersweet story about '{caption}'"

        print(f'Text prompt: "{text}"')
        text = (
            await self._get_new_story_fragment(
                text,
                inference_model_configs,
                keys,
                errors,
                aiohttp_session,
            )
            + " "
        )

        if not text or text.isspace():
            text = caption

        last_text = text

        if text:
            prompt_template = output_image_style + " {x}"
            prompt = caption_to_prompt(text, prompt_template)
            print(f'Image prompt: "{prompt}"')

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
                print(f"Wrote image to file {output_image_filename}.")
                image = get_image_attributes(output_image_filename)
                print(f"Image: {image}.")
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))

        frame = StoryFrameModel(
            image=image,
            source_image=image,
            text=text,
            min_duration_seconds=DEFAULT_MIN_DURATION_SECONDS,
            metadata={
                **debug_data,
                "errors": errors,
            },
        )
        story.frames.append(frame)
        story.text = story.text + text

        return StoryFrameSequenceResponseModel(
            frames=[frame],
            debug_data=debug_data,
            errors=errors,
            append_to_prior_frames=True,
        )

    async def _get_new_story_fragment(
        self,
        text: str,
        inference_model_configs,
        keys: KeysModel,
        errors: List[str],
        aiohttp_session: aiohttp.ClientSession,
    ) -> str:
        try:
            text = await text_to_extended_text_inference(
                aiohttp_session, text, inference_model_configs, keys
            )
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            errors.append(str(e))
        # text = " ".join(text.split(" "))
        # text = text.strip()

        return text
