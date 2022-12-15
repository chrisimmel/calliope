from typing import Optional

from pydantic import BaseModel

from calliope.models.image import ImageModel
from calliope.models.trigger_condition import TriggerConditionModel


class StoryFrameModel(BaseModel):
    """
    A frame of a story. (As in a graphic novel.)
    """

    # A piece of text conveying part of the story.
    text: Optional[str] = None

    # An image illustrating the story.
    image: Optional[ImageModel] = None

    # An optional trigger condition.
    trigger_condition: Optional[TriggerConditionModel] = None
