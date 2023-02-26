from datetime import datetime
from typing import Optional

import cuid
from piccolo.table import Table
from piccolo.columns import (
    Integer,
    ForeignKey,
    JSONB,
    Timestamptz,
    Text,
    Varchar,
)

from calliope.models import StoryFrameModel
from calliope.tables.image import Image
from calliope.tables.story import Story


class StoryFrame(Table):
    """
    A frame of a story. (As in a graphic novel.)
    """

    # The primary key, a CUID.
    # id = Varchar(length=50, primary_key=True)

    story = ForeignKey(references=Story)

    # The frame number in the story, starting from 0.
    number = Integer()

    # A piece of text conveying part of the story.
    text = Text(null=True)

    # An image illustrating the story.
    image = ForeignKey(references=Image, null=True)

    # The original image, before possible format conversion for the client.
    source_image = ForeignKey(references=Image, null=True)

    # The minimum duration of this frame, in seconds.
    min_duration_seconds = Integer()

    # An optional trigger condition.
    trigger_condition = JSONB(null=True)

    # Anything else someone may want to know about this frame?
    # Information about how and when it was generated, etc.
    metadata = JSONB(null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    @classmethod
    async def from_pydantic(
        cls, model: StoryFrameModel, story_cuid: str, number: int
    ) -> "StoryFrame":
        text = model.text
        min_duration_seconds = model.min_duration_seconds or 0
        trigger_condition = (
            model.trigger_condition.dict(exclude_none=True)
            if model.trigger_condition
            else None
        )
        metadata = model.metadata

        # FK fields that must be set otherwise:
        # story
        # image
        # source_image

        instance: Optional[StoryFrame] = (
            await StoryFrame.objects()
            .where(StoryFrame.number == number, StoryFrame.story.cuid == story_cuid)
            .first()
            .run()
        )
        if instance:
            instance.text = text
            instance.min_duration_seconds = min_duration_seconds
            instance.trigger_condition = trigger_condition
            instance.metadata = metadata
        else:
            instance = StoryFrame(
                # id=cuid.cuid(),
                number=number,
                text=text,
                min_duration_seconds=min_duration_seconds,
                trigger_condition=trigger_condition,
                metadata=metadata,
            )

        return instance
