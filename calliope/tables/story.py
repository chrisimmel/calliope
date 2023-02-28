from datetime import datetime
from typing import Optional, Sequence
from calliope.utils.file import FileMetadata

import cuid
from piccolo.table import Table
from piccolo.columns import (
    ForeignKey,
    Integer,
    JSONB,
    Text,
    Timestamptz,
    Varchar,
)

from calliope.models import StoryModel
from calliope.models import StoryFrameModel

# from calliope.tables.story_frame import StoryFrame
from calliope.tables.image import Image


class StoryFrame(Table):
    """
    A frame of a story. (As in a graphic novel.)
    """

    # The primary key, a CUID.
    # id = Varchar(length=50, primary_key=True)

    story = ForeignKey(references="Story")

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
    # TODO: Redefine as auto_update as soon as initial migrations are done.
    date_updated = Timestamptz()  # auto_update=datetime.now)

    @classmethod
    async def from_pydantic(
        cls,
        model: StoryFrameModel,
        file_metadata: FileMetadata,
        story_cuid: str,
        number: int,
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
            instance.date_created = file_metadata.date_created
            instance.date_updated = file_metadata.date_updated
            instance.text = text
            instance.min_duration_seconds = min_duration_seconds
            instance.trigger_condition = trigger_condition
            instance.metadata = metadata
        else:
            instance = StoryFrame(
                # id=cuid.cuid(),
                date_created=file_metadata.date_created,
                date_updated=file_metadata.date_updated,
                number=number,
                text=text,
                min_duration_seconds=min_duration_seconds,
                trigger_condition=trigger_condition,
                metadata=metadata,
            )

        return instance


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

    # The dates the story was created and updated.
    date_created = Timestamptz()
    # TODO: Redefine as auto_update as soon as initial migrations are done.
    date_updated = Timestamptz()  # auto_update=datetime.now)

    async def get_frames(self, include_images: bool = False) -> Sequence[StoryFrame]:
        if include_images:
            frames = (
                await StoryFrame.objects(StoryFrame.image, StoryFrame.source_image)
                .where(StoryFrame.story.id == self.id)
                .order_by(StoryFrame.number)
                .run()
            )
            for frame in frames:
                # This seems like a hack necessitated by a quirk or Piccolo.
                if frame.image and not frame.image.id:
                    frame.image = None
                if frame.source_image and not frame.source_image.id:
                    frame.source_image = None

            return frames
        else:
            return (
                await StoryFrame.objects()
                .where(StoryFrame.story.id == self.id)
                .order_by(StoryFrame.number)
                .run()
            )

    async def get_head_text(self, max_frames: int = -1) -> Sequence[StoryFrame]:
        qs = (
            StoryFrame.select()
            .where(
                StoryFrame.story.id == self.id,
                StoryFrame.text.is_not_null(),
                StoryFrame.text != "",
            )
            .order_by(StoryFrame.number)
        )
        if max_frames > 0:
            qs = qs.limit(max_frames)

        fragments = await qs.run()
        return "\n".join(fragments)

    async def get_tail_text(self, max_frames: int = -1) -> Sequence[StoryFrame]:
        qs = (
            StoryFrame.select()
            .where(
                StoryFrame.story.id == self.id,
                StoryFrame.text.is_not_null(),
                StoryFrame.text != "",
            )
            .order_by(StoryFrame.number, ascending=False)
        )
        if max_frames > 0:
            qs = qs.limit(max_frames)

        fragments = await qs.run()
        return "\n".join(fragments)

    async def compute_title(self) -> str:
        return await self.get_head_text(max_frames=1)

    async def get_thumb(self) -> Optional[Image]:
        frame_with_source_image = (
            await StoryFrame.objects(StoryFrame.source_image)
            .where(
                StoryFrame.story.id == self.id,
                StoryFrame.source_image.is_not_null(),
            )
            .order_by(StoryFrame.number)
            .first()
            .run()
        )
        source_image = (
            frame_with_source_image.source_image if frame_with_source_image else None
        )

        if source_image:
            longer_dim = max(source_image.width, source_image.height)
            scale = 48 / longer_dim
            return Image(
                width=source_image.width * scale,
                height=source_image.height * scale,
                format=source_image.format,
                url=source_image.url,
            )
        return None

    @classmethod
    async def from_pydantic(
        cls, model: StoryModel, file_metadata: FileMetadata
    ) -> "Story":
        story_cuid = model.story_id
        title = model.title if model.title else None
        strategy_name = model.strategy_name
        created_for_sparrow_id = model.created_for_id

        instance: Optional[Story] = (
            await Story.objects().where(Story.cuid == story_cuid).first().run()
        )
        if instance:
            instance.title = title
            instance.strategy_name = strategy_name
            instance.created_for_sparrow_id = created_for_sparrow_id
            instance.date_created = file_metadata.date_created
            instance.date_updated = file_metadata.date_updated
        else:
            instance = Story(
                cuid=story_cuid,
                title=title,
                strategy_name=strategy_name,
                created_for_sparrow_id=created_for_sparrow_id,
                date_created=file_metadata.date_created,
                date_updated=file_metadata.date_updated,
            )

        return instance

    @classmethod
    def create_new(
        cls,
        strategy_name: Optional[str] = None,
        created_for_sparrow_id: Optional[str] = None,
    ) -> "Story":
        return Story(
            cuid=cuid.cuid(),
            strategy_name=strategy_name,
            created_for_sparrow_id=created_for_sparrow_id,
            date_created=datetime.datetime.utcnow(),
        )
