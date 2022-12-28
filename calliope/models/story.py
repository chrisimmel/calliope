from typing import List, Optional

from pydantic import BaseModel, StrictStr

from calliope.models.story_frame import StoryFrameModel


class StoryModel(BaseModel):
    """
    A story.
    """

    # The story's ID.
    story_id: StrictStr

    # The name of the strategy from which the story issues.
    strategy_name: StrictStr

    # The ID of the flock or sparrow for which the story was created.
    created_for_id: Optional[StrictStr] = None

    # The accumulated text.
    text: Optional[StrictStr] = ""

    # The frames that are part of this story.
    frames: List[StoryFrameModel] = []
