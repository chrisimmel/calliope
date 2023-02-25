from typing import List, Optional, Sequence

import cuid
from pydantic import BaseModel, StrictStr
from tortoise.models import Model
from tortoise import fields

from calliope.models.schedule import ScheduleStateModel
from calliope.models.story import Story


class SparrowStateModel(BaseModel):
    """
    The state of a given sparrow or flock.
    """

    # The sparrow's ID.
    sparrow_id: StrictStr

    # THe ID of the story in progress.
    current_story_id: Optional[StrictStr] = None

    # The IDs of all stories created for this client.
    story_ids: List[StrictStr] = []

    # The schedule state, if any.
    schedule_state: Optional[ScheduleStateModel]


class SparrowState(Model):
    """
    The state of a given sparrow or flock.
    """

    id = fields.CharField(max_length=50, pk=True, generated=False)

    # The sparrow's ID. There can be only one state per sparrow or flock.
    sparrow_id = fields.CharField(max_length=50, unique=True)

    # The story in progress, if any.
    current_story = fields.ForeignKeyField(
        "models.Story", related_name="active_sparrow_states", null=True
    )

    # All stories created for this client.
    stories = fields.ManyToManyField("models.Story", related_name="sparrow_states")

    # The schedule state, if any.
    # (Holding off on defining this, pending agreement on how a schedule should work.)
    # schedule_state = fields.ForeignKeyField(
    #     "models.ScheduleState", related_name="sparrow_states", null=True
    # )

    class Meta:
        table = "sparrow_state"

    @classmethod
    async def from_pydantic(cls, model: SparrowStateModel) -> "SparrowState":
        sparrow_id = model.sparrow_id

        instance: SparrowState = await SparrowState.get_or_none(sparrow_id=sparrow_id)

        current_story: Optional[Story] = (
            Story.get_or_none(model.current_story_id) if model.current_story_id else None
        )
        stories: Sequence[Story] = (
            list(Story.filter(id__in=model.story_ids)) if model.story_ids else []
        )
        # schedule_state: Optional[ScheduleState] = ScheduleState.get_or_none(
        #     sparrow_id=sparrow_id
        # )

        if instance:
            instance.sparrow_id = sparrow_id
            instance.current_story = current_story
            instance.stories = stories
        else:
            instance = SparrowState(
                id=cuid.cuid(),
                sparrow_id=sparrow_id,
                current_story=current_story,
                stories=stories,
            )

        return instance
