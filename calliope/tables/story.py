from datetime import datetime, timezone
from typing import Optional

from piccolo.table import Table
from piccolo.columns import (
    Text,
    Timestamptz,
    Varchar,
)

from calliope.models import StoryModel


class Story(Table):
    """
    A story.
    """

    # A visible unique ID, a CUID.
    cuid = Varchar(length=50, unique=True, index=True)

    # The story's title.
    title = Text()

    # The name of the strategy from which the story issues.
    strategy_name = Varchar(length=50, null=True)

    # The ID of the flock or sparrow for which the story was created.
    created_for_sparrow_id = Varchar(length=50, null=True)

    # The date the story was created.
    date_created = Timestamptz()

    # The date the story was last updated.
    date_updated = Timestamptz(auto_update=datetime.now)

    @property
    def computed_title(self) -> str:
        """
        Takes as the title the text of the first frame, if any, else the story_id.
        """
        for frame in self.frames:
            if frame.text:
                return frame.text

        return self.id

    @classmethod
    async def from_pydantic(cls, model: StoryModel) -> "Story":
        story_cuid = model.story_id
        title = model.title if model.title else None
        strategy_name = model.strategy_name
        created_for_sparrow_id = model.created_for_id

        date_created = (
            datetime.fromisoformat(model.date_created)
            if model.date_created
            else datetime.now(timezone.utc)
        )
        date_updated = (
            datetime.fromisoformat(model.date_updated)
            if model.date_updated
            else datetime.now(timezone.utc)
        )

        instance: Optional[Story] = (
            await Story.objects().where(Story.cuid == story_cuid).first().run()
        )
        if instance:
            instance.title = title
            instance.strategy_name = strategy_name
            instance.created_for_sparrow_id = created_for_sparrow_id
        else:
            instance = Story(
                cuid=story_cuid,
                title=title,
                strategy_name=strategy_name,
                created_for_sparrow_id=created_for_sparrow_id,
                date_created=date_created,
                date_updated=date_updated,
            )

        return instance
