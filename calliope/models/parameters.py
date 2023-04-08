from typing import Any, Dict, Optional

from pydantic import BaseModel, root_validator

from calliope.strategies import StrategyName


"""
This doesn't work. Improper use of Field()...
TODO: Would be nice to get descriptions on these fields for the OpenAPI docs.

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
    max_output_text_length: Optional[int] = (
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


class ClientTypeParamsModel(BaseModel):
    """
    Holds parameters that may be attached to a type of client,
    such as a specific class of device or application.
    """

    output_image_format: Optional[str] = None
    output_image_width: Optional[int] = None
    output_image_height: Optional[int] = None
    max_output_text_length: Optional[int] = None


class StoryParamsModel(ClientTypeParamsModel):
    """
    Holds parameters for generating frames of a story.
    """

    client_type: Optional[str] = None
    input_image: Optional[str] = None
    input_image_filename: Optional[str]
    input_audio: Optional[str] = None
    input_audio_filename: Optional[str]
    location: Optional[str] = None
    input_text: Optional[str] = None
    output_image_style: Optional[str] = None
    output_text_style: Optional[str] = None
    strategy: Optional[StrategyName] = None
    image_to_text_model_config: Optional[str] = None
    text_to_image_model_config: Optional[str] = None
    text_to_text_model_config: Optional[str] = None
    audio_to_text_model_config: Optional[str] = None
    debug: Optional[bool] = False
    extra_fields: Optional[Dict[str, Any]] = None

    @root_validator(pre=True)
    def build_extra_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collects any fields that aren't explicitly modeled into extra_fields.
        """
        modeled_field_names = {field.alias for field in cls.__fields__.values()}

        extra_fields: Dict[str, Any] = {}
        for field_name in list(values):
            if field_name not in modeled_field_names:
                extra_fields[field_name] = values.pop(field_name)
        values["extra_fields"] = extra_fields
        return values


class FramesRequestParamsModel(StoryParamsModel):
    client_id: str
