from enum import Enum
from typing import Optional

from pydantic import BaseModel


class VideoFormat(str, Enum):
    MP4 = "video/mp4"
    WEBM = "video/webm"
    MOV = "video/quicktime"

    def fromMediaFormat(mediaFormat: Optional[str]) -> Optional["VideoFormat"]:
        if mediaFormat is None:
            return None
        return VideoFormat(mediaFormat)


class VideoModel(BaseModel):
    """
    The high-level attributes of a video.
    """

    width: int
    height: int
    format: VideoFormat
    url: Optional[str] = None
    duration_seconds: Optional[float] = None  # Duration in seconds
    frame_rate: Optional[float] = None  # Frames per second