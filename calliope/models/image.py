from enum import Enum
from typing import Optional

import cuid
from pydantic import BaseModel
from tortoise.models import Model
from tortoise import fields


class ImageFormat(str, Enum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    # Unofficial media types for the RGB565 and Grayscale-16 formats we use...
    GRAYSCALE16 = "image/grayscale16"
    RGB565 = "image/rgb565"

    def fromMediaFormat(mediaFormat: str) -> "ImageFormat":
        if mediaFormat == None:
            return None
        if mediaFormat == "image/raw":
            mediaFormat = "image/rgb565"
        return ImageFormat(mediaFormat)


class ImageModel(BaseModel):
    """
    The high-level attributes of an image.
    """

    width: int
    height: int
    format: ImageFormat
    url: Optional[str] = None


class Image(Model):
    """
    The high-level attributes of an image.
    """

    id = fields.CharField(max_length=50, pk=True, generated=False)
    width = fields.IntField()
    height = fields.IntField()
    format = fields.CharField(max_length=50)
    url = fields.CharField(max_length=500)

    date_created = fields.DatetimeField(auto_now_add=True)
    date_updated = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "image"

    @classmethod
    async def from_pydantic(cls, model: ImageModel) -> "Image":
        width = model.width
        height = model.height
        format = model.format.value
        url = model.url

        instance: Optional[Image] = await Image.get_or_none(
            url=url, format=format, width=width, height=height
        )
        if not instance:
            instance = Image(
                id=cuid.cuid(),
                width=width,
                height=height,
                format=format,
                url=url,
            )

        return instance
