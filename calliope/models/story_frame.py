import json
from typing import Any, Dict, Optional

import cuid
from pydantic import BaseModel
from tortoise.models import Model
from tortoise import fields

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


class StoryFrame(Model):
    """
    A frame of a story. (As in a graphic novel.)
    """

    id = fields.CharField(max_length=50, pk=True, generated=False)

    story = fields.ForeignKeyField("models.Story", related_name="frames")

    # The frame number in the story, starting from 0.
    number = fields.BigIntField()

    # A piece of text conveying part of the story.
    text = fields.CharField(max_length=65536, null=True)

    # An image illustrating the story.
    image = fields.OneToOneField("models.Image", related_name="frame", null=True)

    # The minimum duration of this frame, in seconds.
    min_duration_seconds = fields.IntField()

    # An optional trigger condition.
    trigger_condition = fields.JSONField(null=True)

    # The original image, before possible format conversion for the client.
    source_image = fields.OneToOneField(
        "models.Image", related_name="source_for_frame", null=True
    )

    # Anything else someone may want to know about this frame?
    # Information about how and when it was generated, etc.
    metadata = fields.JSONField(null=True)

    date_created = fields.DatetimeField(auto_now_add=True)
    date_updated = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "story_frame"

    @classmethod
    async def from_pydantic(cls, model: StoryFrameModel, number: int) -> "StoryFrame":
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

        instance: Optional[StoryFrame] = await StoryFrame.get_or_none(id=id)
        if instance:
            instance.text = text
            instance.min_duration_seconds = min_duration_seconds
            instance.trigger_condition = trigger_condition
            instance.metadata = metadata
        else:
            instance = StoryFrame(
                id=cuid.cuid(),
                number=number,
                text=text,
                min_duration_seconds=min_duration_seconds,
                trigger_condition=trigger_condition,
                metadata=metadata,
            )

        return instance
