import re
import sys, traceback
from typing import List

import aiohttp

from calliope.inference import (
    caption_to_prompt,
    image_analysis_inference,
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
class ContinuousStoryV0Strategy(StoryStrategy):
    """
    Tries to keep a story going, carrying context from a previous frame, if any,
    to a new frame. This works in the manner of an "Exquisite Corpse" exercise,
    where each generation blindly adds something new to the story, based only on
    the step immediately precedent.

    This is largely tuned for the EleutherAI/gpt-neo-2.7B model, so uses very short
    text fragments.

    Returns a single frame.
    """

    strategy_name = "continuous_v0"

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

        output_image_style = (
            parameters.output_image_style or "A dreamy watercolor, paper texture."
        )
        debug_data = self._get_default_debug_data(parameters)
        errors = []
        caption = ""
        prompt = None
        text = None
        image = None

        if parameters.input_image_filename:
            # caption = "Along the riverrun"
            try:
                """
                caption = await image_file_to_text_inference(
                    aiohttp_session,
                    parameters.input_image_filename,
                    inference_model_configs,
                    keys,
                )
                """
                analysis = await image_analysis_inference(
                    aiohttp_session,
                    parameters.input_image_filename,
                    inference_model_configs,
                    keys,
                )
                caption = analysis.get("description")
                debug_data["i_see"] = caption

            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))

        input_text = ""

        if parameters.input_text:
            if caption:
                input_text = f"{caption}. {parameters.input_text}"
            else:
                input_text = parameters.input_text

        last_text = story.text
        if last_text:
            last_text_tokens = story.text.split()
            # last_text_tokens = last_text_tokens[int(len(last_text_tokens) / 2) :]
            last_text_tokens = last_text_tokens[-20:]
            last_text = " ".join(last_text_tokens)

        text = f"{input_text} {last_text}"
        print(f'Text prompt: "{text}"')
        if text and not text.isspace():
            text_1 = await self._get_new_story_fragment(
                text, parameters, inference_model_configs, keys, errors, aiohttp_session
            )
            print(f"{text_1=}")
            text_2 = await self._get_new_story_fragment(
                text_1,
                parameters,
                inference_model_configs,
                keys,
                errors,
                aiohttp_session,
            )
            print(f"{text_2=}")
            text_3 = await self._get_new_story_fragment(
                text_2,
                parameters,
                inference_model_configs,
                keys,
                errors,
                aiohttp_session,
            )
            print(f"{text_3=}")
            text = text_1 + " " + text_2 + " " + text_3 + " "

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
                image = get_image_attributes(output_image_filename)
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
        parameters: FramesRequestParamsModel,
        inference_model_configs: InferenceModelConfigsModel,
        keys: KeysModel,
        errors: List[str],
        aiohttp_session: aiohttp.ClientSession,
    ) -> str:
        fragment_len = len(text)
        print(f'_get_new_story_fragment: "{text=}"')

        try:
            text = await text_to_extended_text_inference(
                aiohttp_session, text, inference_model_configs, keys
            )
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            errors.append(str(e))

        text = text[fragment_len:]

        input_text = parameters.input_text

        if input_text and text.find(input_text) >= 0:
            msg = f"Rejecting story continuation because it contains the input text: {text}\n{input_text=}"
            print(msg)
            errors.append(msg)
            text = ""
        elif re.search(r"[<>#^#\\{}]|0x|://", text):
            msg = f"Rejecting story continuation because it smells like code: {text}"
            print(msg)
            errors.append(msg)
            text = ""
        else:
            text = " ".join(text.split(" "))
            text = text.replace("*", "")
            text = text.replace("_", "")
            text = text.replace("�", "'")
            text = text.strip()

        return text
