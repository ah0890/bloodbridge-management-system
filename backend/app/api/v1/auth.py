from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, client_ip
from app.core.config import get_settings
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    create_session_token,
    decode_session_token,
    rate_limiter,
    verify_password,
)
from app.db.base import utcnow
from app.models import User
from app.schemas.auth import LoginIn, SessionOut, UserOut
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_payload(user: User, csrf: str, expires=None) -> SessionOut:
    return SessionOut(
        user=UserOut.model_validate(user),
        permissions=sorted(p.value for p in ROLE_PERMISSIONS[user.role]),
        csrf_token=csrf,
        expires_at=expires,
    )


@router.post("/login", response_model=SessionOut)
def login(body: LoginIn, request: Request, response: Response, db: DbSession) -> SessionOut:
    settings = get_settings()
    email = body.email.strip().lower()
    ip = client_ip(request)
    if not rate_limiter.hit(f"login:{email}:{ip}", settings.login_max_attempts, settings.login_window_seconds):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts. Try again later.")

    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if not verify_password(body.password, user.password_hash if user else None) or not user or not user.is_active:
        audit.record(db, actor=None, action="auth.login_failed", entity_type="user", summary="Failed login attempt", ip=ip)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")

    rate_limiter.reset(f"login:{email}:{ip}")
    token, csrf, expires = create_session_token(user.id)
    user.last_login_at = utcnow()
    audit.record(db, actor=user, action="auth.login", entity_type="user", entity_id=user.id, summary="Signed in", ip=ip)
    db.commit()

    max_age = settings.session_minutes * 60
    response.set_cookie(
        SESSION_COOKIE, token, max_age=max_age, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/"
    )
    response.set_cookie(
        CSRF_COOKIE, csrf, max_age=max_age, httponly=False, secure=settings.cookie_secure, samesite="lax", path="/"
    )
    return _session_payload(user, csrf, expires)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: CurrentUser, request: Request, response: Response, db: DbSession) -> Response:
    audit.record(db, actor=user, action="auth.logout", entity_type="user", entity_id=user.id, summary="Signed out", ip=client_ip(request))
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return response


@router.get("/me", response_model=SessionOut)
def me(user: CurrentUser, request: Request) -> SessionOut:
    claims = decode_session_token(request.cookies.get(SESSION_COOKIE, "")) or {}
    return _session_payload(user, claims.get("csrf", ""))
