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
    ) -> StoryFrameSequenceResponseModel:
        client_id = parameters.client_id

        output_image_style = parameters.output_image_style or "A watercolor of"
        debug_data = {}
        errors = []
        caption = ""
        prompt = None
        text = None
        image = None

        if parameters.input_image_filename:
            caption = "Along the riverrun"
            try:
                caption = image_file_to_text_inference(
                    parameters.input_image_filename, inference_model_configs, keys
                )
            except Exception as e:
                print(e)
                errors.append(str(e))
        if parameters.input_text:
            if caption:
                caption = f"{caption}. {parameters.input_text}"
            else:
                caption = parameters.input_text

        debug_data["i_see"] = caption

        last_text = story.text
        if last_text:
            last_text_tokens = story.text.split()
            # last_text_tokens = last_text_tokens[int(len(last_text_tokens) / 2) :]
            last_text_tokens = last_text_tokens[-20:]
            last_text = " ".join(last_text_tokens)

        text = f"{caption} {last_text}"
        print(f'Text prompt: "{text}"')
        text_1 = self._get_new_story_fragment(text, inference_model_configs, keys)
        text_2 = self._get_new_story_fragment(text_1, inference_model_configs, keys)
        text = text_1 + " " + text_2 + " "

        if not text or text.isspace():
            text = caption

        last_text = text
        # print(text)

        if text:
            prompt_template = output_image_style + " {x}"
            prompt = caption_to_prompt(text, prompt_template)
            print(f'Image prompt: "{prompt}"')

            try:
                output_image_filename_png = create_sequential_filename(
                    "media", client_id, "out", "png", story
                )
                text_to_image_file_inference(
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
                print(e)
                errors.append(str(e))

        frame = StoryFrameModel(
            image=image,
            text=text,
            min_duration_seconds=DEFAULT_MIN_DURATION_SECONDS,
        )
        story.frames.append(frame)
        story.text = story.text + text

        return StoryFrameSequenceResponseModel(
            frames=[frame],
            debug_data=debug_data,
            errors=errors,
            append_to_prior_frames=True,
        )

    def _get_new_story_fragment(
        self, text: str, inference_model_configs, keys: KeysModel
    ) -> str:
        fragment_len = len(text)
        try:
            text = text_to_extended_text_inference(text, inference_model_configs, keys)
        except Exception as e:
            print(e)

        text = text[fragment_len:]
        text = " ".join(text.split(" "))
        text = text.replace("*", "")
        text = text.replace("_", "")
        text = text.strip()

        return text
