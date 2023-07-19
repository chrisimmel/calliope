import re
import sys
import traceback
from typing import Any, cast, Dict, List, Optional

import aiohttp
from google.cloud import translate_v2 as translate

from calliope.inference import (
    text_to_text_inference,
    text_to_image_file_inference,
)
from calliope.models import (
    FramesRequestParamsModel,
    KeysModel,
)
from calliope.models.frame_sequence_response import StoryFrameSequenceResponseModel
from calliope.strategies.base import StoryStrategy
from calliope.strategies.registry import StoryStrategyRegistry
from calliope.tables import (
    PromptTemplate,
    SparrowState,
    Story,
)
from calliope.tables.model_config import ModelConfig, StrategyConfig
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

    strategy_name = "continuous-v1"

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
        print(f"Begin processing strategy {self.strategy_name}...")
        client_id = parameters.client_id
        output_image_style = parameters.output_image_style or (
            "The entire image must be a watercolor on paper. "
            "We should see washes of the watercolor paint and the texture of the paper. "
            "Prefer abstraction and softer colors or grayscale. Avoid photorealism. "
            "No signature. Don't sign the painting."
        )
        debug_data = self._get_default_debug_data(parameters)
        errors = []
        prompt = None
        image = None

        frame_number = await story.get_num_frames()

        if image_analysis:
            image_scene = image_analysis.get("all_captions")
            image_objects = image_analysis.get("all_tags_and_objects")
            image_text = image_analysis.get("text")
            debug_data["i_see"] = image_analysis.get("description")
        else:
            image_scene = ""
            image_objects = ""
            image_text = ""

        """
        Use input_text parameter only as the story seed, not for each frame.
        if parameters.input_text:
            if image_scene:
                image_scene = f"{image_scene}. {parameters.input_text}"
            else:
                image_scene = parameters.input_text
        """

        # Get some recent text.
        last_text = await story.get_text(-1)
        if not last_text or last_text.isspace():
            if strategy_config.seed_prompt_template:
                if isinstance(strategy_config.seed_prompt_template, int):
                    strategy_config.seed_prompt_template = (
                        await strategy_config.get_related(
                            StrategyConfig.seed_prompt_template
                        )
                    )
                last_text = strategy_config.seed_prompt_template.text
            else:
                last_text = ""

        last_text = (last_text.strip() + " ") if last_text else ""
        print(f"{last_text=}")

        prompt = self._compose_prompt(
            parameters,
            story,
            last_text,
            image_scene,
            image_text,
            image_objects,
            strategy_config,
        )

        print(f'Text prompt: "{prompt}"')
        story_continuation = await self._get_new_story_fragment(
            prompt,
            parameters,
            strategy_config,
            keys,
            errors,
            story,
            last_text,
            aiohttp_session,
        )

        if not story_continuation or story_continuation.isspace():
            # Allow one retry.
            prompt += (
                " "
                + (
                    strategy_config.seed_prompt_template
                    and strategy_config.seed_prompt_template.text
                )
                or ""
            )
            story_continuation = await self._get_new_story_fragment(
                prompt,
                parameters,
                strategy_config,
                keys,
                errors,
                story,
                last_text,
                aiohttp_session,
            )

        if not story_continuation or story_continuation.isspace():
            story_continuation = image_scene + "\n"

        if story_continuation:
            if (
                strategy_config.text_to_text_model_config
                and strategy_config.text_to_text_model_config
                and strategy_config.text_to_text_model_config.prompt_template
                and strategy_config.text_to_text_model_config.prompt_template.target_language
                != "en"
            ):
                en_story = translate_text("en", story_continuation)
            else:
                en_story = story_continuation

            image_prompt = output_image_style + " " + en_story
            print(f'Image prompt: "{image_prompt}"')

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
                output_image_filename = output_image_filename_png
                print(f"Wrote image to file {output_image_filename}.")
                image = get_image_attributes(output_image_filename)
                print(f"Image: {image}.")
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))

        frame = await self._add_frame(
            story,
            image,
            story_continuation,
            frame_number,
            debug_data,
            errors,
        )

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
        scene: str,
        text: str,
        objects: str,
        strategy_config: Optional[StrategyConfig],
    ) -> str:
        if last_text:
            last_text_lines = last_text.split("\n")
            last_text_lines = last_text_lines[-8:]
            last_text = "\n".join(last_text_lines)
        else:
            last_text = parameters.input_text or (
                strategy_config.seed_prompt_template
                and strategy_config.seed_prompt_template.text
            )

        model_config = (
            cast(ModelConfig, strategy_config.text_to_text_model_config)
            if strategy_config
            else None
        )
        prompt_template = (
            cast(PromptTemplate, model_config.prompt_template) if model_config else None
        )

        if prompt_template:
            prompt = prompt_template.render(
                {
                    "poem": last_text,
                    "scene": scene,
                    "text": text,
                    "objects": objects,
                }
            )
        else:
            prompt = last_text + "\n" + scene + "\n" + text + "\n" + objects

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
        aiohttp_session: aiohttp.ClientSession,
    ) -> str:
        try:
            text = await text_to_text_inference(
                aiohttp_session, text, strategy_config.text_to_text_model_config, keys
            )
            print(f"Raw output: '{text}'")

            def ends_with_punctuation(str):
                return len(str) and str[-1] in (
                    ".",
                    "!",
                    "?",
                    ":",
                    ",",
                    ";",
                    "-",
                    '"',
                    "'",
                )

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

                """
                lines = split_into_sentences(text)
                if len(lines) > 3:
                    # Discard the last line in order to subvert GPT-3's desire
                    # to put an ending on every episode.
                    print(f"Discarding last sentence: '{lines[-1]}'")
                    lines = lines[0:-1]
                    text = "\n".join(lines)
                """
                text = text.strip()
                if not ends_with_punctuation(text):
                    text += "."

                text += "\n\n"

        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            errors.append(str(e))

        stripped_text = text.strip()
        input_text = parameters.input_text

        if input_text and stripped_text.find(input_text) >= 0:
            msg = (
                "Rejecting story continuation because it contains the input text: "
                f"{stripped_text[:100]}[...]"
            )
            print(msg)
            errors.append(msg)
            text = ""
        elif re.search(r"[<>#^#\\{}]|0x|://", text):
            msg = (
                "Rejecting story continuation because it smells like code: "
                f"{stripped_text[:100]}[...]"
            )
            print(msg)
            errors.append(msg)
            text = ""
        elif stripped_text and stripped_text in last_text:
            msg = (
                "Rejecting story continuation because it's already appeared in the "
                f"story: {stripped_text[:100]}[...]"
            )
            print(msg)
            errors.append(msg)
            text = ""

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


def translate_text(target: str, text: str) -> str:
    """Translates text into the target language.

    Target must be an ISO 639-1 language code.
    See https://g.co/cloud/translate/v2/translate-reference#supported_languages
    """
    translate_client = translate.Client()

    if isinstance(text, bytes):
        text = text.decode("utf-8")

    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.translate(text, target_language=target)

    translation = result.get("translatedText", text) if result else text

    print("Translation: {}".format(translation))
    print("Detected source language: {}".format(result["detectedSourceLanguage"]))

    return translation
