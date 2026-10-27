from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.permissions import Perm, has_perm
from app.core.security import CSRF_HEADER, SESSION_COOKIE, csrf_matches, decode_session_token
from app.db.session import get_db
from app.models import User
from app.models.enums import Provenance, Role

DbSession = Annotated[Session, Depends(get_db)]

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    claims = decode_session_token(token) if token else None
    if not claims:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required.")
    if request.method not in _SAFE_METHODS and not csrf_matches(claims.get("csrf"), request.headers.get(CSRF_HEADER)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token.")
    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require(*perms: Perm) -> Callable[[User], User]:
    """Dependency factory enforcing that the current user holds every listed permission."""

    def _dep(user: CurrentUser) -> User:
        if not all(has_perm(user.role, p) for p in perms):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission for this action.")
        return user

    return _dep


def org_scope(user: User) -> int | None:
    """Organisation a user is confined to, or None for platform-wide roles."""
    return user.blood_bank_id if user.role == Role.BANK_MANAGER else None


def ensure_org_access(user: User, blood_bank_id: int) -> None:
    scope = org_scope(user)
    if scope is not None and scope != blood_bank_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This record belongs to another organisation.")


def record_provenance(user: User) -> Provenance:
    """Records created by demo staff accounts stay labelled synthetic so they never mix with real data."""
    return Provenance.SYNTHETIC if user.is_demo else Provenance.VERIFIED
