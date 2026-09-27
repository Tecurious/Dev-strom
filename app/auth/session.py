"""JWT session token + cookie helpers.

The session is a stateless HS256 JWT. Normal payload: ``sub`` (user id).
While an admin is impersonating another user the cookie also carries
``imp`` (the admin's user id). Logout clears the cookie — there is no
server-side session store.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Response

from app.config import settings

COOKIE_NAME = "ds_session"
_ALGO = "HS256"


class SessionError(Exception):
    """Raised when a session token is missing, malformed, or expired."""


@dataclass(frozen=True)
class SessionClaims:
    user_id: uuid.UUID
    impersonator_id: uuid.UUID | None = None


def _secret() -> str:
    if not settings.session_secret:
        raise RuntimeError(
            "SESSION_SECRET is not set — required when AUTH_ENABLED=true."
        )
    return settings.session_secret


def issue_token(
    user_id: uuid.UUID,
    *,
    impersonator_id: uuid.UUID | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.session_ttl_days)).timestamp()),
    }
    if impersonator_id is not None:
        payload["imp"] = str(impersonator_id)
    return jwt.encode(payload, _secret(), algorithm=_ALGO)


def read_token(token: str) -> uuid.UUID:
    """Back-compat: return only the effective user id (``sub``)."""
    return read_claims(token).user_id


def read_claims(token: str) -> SessionClaims:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_ALGO])
        user_id = uuid.UUID(payload["sub"])
        imp_raw = payload.get("imp")
        impersonator_id = uuid.UUID(imp_raw) if imp_raw else None
        return SessionClaims(user_id=user_id, impersonator_id=impersonator_id)
    except (jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise SessionError(str(exc)) from exc


def set_session_cookie(
    response: Response,
    user_id: uuid.UUID,
    *,
    impersonator_id: uuid.UUID | None = None,
) -> None:
    response.set_cookie(
        COOKIE_NAME,
        issue_token(user_id, impersonator_id=impersonator_id),
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", samesite="lax")
