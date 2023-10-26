from datetime import datetime, timezone
from typing import Optional

from piccolo.table import Table
from piccolo.columns import (
    Integer,
    Timestamptz,
    Varchar,
)

from calliope.models import ImageFormat, ImageModel
from calliope.utils.file import FileMetadata


class Image(Table):
    """
    The high-level attributes of an image.
    """

    # The primary key, a CUID.
    # id = Varchar(length=50, primary_key=True)

    width = Integer()
    height = Integer()
    format = Varchar(length=50)
    url = Varchar()

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)

    def __str__(self) -> str:
        return f"<Image {self.width}x{self.height}, {self.format}, {self.url}>"

    def __repr__(self) -> str:
        return (
            f"<Image {self.id}: "  # type: ignore[attr-defined]
            f"{self.width}x{self.height}, "
            f"{self.format}, {self.url}"
        )

    def to_pydantic(self) -> ImageModel:
        format = ImageFormat.fromMediaFormat(self.format)
        if not format:
            raise ValueError(f"Invalid image format: {self.format}")

        return ImageModel(
            width=self.width,
            height=self.height,
            format=format,
            url=self.url,
        )

    @classmethod
    async def from_pydantic(
        cls, model: ImageModel, file_metadata: FileMetadata
    ) -> "Image":
        width = model.width
        height = model.height
        format = model.format.value
        url = model.url

        date_created = file_metadata.date_created or datetime.now(timezone.utc)
        date_updated = file_metadata.date_updated or date_created

        instance: Optional[Image] = (
            await Image.objects()
            .where(
                Image.url == url,
                Image.format == format,
                Image.width == width,
                Image.height == height,
            )
            .first()
            .run()
        )
        if not instance:
            instance = Image(
                # id=cuid.cuid(),
                date_created=date_created,
                date_updated=date_updated,
                width=width,
                height=height,
                format=format,
                url=url,
            )

        return instance
