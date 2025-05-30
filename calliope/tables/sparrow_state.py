from datetime import datetime, timezone
from typing import Optional
from calliope.utils.file import FileMetadata

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
    async def from_pydantic(
        cls, model: SparrowStateModel, file_metadata: FileMetadata
    ) -> "SparrowState":
        sparrow_id = model.sparrow_id
        current_story_cuid = model.current_story_id

        current_story: Optional[Story] = (
            await Story.objects().where(Story.cuid == current_story_cuid).first().run()
            if current_story_cuid
            else None
        )

        date_created = file_metadata.date_created or datetime.now(timezone.utc)
        date_updated = file_metadata.date_updated or date_created

        instance: Optional[SparrowState] = (
            await SparrowState.objects()
            .where(SparrowState.sparrow_id == sparrow_id)
            .first()
            .run()
        )
        if instance:
            instance.date_created = date_created
            instance.date_updated = date_updated
            instance.current_story = (
                current_story.id if current_story else None  # type: ignore[attr-defined]
            )
        else:
            instance = SparrowState(
                # id=create_cuid(),
                sparrow_id=sparrow_id,
                date_created=date_created,
                date_updated=date_updated,
                current_story=(
                    current_story.id  # type: ignore[attr-defined]
                    if current_story
                    else None
                ),
            )

        return instance
