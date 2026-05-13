"""Firebase ID-token verification.

Initialized lazily on first call. In production, credentials come from
``GOOGLE_APPLICATION_CREDENTIALS`` (the Cloud Run convention) or an explicit
service-account JSON. In tests, the verification function is replaced via
``app.dependency_overrides`` — `firebase_admin` is never invoked.
"""

from __future__ import annotations

from typing import Any

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials

from calliope2.settings import get_settings

_app: firebase_admin.App | None = None


def _get_app() -> firebase_admin.App:
    global _app
    if _app is not None:
        return _app
    if firebase_admin._apps:
        _app = firebase_admin.get_app()
        return _app
    settings = get_settings()
    options: dict[str, Any] = {}
    if settings.firebase_project_id:
        options["projectId"] = settings.firebase_project_id
    _app = firebase_admin.initialize_app(credentials.ApplicationDefault(), options)
    return _app


def verify_id_token(id_token: str) -> dict[str, Any]:
    """Verify a Firebase ID token and return the decoded claims.

    Raises ``firebase_admin.auth.InvalidIdTokenError`` (and subclasses) on
    bad tokens; the calling FastAPI dependency converts those to HTTP 401.
    """
    return fb_auth.verify_id_token(id_token, app=_get_app())
