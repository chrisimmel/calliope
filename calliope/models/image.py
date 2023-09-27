from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ImageFormat(str, Enum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    # Unofficial media types for the RGB565 and Grayscale-16 formats we use...
    GRAYSCALE16 = "image/grayscale16"
    RGB565 = "image/rgb565"

    def fromMediaFormat(mediaFormat: Optional[str]) -> Optional["ImageFormat"]:
        if mediaFormat is None:
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
