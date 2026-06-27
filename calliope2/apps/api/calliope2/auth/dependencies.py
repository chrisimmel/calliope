"""FastAPI dependencies for Firebase auth + the per-request DB session."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from calliope2.auth.firebase import verify_id_token
from calliope2.db.models import User
from calliope2.db.session import get_session

_bearer = HTTPBearer(auto_error=True)


async def get_firebase_claims(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict[str, Any]:
    """Decode the Bearer token. Raises 401 on any verification failure."""
    try:
        return verify_id_token(creds.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid Firebase ID token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    claims: Annotated[dict[str, Any], Depends(get_firebase_claims)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Resolve the Firebase UID to a User row, auto-creating on first sight."""
    uid = claims["uid"]
    user = await session.scalar(select(User).where(User.firebase_uid == uid))
    if user is None:
        try:
            user = User(
                firebase_uid=uid,
                email=claims.get("email"),
                display_name=claims.get("name") or claims.get("display_name"),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        except IntegrityError:
            # Concurrent first request won the race — roll back and re-fetch.
            await session.rollback()
            user = await session.scalar(select(User).where(User.firebase_uid == uid))
    return user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin required")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
