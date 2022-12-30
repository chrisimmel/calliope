from calliope.models import (
    FramesRequestParamsModel,
    KeysModel,
    InferenceModelConfigsModel,
    SparrowStateModel,
    StoryFrameModel,
    StoryFrameSequenceResponseModel,
    StoryModel,
)
from calliope.strategies.base import StoryStrategy
from calliope.strategies.registry import StoryStrategyRegistry


from calliope.inference import (
    caption_to_prompt,
    image_file_to_text_inference,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)
from calliope.utils.file import create_sequential_filename
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class SimpleOneFrameStoryStrategy(StoryStrategy):
    """
    The strategy of the original /story/ endpoint.
    Returns a single frame based on input parameters. Doesn't attempt story continuation.
    """

    strategy_name = "simple_one_frame"

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
        image = None

        if parameters.input_image_filename:
            try:
                caption = image_file_to_text_inference(
                    parameters.input_image_filename, inference_model_configs, keys
                )
            except Exception as e:
                print(e)
                errors.append(str(e))

        debug_data["i_see"] = caption

        if parameters.input_text:
            if caption:
                caption = f"{caption}. {parameters.input_text}"
            else:
                caption = parameters.input_text

        text = text_to_extended_text_inference(caption, inference_model_configs, keys)
        prompt_template = output_image_style + " {x}"
        print(text)

        if text:
            prompt = caption_to_prompt(text, prompt_template)

            try:
                output_image_filename_png = create_sequential_filename(
                    "media", client_id, "out", "png", story
                )
                text_to_image_file_inference(
                    prompt, output_image_filename_png, inference_model_configs, keys
                )
                image = get_image_attributes(output_image_filename_png)
            except Exception as e:
                print(e)
                errors.append(str(e))

        frame = StoryFrameModel(
            image=image,
            text=text,
        )
        story.frames.append(frame)
        story.text = story.text + "\n" + text

        return StoryFrameSequenceResponseModel(
            frames=[frame], debug_data=debug_data, errors=errors
        )
