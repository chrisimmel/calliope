from datetime import datetime, timezone
from typing import Optional

import cuid
from piccolo.table import Table
from piccolo.columns import (
    Integer,
    Timestamptz,
    Varchar,
)


from calliope.models import ImageModel
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
    # TODO: Redefine as auto_update as soon as initial migrations are done.
    date_updated = Timestamptz()  # auto_update=datetime.now)

    @classmethod
    async def from_pydantic(
        cls, model: ImageModel, file_metadata: FileMetadata
    ) -> "Image":
        width = model.width
        height = model.height
        format = model.format.value
        url = model.url

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
                date_created=file_metadata.date_created,
                date_updated=file_metadata.date_updated,
                width=width,
                height=height,
                format=format,
                url=url,
            )

        return instance
