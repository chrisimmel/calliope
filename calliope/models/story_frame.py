import json
from typing import Any, Dict, Optional

from pydantic import BaseModel

from calliope.models.image import ImageModel
from calliope.models.video import VideoModel
from calliope.models.trigger_condition import TriggerConditionModel


class StoryFrameModel(BaseModel):
    """
    A frame of a story. (As in a graphic novel.)
    """

    # A piece of text conveying part of the story.
    text: Optional[str] = None

    # An image illustrating the story.
    image: Optional[ImageModel] = None

    # A video illustrating the story.
    video: Optional[VideoModel] = None

    # The minimum duration of this frame, in seconds.
    min_duration_seconds: Optional[int]

    # An optional trigger condition.
    trigger_condition: Optional[TriggerConditionModel] = None

    # The original image, before possible format conversion for the client.
    source_image: Optional[ImageModel] = None

    # Anything else someone may want to know about this frame?
    # Information about how and when it was generated, etc.
    metadata: Optional[Dict[str, Any]] = None

    @property
    def pretty_metadata(self) -> str:
        """
        Gets a nicely formatted string containing the frame metadata, if any.
        """
        return json.dumps(self.metadata, indent=2) if self.metadata else ""
