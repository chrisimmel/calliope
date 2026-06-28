"""Media-input ingestion: data URLs (in-browser captures) and plain URLs."""

import base64

import pytest

from calliope2.api.v3.tasks import (
    _audio_blob_from_input,
    _image_blob_from_input,
    _prepare_inputs,
)


def test_plain_url_becomes_url_blob():
    blob = _image_blob_from_input("https://example.com/photo.jpg")
    assert blob.url == "https://example.com/photo.jpg"
    assert blob.data is None


def test_data_url_is_decoded_to_bytes():
    raw = b"\x89PNG\r\n fake bytes"
    data_url = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    blob = _image_blob_from_input(data_url)
    assert blob.url is None
    assert blob.data == raw
    assert blob.format == "png"


def test_data_url_jpeg_format():
    data_url = "data:image/jpeg;base64," + base64.b64encode(b"x").decode("ascii")
    assert _image_blob_from_input(data_url).format == "jpeg"


def test_prepare_inputs_coerces_source_image_url():
    data_url = "data:image/webp;base64," + base64.b64encode(b"y").decode("ascii")
    prepared = _prepare_inputs({"source_image_url": data_url, "theme": "dusk"})
    assert "source_image_url" not in prepared
    assert prepared["theme"] == "dusk"
    assert prepared["source_image"].data == b"y"
    assert prepared["source_image"].format == "webp"


def test_audio_data_url_is_decoded_to_bytes():
    raw = b"OggS fake audio"
    data_url = "data:audio/webm;base64," + base64.b64encode(raw).decode("ascii")
    blob = _audio_blob_from_input(data_url)
    assert blob.url is None
    assert blob.data == raw
    assert blob.format == "webm"


def test_audio_plain_url_becomes_url_blob():
    blob = _audio_blob_from_input("https://example.com/clip.mp3")
    assert blob.url == "https://example.com/clip.mp3"
    assert blob.data is None


def test_prepare_inputs_coerces_source_audio_url():
    data_url = "data:audio/mp4;base64," + base64.b64encode(b"z").decode("ascii")
    prepared = _prepare_inputs({"source_audio_url": data_url})
    assert "source_audio_url" not in prepared
    assert prepared["source_audio"].data == b"z"
    assert prepared["source_audio"].format == "mp4"


def test_non_base64_data_url_raises():
    # Browser captures are always base64; a non-base64 data URL is rejected
    # rather than silently mis-decoded.
    with pytest.raises(ValueError, match="base64"):
        _image_blob_from_input("data:image/png,not-base64-data")
