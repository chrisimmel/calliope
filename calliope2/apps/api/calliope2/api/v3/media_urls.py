"""Normalize stored media references into browser-loadable URLs.

Image/Video rows store a ``gcs_uri`` column, but its contents are heterogeneous:

* **Newly generated media** persists the provider's delivery URL verbatim —
  today an ``https://`` URL (e.g. Replicate). These are already loadable by an
  ``<img>``/``<video>`` and pass through unchanged.
* **Migrated v1/v2 rows** may hold a ``gs://bucket/path`` URI, which a browser
  cannot fetch; we rewrite those to the public GCS HTTPS form.

There is intentionally no streaming proxy: the storage layer that would copy
media into our own bucket isn't built yet (``calliope2.storage`` is a stub), so
a proxy would merely re-fetch the same external URL without adding durability.
When that storage phase lands and ``gcs_uri`` becomes a real ``gs://`` in our
bucket, this helper is the single place to switch to signed URLs or a proxy.
"""

from __future__ import annotations

_GCS_PUBLIC_HOST = "https://storage.googleapis.com"


def to_media_url(gcs_uri: str | None) -> str | None:
    """Return a browser-loadable URL for a stored media reference, or None."""
    if not gcs_uri:
        return None
    if gcs_uri.startswith(("http://", "https://")):
        return gcs_uri
    if gcs_uri.startswith("gs://"):
        # gs://bucket/path/to/object → https://storage.googleapis.com/bucket/path/to/object
        return f"{_GCS_PUBLIC_HOST}/{gcs_uri[len('gs://') :]}"
    # Unknown/relative form — return as-is and let the caller's origin resolve it.
    return gcs_uri
