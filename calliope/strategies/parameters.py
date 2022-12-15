import base64
from typing import Optional, Type

from pydantic import BaseModel, Field

"""
class FramesRequestParams(BaseModel):
    input_image: Optional[str] = (
        Field(
            default=None,
            description="An input image, encoded in base64, optional (harvested image, for now, common web image formats work, jpg, png, etc.)",
        ),
    )
    input_audio: Optional[str] = (
        Field(
            default=None,
            description="An audio sample, encoded in base64, optional (harvested sound)",
        ),
    )
    client_id: str = (
        Field(
            description="Required. Could be a mac address, or, for testing, any string will do."
        ),
    )
    location: Optional[str] = (
        Field(None, description="The geolocation of the client."),
    )
    input_text: Optional[str] = (
        Field(
            default=None,
            description="Harvested text from client environment, not sure where you'd get this, here just in case.",
        ),
    )
    output_image_format: Optional[str] = (
        Field(
            default=None,
            description="The requested image format. Default is whatever comes out of the image generator, usually jpg or png",
        ),
    )
    output_image_width: Optional[int] = (
        Field(
            default=None,
            description="The requested image width. Default is whatever comes out of the image generator.",
        ),
    )
    output_image_height: Optional[int] = (
        Field(
            default=None,
            description="The requested image height. Default is whatever comes out of the image generator.",
        ),
    )
    output_image_style: Optional[str] = (
        Field(
            default=None, description="Optional description of the desired image style."
        ),
    )
    output_text_length: Optional[int] = (
        Field(
            default=None,
            description="Optional, the nominal length of the returned text, advisory, might be ignored.",
        ),
    )
    output_text_style: Optional[str] = (
        Field(
            default=None, description="Optional description of the desired text style."
        ),
    )
    reset_strategy_state: Optional[bool] = (
        Field(
            default=False,
            description="If set, instructs the strategy to reset its state, if any.",
        ),
    )
    strategy: Optional[str] = (
        Field(
            default=None,
            description="Optional, helps Calliope select what algorithm to use to generate the output. The idea is that we'll be able to build new ones and plug them in easily.",
        ),
    )
    debug: Optional[bool] = Field(
        default=False, description="Enables richer diagnostic output in the response."
    )
"""


class FramesRequestParams(BaseModel):
    input_image: Optional[str] = None
    input_audio: Optional[str] = None
    client_id: str
    location: Optional[str] = None
    input_text: Optional[str] = None
    output_image_format: Optional[str] = None
    output_image_width: Optional[int] = None
    output_image_height: Optional[int] = None
    output_image_style: Optional[str] = None
    output_text_length: Optional[int] = None
    output_text_style: Optional[str] = None
    reset_strategy_state: Optional[bool] = False
    strategy: Optional[str] = None
    debug: Optional[bool] = False


def decode_b64_to_file(data: str, filename: str) -> None:
    bytes = str.encode(data)
    decoded_bytes = base64.b64decode(bytes)
    with open(filename, "wb") as f:
        f.write(decoded_bytes)


class StoryStrategyParams(FramesRequestParams):
    input_image_filename: Optional[str]
    input_audio_filename: Optional[str]

    @classmethod
    def from_frame_request_params(
        cls: Type["StoryStrategyParams"],
        request_params: FramesRequestParams,
    ) -> "StoryStrategyParams":
        story_strategy_params = StoryStrategyParams(
            client_id=request_params.client_id,
            location=request_params.location,
            input_image=request_params.input_image,
            input_audio=request_params.input_audio,
            input_text=request_params.input_text,
            output_image_format=request_params.output_image_format,
            output_image_width=request_params.output_image_width,
            output_image_height=request_params.output_image_height,
            output_image_style=request_params.output_image_style,
            output_text_length=request_params.output_text_length,
            output_text_style=request_params.output_text_style,
            reset_strategy_state=request_params.reset_strategy_state,
            strategy=request_params.strategy,
            debug=request_params.debug,
        )
        if story_strategy_params.input_image:
            input_image_filename = "input_image.jpg"
            decode_b64_to_file(story_strategy_params.input_image, input_image_filename)
            story_strategy_params.input_image_filename = input_image_filename

        if story_strategy_params.input_audio:
            input_audio_filename = "input_audio.wav"
            decode_b64_to_file(story_strategy_params.input_audio, input_audio_filename)
            story_strategy_params.input_audio_filename = input_audio_filename

        return story_strategy_params
