"""Durable media storage.

Generated media comes back from providers as either raw bytes (OpenAI) or a
*temporary* delivery URL (Replicate — these expire within hours). Persisting the
provider URL verbatim means images vanish once the URL expires. This module
copies generated media into our own GCS bucket (public-read) and returns a
stable ``gs://`` URI, which the API then serves via
``media_urls.to_media_url`` → ``https://storage.googleapis.com/...``.

Everything here is **fail-safe**: if no bucket is configured (dev) or any step
fails, ``persist_media`` returns ``None`` and the caller falls back to the
provider URL. Storage problems must never break frame generation.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging

import httpx

from calliope2.settings import get_settings

logger = logging.getLogger(__name__)

_PREFIX = "media/v3"


def _get_bucket():
    settings = get_settings()
    if not settings.gcs_bucket:
        return None
    # Local import: google-cloud-storage is heavy and only needed in prod.
    from google.cloud import storage

    return storage.Client().bucket(settings.gcs_bucket)


def _upload(bucket, data: bytes, blob_name: str, content_type: str) -> None:
    blob = bucket.blob(blob_name)
    if not blob.exists():  # content-addressed → idempotent
        blob.upload_from_string(data, content_type=content_type)


async def _fetch(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


async def persist_media(
    *,
    data: bytes | None,
    url: str | None,
    kind: str,  # "image" | "video"
    fmt: str | None,
) -> str | None:
    """Copy generated media into our bucket; return a durable ``gs://`` URI, or
    ``None`` to signal the caller should fall back to the provider URL.

    Content-addressed by SHA-256, so re-persisting identical bytes is a no-op.
    Never raises.
    """
    try:
        bucket = _get_bucket()
        if bucket is None:
            return None
        if data is None and url is not None:
            data = await _fetch(url)
        if not data:
            return None
        ext = (fmt or ("png" if kind == "image" else "mp4")).lower()
        content_type = f"{'image' if kind == 'image' else 'video'}/{ext}"
        digest = hashlib.sha256(data).hexdigest()
        blob_name = f"{_PREFIX}/{digest}.{ext}"
        await asyncio.to_thread(_upload, bucket, data, blob_name, content_type)
        return f"gs://{bucket.name}/{blob_name}"
    except Exception as e:
        logger.warning("media storage failed (%s); falling back to provider URL: %s", kind, e)
        return None
