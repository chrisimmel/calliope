from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ImageFormat(str, Enum):
    # RGB565 doesn't have an official media type, but let's use this:
    RGB565 = "image/rgb565"
    PNG = "image/png"
    JPEG = "image/jpeg"

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
