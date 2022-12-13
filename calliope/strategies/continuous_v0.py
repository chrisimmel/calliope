from calliope.models import ImageFormat, StoryFrameSequenceResponseModel
from calliope.models.story_frame import StoryFrameModel
from calliope.strategies.base import StoryStrategy
from calliope.strategies.parameters import StoryParameters
from calliope.strategies.registry import StoryStrategyRegistry


from calliope.inference import (
    caption_to_prompt,
    image_file_to_text_inference,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)
from calliope.utils.file import compose_filename
from calliope.utils.image import get_image_attributes

last_text = ""


@StoryStrategyRegistry.register()
class ContinuousStoryV0Strategy(StoryStrategy):
    """
    Tries to keep a story going, carrying context from a previous frame, if any,
    to a new frame. This works in the manner of an "Exquisite Corpse" exercise,
    where each generation blindly adds something new to the story, based only on
    the step immediately precedent.

    Returns a single frame.
    """

    strategy_name = "continuous_v0"

    def get_frame_sequence(
        self, parameters: StoryParameters
    ) -> StoryFrameSequenceResponseModel:
        client_id = parameters.get("client_id")

        # Get last_text from saved story state.
        global last_text

        if parameters.get("reset_strategy_state", False):
            last_text = ""

        output_image_style = parameters.get("output_image_style") or "A watercolor of"
        debug_data = {}
        errors = []
        caption = ""
        prompt = None
        text = None
        fragment_len = 0
        image = None

        if "input_image" in parameters:
            input_image = parameters.get("input_image")
            # TODO: Support other input image formats as needed.
            input_image_filename = "input_image.jpg"
            caption = "Along the riverrun"
            try:
                with open(input_image_filename, "wb") as f:
                    f.write(input_image)
                caption = image_file_to_text_inference(input_image_filename)
            except Exception as e:
                print(e)
                errors.append(str(e))
        if "input_text" in parameters:
            input_text = parameters.get("input_text")
            if caption:
                caption = f"{caption}. {input_text}"
            else:
                caption = input_text

        debug_data["image_caption"] = caption

        if last_text:
            last_text_tokens = last_text.split()
            last_text_tokens = last_text_tokens[int(len(last_text_tokens) / 2) :]
            last_text = " ".join(last_text_tokens)

        text = f"{caption} {last_text}"
        print(f'text prompt: "{text}"')
        text_1 = self._get_new_story_fragment(text)
        text_2 = self._get_new_story_fragment(text_1)
        text = text_1 + " " + text_2

        if not text:
            text = caption

        last_text = text
        # print(text)

        if text:
            prompt_template = output_image_style + " {x}"
            prompt = caption_to_prompt(text, prompt_template)

            try:
                output_image_filename_png = compose_filename(
                    "media", client_id, "output_image.png"
                )
                text_to_image_file_inference(prompt, output_image_filename_png)

                output_image_filename = output_image_filename_png
                image = get_image_attributes(output_image_filename)
            except Exception as e:
                print(e)
                errors.append(str(e))

        frame = StoryFrameModel(
            image=image,
            text=text,
        )

        return StoryFrameSequenceResponseModel(
            frames=[frame], debug_data=debug_data, errors=errors
        )

    def _get_new_story_fragment(self, text: str) -> str:
        fragment_len = len(text)
        try:
            text = text_to_extended_text_inference(text)
        except Exception as e:
            print(e)

        text = text[fragment_len:]
        text = " ".join(text.split(" "))
        text = text.replace("*", "")
        text = text.replace("_", "")
        text = text.strip()

        return text
