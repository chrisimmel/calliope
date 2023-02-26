from datetime import datetime, timezone
from typing import Optional

import cuid
from piccolo.table import Table
from piccolo.columns import (
    ForeignKey,
    Timestamptz,
    Varchar,
)

from calliope.models import SparrowStateModel
from calliope.tables.story import Story


class SparrowState(Table):
    """
    The state of a given sparrow or flock.
    """

    # The primary key, a CUID.
    # id = Varchar(length=50, primary_key=True)

    # The sparrow's ID. There can be only one state per sparrow or flock.
    sparrow_id = Varchar(length=50, unique=True, index=True)

    # The story in progress, if any.
    current_story = ForeignKey(references=Story, null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    # The schedule state, if any.
    # (Holding off on defining this, pending agreement on how a schedule should work.)
    # schedule_state = fields.ForeignKeyField(
    #     "models.ScheduleState", related_name="sparrow_states", null=True
    # )

    @classmethod
    async def from_pydantic(cls, model: SparrowStateModel) -> "SparrowState":
        sparrow_id = model.sparrow_id
        current_story_cuid = model.current_story_id

        current_story: Optional[Story] = (
            await Story.objects().where(Story.cuid == current_story_cuid).first().run()
            if current_story_cuid
            else None
        )

        instance: Optional[SparrowState] = (
            await SparrowState.objects()
            .where(SparrowState.sparrow_id == sparrow_id)
            .first()
            .run()
        )
        if instance:
            instance.current_story = model.current_story_id
        else:
            instance = SparrowState(
                # id=cuid.cuid(),
                sparrow_id=sparrow_id,
                date_created=datetime.now(timezone.utc),
                current_story=current_story.id if current_story else None,
            )

        return instance
