from dataclasses import dataclass


@dataclass(slots=True)
class ImageBlob:
    """A generated or referenced image, by bytes and/or URL.

    At least one of `data` or `url` must be set. Persistence (GCS upload,
    `Image` row creation) is the caller's responsibility.
    """

    data: bytes | None = None
    url: str | None = None
    format: str | None = None
    width: int | None = None
    height: int | None = None

    def __post_init__(self) -> None:
        if self.data is None and self.url is None:
            raise ValueError("ImageBlob requires either `data` or `url`")


@dataclass(slots=True)
class VideoBlob:
    """A generated video, by bytes and/or URL."""

    data: bytes | None = None
    url: str | None = None
    format: str | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    frame_rate: float | None = None

    def __post_init__(self) -> None:
        if self.data is None and self.url is None:
            raise ValueError("VideoBlob requires either `data` or `url`")
