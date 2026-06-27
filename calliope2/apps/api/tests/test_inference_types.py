import pytest

from calliope2.inference import ImageBlob, VideoBlob


def test_image_blob_requires_data_or_url():
    with pytest.raises(ValueError):
        ImageBlob()

    ImageBlob(data=b"\x89PNG", format="png")
    ImageBlob(url="https://example.com/x.png")


def test_video_blob_requires_data_or_url():
    with pytest.raises(ValueError):
        VideoBlob()

    VideoBlob(url="https://example.com/v.mp4", duration_seconds=4.0)
