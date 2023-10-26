from datetime import datetime, timezone
import json
from typing import cast, Optional, Sequence

import cuid
from piccolo.table import Table
from piccolo.columns import (
    Boolean,
    ForeignKey,
    Integer,
    JSONB,
    Text,
    Timestamptz,
    Varchar,
)

from calliope.models import StoryModel
from calliope.models import StoryFrameModel
from calliope.tables.image import Image
from calliope.utils.file import FileMetadata
from calliope.utils.piccolo import load_json_if_necessary


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

    indexed_for_search = Boolean(default=False)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    @property
    def pretty_metadata(self) -> str:
        """
        Gets a nicely formatted string containing the frame metadata, if any.
        """
        return json.dumps(self.metadata, indent=2) if self.metadata else ""

    def to_pydantic(self) -> StoryFrameModel:
        return StoryFrameModel(
            text=self.text,
            min_duration_seconds=self.min_duration_seconds,
            trigger_condition=None,  # TODO: Fix! self.trigger_condition,
            image=self.image.to_pydantic() if self.image else None,
            source_image=self.source_image.to_pydantic() if self.source_image else None,
            metadata=load_json_if_necessary(self.metadata),
        )

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

        date_created = file_metadata.date_created or datetime.now(timezone.utc)
        date_updated = file_metadata.date_updated or date_created

        instance: Optional[StoryFrame] = (
            await StoryFrame.objects()
            .where(StoryFrame.number == number, StoryFrame.story.cuid == story_cuid)
            .first()
            .run()
        )
        if instance:
            instance.date_created = date_created
            instance.date_updated = date_updated
            instance.text = text
            instance.min_duration_seconds = min_duration_seconds
            instance.trigger_condition = trigger_condition or ""
            instance.metadata = metadata or ""
        else:
            instance = StoryFrame(
                date_created=date_created,
                date_updated=date_updated,
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

    # A thumbnail image illustrating the story.
    thumbnail_image = ForeignKey(references=Image, null=True)

    # The dates the story was created and updated.
    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    async def get_frame_count(self) -> int:
        return cast(int, await StoryFrame.count().where(
            StoryFrame.story.id == self.id  # type: ignore[attr-defined]
        ))

    async def get_frames(
        self,
        offset: int = 0,
        max_frames: int = 0,
        include_images: bool = False,
        include_indexed_for_search: bool = True,
    ) -> Sequence[StoryFrame]:
        """
        Gets the story's frames.

        Args:
            max_frames: the maximum number of frames to include.
            If negative, takes the last N frames.
            If zero (the default), takes all.
        """
        qs = (
            StoryFrame.objects(StoryFrame.image, StoryFrame.source_image)
            if include_images
            else StoryFrame.objects()
        ).where(StoryFrame.story.id == self.id)  # type: ignore[attr-defined]

        if not include_indexed_for_search:
            qs = qs.where(StoryFrame.indexed_for_search.eq(True))

        if max_frames > 0:
            # First n frames.
            qs = qs.order_by(StoryFrame.number).limit(max_frames)
        elif max_frames < 0:
            # Last n frames. These are reversed, so need to reverse again after
            # retrieved.
            qs = qs.order_by(StoryFrame.number, ascending=False).limit(-max_frames)
        else:
            # All frames.
            qs = qs.order_by(StoryFrame.number)

        frames = await qs.output(load_json=True).offset(offset).run()
        if include_images:
            for frame in frames:
                # This seems like a hack necessitated by a Piccolo quirk.
                if frame.image and not frame.image.id:
                    frame.image = None
                if frame.source_image and not frame.source_image.id:
                    frame.source_image = None

        if max_frames < 0:
            # Rows are sorted in reverse frame order, so reverse them.
            frames.reverse()

        return frames

    async def get_text(self, max_frames: int = 0) -> str:
        """
        Gets the story text.

        Args:
            max_frames: the maximum number of frames with text to include.
            If negative, takes the last N frames. If zero (the default),
            takes all.
        """
        qs = StoryFrame.select(StoryFrame.text).where(
            StoryFrame.story.id == self.id,  # type: ignore[attr-defined]
            StoryFrame.text.is_not_null(),
            StoryFrame.text != "",
        )
        if max_frames > 0:
            # First n frames.
            qs = qs.order_by(StoryFrame.number).limit(max_frames)
        elif max_frames < 0:
            # Last n frames. These are reversed, so need to reverse again after
            # retrieved.
            qs = qs.order_by(StoryFrame.number, ascending=False).limit(-max_frames)
        else:
            # All frames.
            qs = qs.order_by(StoryFrame.number)

        rows = list(await qs.run())
        if max_frames < 0:
            # Rows are sorted in reverse frame order, so reverse them.
            rows.reverse()

        fragments = [row.get("text", "") for row in rows]
        return "".join(fragments) if fragments else ""

    async def get_num_frames(self) -> int:
        return int(await StoryFrame.count().where(
            StoryFrame.story.id == self.id  # type: ignore[attr-defined]
        ))

    async def compute_title(self) -> str:
        return await self.get_text(max_frames=1)

    async def compute_thumbnail(self) -> Optional[Image]:
        frame_with_source_image = (
            await StoryFrame.objects(StoryFrame.source_image)
            .where(
                StoryFrame.story.id == self.id,  # type: ignore[attr-defined]
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

        date_created = datetime.fromisoformat(cast(str, model.date_created))
        date_updated = datetime.fromisoformat(cast(str, model.date_updated))

        instance: Optional[Story] = (
            await Story.objects().where(Story.cuid == story_cuid).first().run()
        )
        if instance:
            instance.title = title
            instance.strategy_name = strategy_name
            instance.created_for_sparrow_id = created_for_sparrow_id
            instance.date_created = date_created
            instance.date_updated = date_updated
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
            date_created=datetime.now(timezone.utc),
        )
