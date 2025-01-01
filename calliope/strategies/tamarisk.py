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
    InferenceModel,
    ModelConfig,
    PromptTemplate,
    SparrowState,
    Story,
    StrategyConfig,
)
from calliope.utils.file import create_sequential_filename
from calliope.utils.image import get_image_attributes
from calliope.utils.text import translate_text


@StoryStrategyRegistry.register()
class TamariskStrategy(StoryStrategy):
    """
    An evolution of the continuous-v0 strategy, specifically based on the Lichen variant,
    using gpt-4o to tidy up the results from EleutherAI/gpt-neo-2.7B.

    Returns a single frame.
    """

    strategy_name = "tamarisk"

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
        # TODO: Because of tiny model context window, use a short, one-sentence
        # summarized description. Make this a standard part of the enhanced image
        # analysis.
        text: Optional[str] = None
        image = None
        input_text = ""
        frame_number = await story.get_num_frames()
        seed_prompt = await self.get_seed_prompt(strategy_config)

        model_config = (
            cast(ModelConfig, strategy_config.text_to_text_model_config)
            if strategy_config
            else None
        )
        prompt_template = (
            cast(PromptTemplate, model_config.prompt_template) if model_config else None
        )
        target_language = prompt_template.target_language if prompt_template else "en"
        print(f"{target_language=}")

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
            last_text_tokens = last_text.split(" ")
            last_text_tokens = last_text_tokens[-40:]
            last_text = " ".join(last_text_tokens)
            if last_text.endswith("..."):
                last_text = last_text[:-3]

        in_text = f"{input_text} {last_text}"
        out_text = ""
        if target_language != "en":
            try:
                in_text = translate_text("en", in_text)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))
                in_text = in_text

        # print(f'Text prompt: "{text}"')
        if in_text and not in_text.isspace():
            # gpt-neo-2.7B produces very short text, so collect a handful
            # of its responses as the frame text.
            for i in range(3):
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
                        if len(out_text) > 500:
                            break
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

        text = await self._clean_up_text(
            text=text,
            keys=keys,
            errors=errors,
            httpx_client=httpx_client,
        )

        if text:
            # Generate an image for the frame, composing a prompt from
            # the frame's text...

            # Translate the story to English before
            # sending as an image prompt.
            try:
                text_en = translate_text("en", text)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))
                text_en = text

            image_prompt = output_image_style + " " + text_en
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

            if target_language != "en":
                try:
                    text = translate_text(target_language, text)
                except Exception as e:
                    traceback.print_exc(file=sys.stderr)
                    errors.append(str(e))

            text = (
                text.replace("&#39;", "'")
                .replace("&quot;", '"')
                .replace(" . ", ".\n\n")
                .replace(". ", ".\n\n")
                .replace("? ", "?\n\n")
                .replace("! ", "!\n\n")
            )

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
        text = " ".join(text.split(" "))
        text = text.replace("*", "")
        text = text.replace("_", "")
        text = text.replace("�", "'")
        text = text.strip()
        return text

    async def _clean_up_text(
        self,
        text: str,
        keys: KeysModel,
        errors: list[str],
        httpx_client: httpx.AsyncClient,
    ) -> str:
        """
        Cleans up the text for display.
        """
        text = (text or "").strip()
        if not text:
            return text

        prompt = f"""You are a fiction editor, given a text by a creative author prone
to errors of punctuation and grammar. Correct these errors, while preserving any
qualities the text may have of surrealism or even nonsense. If you see text like this:
"i a m b a d l y  f o r m a t t e d", remove the superfluous spaces and rewrite it like
this: "iambadly formatted". Remove anything that resembles computer source code,
filenames, or technical aspects of the Web. Replace any mention of American presidential
politics with something crazy and fanciful. If the text breaks off mid-sentence, finish
the thought while preserving the author's intent and style, ending the sentence with
correct grammar and punctuation.

Include nothing in your response but the corrected text.

Here is the text to correct:

{text}
"""
        model = (
            await InferenceModel.objects()
            .where(InferenceModel.slug == "openai-gpt-4o")
            .first()
            .output(load_json=True)
            .run()
        )
        if model:
            model_config = ModelConfig(
                slug="gpt-4o-cleaner",
                description="",
                model_parameters={},
                model=model,
            )
        else:
            raise ValueError("No gpt-4o model found.")

        # Use gpt-4o and the prompt above to clean up the text.
        try:
            print(f"Cleaning text: {text}")
            text = await text_to_text_inference(httpx_client, prompt, model_config, keys)
            print(f"Cleaned text: {text}")
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            errors.append(str(e))

        return text
