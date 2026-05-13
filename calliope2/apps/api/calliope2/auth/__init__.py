"""Firebase-based auth: token verification + the FastAPI dependencies used by /v3."""

from calliope2.auth.dependencies import (
    AdminUser,
    CurrentUser,
    SessionDep,
    get_current_user,
    get_firebase_claims,
    require_admin,
)
from calliope2.auth.firebase import verify_id_token

__all__ = [
    "AdminUser",
    "CurrentUser",
    "SessionDep",
    "get_current_user",
    "get_firebase_claims",
    "require_admin",
    "verify_id_token",
]
