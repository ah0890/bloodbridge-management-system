"""Password hashing, session tokens and CSRF helpers.

Session strategy: a signed JWT is stored in an HttpOnly, SameSite=Lax cookie. Each session also
carries a random CSRF token that is embedded in the JWT and mirrored in a JS-readable cookie; every
state-changing request must echo it in the ``X-CSRF-Token`` header (double-submit, bound to session).
"""

import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

SESSION_COOKIE = "bb_session"
CSRF_COOKIE = "bb_csrf"
CSRF_HEADER = "X-CSRF-Token"
_ALGORITHM = "HS256"

_hasher = PasswordHasher()
# Used to equalise timing when the account does not exist.
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def create_session_token(user_id: int) -> tuple[str, str, datetime]:
    settings = get_settings()
    csrf = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(minutes=settings.session_minutes)
    payload = {"sub": str(user_id), "csrf": csrf, "exp": expires, "iat": datetime.now(UTC)}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM), csrf, expires


def decode_session_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None


def csrf_matches(expected: str | None, provided: str | None) -> bool:
    return bool(expected and provided) and hmac.compare_digest(expected, provided)


class RateLimiter:
    """Small in-process sliding-window limiter.

    Adequate for a single-process deployment; a multi-instance deployment needs a shared store.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record an attempt; return False when the key is over its limit."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


rate_limiter = RateLimiter()
