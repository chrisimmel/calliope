import re
import sys
import traceback
from typing import Any, Dict, List, Optional

import httpx

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
    StrategyConfig,
)
from calliope.utils.file import create_sequential_filename
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class ContinuousStoryV0Strategy(StoryStrategy):
    """
    Tries to keep a story going, carrying context from a previous frame, if any,
    to a new frame. This works in the manner of an "Exquisite Corpse" exercise,
    where each generation blindly adds something new to the story, based only on
    the tail of the story so far.

    This is largely tuned for the EleutherAI/gpt-neo-2.7B model, so uses very short
    text fragments.

    Returns a single frame.
    """

    strategy_name = "continuous-v0"

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
        situation = get_local_situation_text(image_analysis, location_metadata)
        debug_data = self._get_default_debug_data(parameters, strategy_config, situation)
        errors: List[str] = []
        caption = image_analysis.get("description") if image_analysis else None
        text: Optional[str] = None
        image = None
        input_text = ""
        frame_number = await story.get_num_frames()
        seed_prompt = await self.get_seed_prompt(strategy_config)

        if parameters.input_text:
            if caption:
                input_text = f"{caption}. {parameters.input_text}"
            else:
                input_text = parameters.input_text

        # Get last four frames of text.
        last_text: Optional[str] = await story.get_text(-4)
        if not last_text or last_text.isspace():
            if strategy_config.seed_prompt_template:
                last_text = seed_prompt
                debug_data["applied_seed_prompt"] = last_text
            else:
                last_text = ""

        if last_text:
            last_text_tokens = last_text
            last_text_tokens = last_text_tokens[-20:]
            last_text = " ".join(last_text_tokens)

        in_text = f"{input_text} {last_text}"
        out_text = ""

        # print(f'Text prompt: "{text}"')
        if in_text and not in_text.isspace():
            # gpt-neo-2.7B produces very short text, so collect a handful
            # of its responses as the frame text.
            for i in range(5):
                try:
                    text_n = await self._get_new_story_fragment(
                        in_text + out_text,
                        parameters,
                        strategy_config,
                        keys,
                        errors,
                        story,
                        last_text,
                        httpx_client,
                    )
                    print(f"{text_n=}")
                    if text_n:
                        if len(out_text):
                            out_text += " "
                        out_text += text_n
                    else:
                        # Things seem to be broken.
                        # Reset to to the seed prompt.
                        if caption or seed_prompt:
                            in_text = caption or seed_prompt
                except Exception as e:
                    traceback.print_exc(file=sys.stderr)
                    errors.append(str(e))

        print(f"{out_text=}")
        text = out_text
        if not text or text.isspace():
            text = caption

        last_text = text

        if text:
            # Generate an image for the frame, composing a prompt from
            # the frame's text...
            image_prompt = output_image_style + " " + text
            print(f'Image prompt: "{image_prompt}"')

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

        # Append and persist the frame to the story.
        frame = await self._add_frame(
            story,
            image,
            text,
            frame_number,
            debug_data,
            errors,
        )

        # Return the new frame.
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
        strategy_config: StrategyConfig,
        keys: KeysModel,
        errors: List[str],
        story: Story,
        last_text: Optional[str],
        httpx_client: httpx.AsyncClient,
    ) -> str:
        """
        Gets a new story fragment to be used in building the frame's text.
        """
        fragment_len = len(text)
        print(f'_get_new_story_fragment: "{text=}"')

        try:
            text = await text_to_text_inference(
                httpx_client, text, strategy_config.text_to_text_model_config, keys
            )
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            errors.append(str(e))

        text = text[fragment_len:]
        stripped_text = text.strip()

        input_text = parameters.input_text

        # Filter out some basic nonsense we don't like to see in stories...
        """
        if input_text and text.find(input_text) >= 0:
            # Don't want to see the input text parroted back.
            msg = (
                "Rejecting story continuation because it contains the input text: "
                f"{stripped_text[:100]}[...]"
            )
            print(msg)
            errors.append(msg)
            text = ""
        el
        """
        if re.search(r"[<>#^#\\{}]|0x|://", text):
            # Don't want to see computer code or similar digital detritus.
            msg = (
                "Rejecting story continuation because it smells like code: "
                f"{stripped_text[:100]}[...]"
            )
            print(msg)
            errors.append(msg)
            text = ""
        elif stripped_text and last_text and stripped_text in last_text:
            # Don't want to literally repeat ourselves.
            msg = (
                "Rejecting story continuation because it's already appeared in the "
                f"story: {stripped_text[:100]}[...]"
            )
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
