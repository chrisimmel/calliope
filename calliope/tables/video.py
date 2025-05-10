from datetime import datetime, timezone
from typing import Optional

from piccolo.table import Table
from piccolo.columns import (
    Float,
    Integer,
    Timestamptz,
    Varchar,
)

from calliope.models.video import VideoFormat, VideoModel
from calliope.utils.file import FileMetadata


class Video(Table):
    """
    The high-level attributes of a video.
    """

    width = Integer()
    height = Integer()
    format = Varchar(length=50)
    url = Varchar()
    duration_seconds = Float(null=True)
    frame_rate = Float(null=True)

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    def __str__(self) -> str:
        return f"<Video {self.width}x{self.height}, {self.format}, {self.duration_seconds}s, {self.url}>"

    def __repr__(self) -> str:
        return (
            f"<Video {self.id}: "  # type: ignore[attr-defined]
            f"{self.width}x{self.height}, "
            f"{self.format}, {self.duration_seconds}s, {self.frame_rate}fps, {self.url}"
        )

    def to_pydantic(self) -> Optional[VideoModel]:
        format = VideoFormat.fromMediaFormat(self.format)
        if not format:
            return None

        return VideoModel(
            width=self.width,
            height=self.height,
            format=format,
            url=self.url,
            duration_seconds=self.duration_seconds,
            frame_rate=self.frame_rate,
        )

    @classmethod
    async def from_pydantic(
        cls, model: VideoModel, file_metadata: FileMetadata
    ) -> "Video":
        width = model.width
        height = model.height
        format = model.format.value
        url = model.url
        duration_seconds = model.duration_seconds
        frame_rate = model.frame_rate

        date_created = file_metadata.date_created or datetime.now(timezone.utc)
        date_updated = file_metadata.date_updated or date_created

        instance: Optional[Video] = (
            await Video.objects()
            .where(
                Video.url == url,
                Video.format == format,
                Video.width == width,
                Video.height == height,
            )
            .first()
            .run()
        )
        if not instance:
            instance = Video(
                date_created=date_created,
                date_updated=date_updated,
                width=width,
                height=height,
                format=format,
                url=url,
                duration_seconds=duration_seconds,
                frame_rate=frame_rate,
            )

        return instance