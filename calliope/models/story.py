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

    # The date the story was created.
    date_created: Optional[StrictStr] = None

    # The date the story was last updated.
    date_updated: Optional[StrictStr] = None

    # The accumulated text.
    text: Optional[StrictStr] = ""

    # The URL-friendly slug for the story
    slug: Optional[StrictStr] = None

    # The frames that are part of this story.
    frames: List[StoryFrameModel] = []

    @property
    def title(self) -> str:
        """
        Takes as the title the text of the first frame, if any, else the story_id.
        """
        for frame in self.frames:
            if frame.text:
                return frame.text

        return self.story_id
