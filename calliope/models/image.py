from enum import Enum
from typing import Optional

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

    id = fields.CharField(max_length=50, pk=True, generate=False)
    width = fields.IntField()
    height = fields.IntField()
    format = fields.CharField(max_length=50)
    url = fields.CharField(max_length=500)

    class Meta:
        table = "image"

    @classmethod
    async def from_pydantic(cls, model: ImageModel) -> "Image":
        id = model.id
        width = model.width
        height = model.height
        format = model.format.value
        url = model.url

        instance: Image = await Image.get_or_none(id=id)
        if instance:
            instance.width = width
            instance.height = height
            instance.format = format
            instance.url = url
        else:
            instance = Image(
                id=id,
                width=width,
                height=height,
                format=format,
                url=url,
            )

        return instance
