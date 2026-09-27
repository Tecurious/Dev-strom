"""FastAPI dependencies for the current user.

`require_user` is attached to every data route. Behaviour:
  - AUTH_ENABLED=false  → always the seeded anonymous user (local dev).
  - AUTH_ENABLED=true   → decode the session cookie; 401 if missing/invalid.

`require_admin` layers on top for the admin dashboard — 403 unless the
*acting* principal is an admin. While impersonating, the actor is the
admin in the JWT ``imp`` claim, not the viewed user.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request

from app.auth import service, session
from app.config import settings
from app.services.models import ANONYMOUS_USER_ID

_ANON = {
    "id": str(ANONYMOUS_USER_ID),
    "email": "anonymous@devstrom.local",
    "name": "Anonymous",
    "avatar_url": None,
    "auth_provider": "system",
    "created_at": None,
    "role": "system",
    "is_active": True,
    "impersonator": None,
}


def require_user(request: Request) -> dict:
    """Return the effective user dict (the viewed account when impersonating)."""
    if not settings.auth_enabled:
        return dict(_ANON)

    token = request.cookies.get(session.COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        claims = session.read_claims(token)
    except session.SessionError:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    user = service.get_user(claims.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="This account has been deactivated.")

    impersonator = None
    if claims.impersonator_id is not None:
        admin = service.get_user(claims.impersonator_id)
        if admin is None or admin.get("role") != "admin" or not admin.get("is_active", True):
            raise HTTPException(status_code=401, detail="Impersonation session is no longer valid")
        impersonator = {
            "id": admin["id"],
            "email": admin["email"],
            "name": admin["name"],
        }
    user["impersonator"] = impersonator
    return user


def require_admin(user: dict = Depends(require_user)) -> dict:
    """403 unless the acting principal is an admin.

    During impersonation the acting principal is the admin in ``impersonator``,
    so /admin/* stays reachable (e.g. to stop viewing as another user).
    """
    actor = user.get("impersonator")
    if actor is not None:
        # Impersonator was already verified as an active admin in require_user.
        return service.get_user(uuid.UUID(actor["id"])) or user
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def current_user_id(request: Request) -> uuid.UUID:
    return uuid.UUID(require_user(request)["id"])
