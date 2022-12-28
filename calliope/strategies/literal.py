from calliope.models import (
    FramesRequestParamsModel,
    SparrowStateModel,
    StoryFrameModel,
    StoryFrameSequenceResponseModel,
    StoryModel,
)
from calliope.strategies.base import StoryStrategy
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
        sparrow_state: SparrowStateModel,
        story: StoryModel,
    ) -> StoryFrameSequenceResponseModel:
        client_id = parameters.client_id
        debug_data = {}
        errors = []
        frames = []

        input_text = parameters.input_text

        prompts = input_text.split("|") if input_text else []

        if parameters.input_image_filename:
            try:
                caption = image_file_to_text_inference(parameters.input_image_filename)
                debug_data["i_see"] = caption
                prompts.append(caption)
            except Exception as e:
                print(e)
                errors.append(str(e))

        for prompt in prompts:
            image = None

            try:
                output_image_filename_png = create_sequential_filename(
                    "media", client_id, "out", "png", story
                )
                text_to_image_file_inference(prompt, output_image_filename_png)

                output_image_filename = output_image_filename_png
                image = get_image_attributes(output_image_filename)
            except Exception as e:
                print(e)
                errors.append(str(e))

            frame = StoryFrameModel(
                image=image,
                text=prompt,
            )
            frames.append(frame)

            story.frames.append(frame)
            story.text = story.text + "\n" + prompt

        return StoryFrameSequenceResponseModel(
            frames=frames, debug_data=debug_data, errors=errors
        )
