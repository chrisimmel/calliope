from typing import Optional

from pydantic import BaseModel

from calliope.models.inference_model_config import InferenceModelConfigsModel
from calliope.models.keys import KeysModel
from calliope.models.parameters import FramesRequestParamsModel


class StoryContextModel(BaseModel):
    """
    The context in which a story is created.
    """

    # Overall request parameters.
    parameters: FramesRequestParamsModel

    # Which inference models to use, and how.
    model_configs: InferenceModelConfigsModel

    # A dictionary of things like API keys.
    keys: KeysModel
