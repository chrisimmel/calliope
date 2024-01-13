import sys
import traceback
from typing import Any, cast, Dict, List, Optional

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
    ModelConfig,
    PromptTemplate,
    SparrowState,
    Story,
    StrategyConfig,
)
from calliope.utils.file import create_sequential_filename
from calliope.utils.image import get_image_attributes
from calliope.utils.text import (
    balance_quotes,
    ends_with_punctuation,
    load_llm_output_as_json,
    split_into_sentences,
    translate_text,
)

@StoryStrategyRegistry.register()
class LavenderStrategy(StoryStrategy):
    """
    Similar to the "continuous" strategy series, but takes into account
    situational context from where the client is running: location
    time, season, weather, etc.

    Returns a single frame.
    """

    strategy_name = "lavender"

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
        print(f"Begin processing strategy {self.strategy_name}...")
        client_id = parameters.client_id
        output_image_style = parameters.output_image_style or (
            # A default image style:
            "The entire image must be a watercolor on paper. "
            "We should see washes of the watercolor paint and the texture of the paper. "
            "Prefer abstraction and softer colors or grayscale. Avoid photorealism. "
            "No signature. Don't sign the painting."
        )

        situation = get_local_situation_text(
            image_analysis, location_metadata
        )
        debug_data = self._get_default_debug_data(
            parameters, strategy_config, situation
        )
        errors: List[str] = []
        prompt = None
        image = None

        frame_number = await story.get_num_frames()

        # Get some recent text.
        last_text = await story.get_text(-3)
        if not last_text or last_text.isspace():
            last_text = await self.get_seed_prompt(strategy_config)

        last_text = (last_text.strip() + " ") if last_text else ""
        print(f"{last_text=}")

        prompt = self._compose_prompt(
            parameters,
            story,
            last_text,
            situation,
            image_analysis,
            strategy_config,
            debug_data,
        )

        # print(f'Text prompt: "{prompt}"')
        story_continuation: Optional[str] = await self._get_new_story_fragment(
            prompt,
            parameters,
            strategy_config,
            keys,
            errors,
            story,
            last_text,
            httpx_client,
        )

        if not story_continuation or story_continuation.isspace():
            # Allow one retry, augmenting the prompt with the seed prompt.
            prompt += " " + await self.get_seed_prompt(strategy_config)

            story_continuation = await self._get_new_story_fragment(
                prompt,
                parameters,
                strategy_config,
                keys,
                errors,
                story,
                last_text,
                httpx_client,
            )

        image_description = None
        state_props = {}
        if story_continuation and not story_continuation.isspace():
            print(f"{story_continuation=}")
            continuation_json = load_llm_output_as_json(story_continuation)
            print(f"{continuation_json=}")
            if continuation_json:
                story_continuation = cast(
                    Optional[str], continuation_json.get("continuation")
                )
                image_description = cast(
                    Optional[str], continuation_json.get("illustration")
                )
                state_props = {key: val for key, val in continuation_json if key not in ("continuation", "illustration")}

        if not story_continuation or story_continuation.isspace():
            story_continuation = situation + "\n"

        if not image_description:
            image_description = story_continuation
            if (
                strategy_config.text_to_text_model_config
                and strategy_config.text_to_text_model_config
                and strategy_config.text_to_text_model_config.prompt_template
                and strategy_config.text_to_text_model_config.prompt_template.target_language  # noqa: E501
                != "en"
            ):
                # Translate the story to English before
                # sending as an image prompt.
                image_description = translate_text("en", image_description)

        if image_description:
            # Generate an image for the frame, composing a prompt from
            # the frame's text...

            image_prompt = output_image_style + " " + image_description
            print(f'Image prompt: "{image_prompt}"')

            for _ in range(2):
                # Allow a retry.
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
                    print(f"Wrote image to file {output_image_filename}.")
                    image = get_image_attributes(output_image_filename)
                    print(f"Image: {image}.")
                    break
                except Exception as e:
                    traceback.print_exc(file=sys.stderr)
                    errors.append(str(e))

        # Append and persist the frame to the story.
        frame = await self._add_frame(
            story,
            image,
            story_continuation,
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

    def _compose_prompt(
        self,
        parameters: FramesRequestParamsModel,
        story: Story,
        last_text: Optional[str],
        situation: str,
        image_analysis: Optional[Dict[str, Any]],
        strategy_config: StrategyConfig,
        debug_data: Dict[str, Any],
    ) -> str:
        if last_text:
            last_text_lines = last_text.split("\n")
            last_text_lines = last_text_lines[-8:]
            last_text = "\n".join(last_text_lines)
        else:
            # If there is no text from the existing story,
            # fall back to either the input_text parameter
            # or the seed prompt, in that order of preference.
            last_text = parameters.input_text or (
                strategy_config.seed_prompt_template
                and strategy_config.seed_prompt_template.text
            )
            debug_data["applied_seed_prompt"] = last_text

        if not last_text:
            last_text = ""

        if image_analysis:
            image_scene = image_analysis.get("all_captions") or ""
            image_objects = ""  # image_analysis.get("all_tags_and_objects") or ""
            image_text = image_analysis.get("text") or ""
        else:
            image_scene = ""
            image_objects = ""
            image_text = ""

        model_config = (
            cast(ModelConfig, strategy_config.text_to_text_model_config)
            if strategy_config
            else None
        )
        prompt_template = (
            cast(PromptTemplate, model_config.prompt_template) if model_config else None
        )

        if prompt_template:
            debug_data["prompt_template"] = prompt_template.slug
            prompt = prompt_template.render(
                {
                    "poem": last_text,
                    "scene": image_scene,
                    "text": image_text,
                    "objects": image_objects,
                    "situation": situation,
                }
            )
        else:
            debug_data["prompt_template"] = None
            prompt = last_text + "\n" + situation

        return prompt

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
        try:
            print(f"Model input: '{text}'")
            text = await text_to_text_inference(
                httpx_client, text, strategy_config.text_to_text_model_config, keys
            )
            print(f"Raw output: '{text}'")

            if text:
                LIMIT = 1024

                if len(text) > LIMIT:
                    text_parts = text.split()
                    text = ""
                    for part in text_parts:
                        # if ends_with_punctuation(part):
                        #    text += part + "\n"
                        # else:
                        text += part + " "

                        if len(text) > LIMIT:
                            break

                lines = split_into_sentences(text)
                if len(lines) > 3:
                    # Discard the last line in order to subvert GPT-3's desire
                    # to put an ending on every episode. Also avoids final
                    # sentence fragments caused by token limit cutoff.
                    print(f"Discarding last sentence: '{lines[-1]}'")
                    lines = lines[0:-1]
                    # Adding blank lines between sentences helps break up
                    # dense text from especially GPT-4.
                    text = "\n\n".join(lines)
                    text = balance_quotes(text)
                text = text.strip()
                if not ends_with_punctuation(text):
                    text += "."

                text += "\n\n"

        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            errors.append(str(e))

        stripped_text = text.strip()
        input_text = parameters.input_text

        # Reject same things as continuous-v0. (TODO: extract this to a
        # shared utility.)
        if input_text and stripped_text.find(input_text) >= 0:
            msg = (
                "Rejecting story continuation because it contains the input text: "
                f"{stripped_text[:100]}[...]"
            )
            print(msg)
            errors.append(msg)
            text = ""

        # Don't want to see fragments of the prompt in the story.
        prompt_words = ("Scene:", "Text:", "Objects:", "Continuation:")
        for prompt_word in prompt_words:
            if text.find(prompt_word) >= 0:
                msg = (
                    "Rejecting story continuation because it contains a prompt word: "
                    f"'{text}'"
                )
                print(msg)
                errors.append(msg)
                text = ""

        return text
