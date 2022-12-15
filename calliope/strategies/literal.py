import base64

from calliope.models import StoryFrameSequenceResponseModel
from calliope.models.story_frame import StoryFrameModel
from calliope.strategies.base import StoryStrategy
from calliope.strategies.parameters import StoryStrategyParams
from calliope.strategies.registry import StoryStrategyRegistry


from calliope.inference import (
    text_to_image_file_inference,
)
from calliope.utils.file import compose_filename
from calliope.utils.image import get_image_attributes


@StoryStrategyRegistry.register()
class LiteralStrategy(StoryStrategy):
    """
    Takes the input_text as the prompt to generate an image in a single frame. Echos back the text.
    """

    strategy_name = "literal"

    async def get_frame_sequence(
        self, parameters: StoryStrategyParams
    ) -> StoryFrameSequenceResponseModel:
        client_id = parameters.client_id
        debug_data = {}
        errors = []
        frames = []

        input_text = parameters.input_text or ""

        prompts = input_text.split("|")
        for index, prompt in enumerate(prompts):
            try:
                output_image_filename_png = compose_filename(
                    "media", client_id, f"output_image_{index}.png"
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

        return StoryFrameSequenceResponseModel(
            frames=frames, debug_data=debug_data, errors=errors
        )
