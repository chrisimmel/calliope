from typing import List, Optional

from pydantic import BaseModel, StrictStr
from tortoise.models import Model
from tortoise import fields

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


class Story(Model):
    """
    A story.
    """

    id = fields.CharField(max_length=50, pk=True, generated=False)

    # The story's title.
    title = fields.CharField(max_length=512, null=True)

    # The name of the strategy from which the story issues.
    strategy_name: fields.CharField(max_length=50, null=True)

    # The ID of the flock or sparrow for which the story was created.
    created_for_id = fields.CharField(max_length=50, null=True)

    # The date the story was created.
    date_created = fields.DatetimeField(auto_now_add=True)

    # The date the story was last updated.
    date_updated = fields.DatetimeField(auto_now=True)

    @property
    def computed_title(self) -> str:
        """
        Takes as the title the text of the first frame, if any, else the story_id.
        """
        for frame in self.frames:
            if frame.text:
                return frame.text

        return self.id

    class Meta:
        table = "story"

    @classmethod
    async def from_pydantic(cls, model: StoryModel) -> "Story":
        id = model.story_id
        strategy_name = model.strategy_name
        created_for_id = model.created_for_id
        title = model.title[:512] if model.title else None

        instance: Story = await Story.get_or_none(id=id)
        if instance:
            instance.strategy_name = strategy_name
            instance.created_for_id = created_for_id
        else:
            instance = Story(
                id=id,
                title=title,
                strategy_name=strategy_name,
                created_for_id=created_for_id,
            )

        return instance
