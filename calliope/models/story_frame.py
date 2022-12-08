from typing import Optional

from pydantic import BaseModel

from calliope.models.image import ImageModel


class StoryFrameModel(BaseModel):
    """
    A frame of a story. (As in a graphic novel.)
    """

    # A piece of text conveying part of the story.
    text: Optional[str]

    # An image illustrating the story.
    image: Optional[ImageModel]

    # When to begin displaying this frame.
    start_time: Optional[str]

    # When to stop displaying this frame.
    end_time: Optional[str]
