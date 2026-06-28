"""Unit tests for media URL normalization."""

from calliope2.api.v3.media_urls import to_media_url


def test_passes_through_https():
    assert to_media_url("https://replicate.delivery/x.png") == "https://replicate.delivery/x.png"


def test_passes_through_http():
    assert to_media_url("http://example.com/a.jpg") == "http://example.com/a.jpg"


def test_rewrites_gs_to_public_https():
    assert to_media_url("gs://my-bucket/path/to/img.png") == (
        "https://storage.googleapis.com/my-bucket/path/to/img.png"
    )


def test_none_and_empty():
    assert to_media_url(None) is None
    assert to_media_url("") is None
