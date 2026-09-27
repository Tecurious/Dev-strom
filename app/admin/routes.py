"""/admin/* endpoints: cross-user stats, requests, and moderation actions.

Every route in this router requires an admin (see the router-level
`dependencies=` below) — this is the FastAPI-idiomatic way to guarantee the
check runs on every endpoint by construction, rather than repeating
`Depends(require_admin)` on each one and risking forgetting it somewhere.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth.deps import require_admin, require_user
from app.models.dto import SetActiveRequest, SetRoleRequest
from app.services import admin as admin_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/stats")
def get_stats() -> dict:
    """Summary counts for the dashboard's stat cards."""
    return admin_service.get_dashboard_stats()


@router.get("/requests")
def list_requests(limit: int = 50, offset: int = 0, kind: str | None = None) -> dict:
    """Merged idea-run + analysis feed across every user, newest first."""
    if kind is not None and kind not in ("idea", "analysis"):
        raise HTTPException(400, "kind must be 'idea' or 'analysis' if given.")
    limit = min(max(limit, 1), 200)
    requests = admin_service.list_all_requests(limit=limit, offset=offset, kind=kind)
    return {"requests": requests, "limit": limit, "offset": offset}


@router.get("/users")
def list_users(limit: int = 50, offset: int = 0) -> dict:
    limit = min(max(limit, 1), 200)
    return {"users": admin_service.list_users(limit=limit, offset=offset), "limit": limit, "offset": offset}


@router.put("/users/{user_id}/role")
def set_role(user_id: uuid.UUID, body: SetRoleRequest, admin: dict = Depends(require_admin)) -> dict:
    admin_id = uuid.UUID(admin["id"])
    try:
        result = admin_service.set_user_role(admin_id=admin_id, target_id=user_id, role=body.role)
    except admin_service.LastAdminError as exc:
        raise HTTPException(409, str(exc))
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    logger.warning("admin %s set role=%s for user %s", admin_id, body.role, user_id)
    return result


@router.put("/users/{user_id}/active")
def set_active(user_id: uuid.UUID, body: SetActiveRequest, admin: dict = Depends(require_admin)) -> dict:
    admin_id = uuid.UUID(admin["id"])
    try:
        result = admin_service.set_user_active(admin_id=admin_id, target_id=user_id, is_active=body.is_active)
    except admin_service.SelfDeactivationError as exc:
        raise HTTPException(409, str(exc))
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    logger.warning("admin %s set is_active=%s for user %s", admin_id, body.is_active, user_id)
    return result


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: str, admin: dict = Depends(require_admin)):
    if not admin_service.delete_run_admin(run_id=run_id):
        raise HTTPException(404, f"Run {run_id} not found.")
    logger.warning("admin %s deleted run %s", admin["id"], run_id)


@router.delete("/analyses/{run_id}", status_code=204)
def delete_analysis(run_id: str, admin: dict = Depends(require_admin)):
    if not admin_service.delete_analysis_admin(run_id=run_id):
        raise HTTPException(404, f"Analysis {run_id} not found.")
    logger.warning("admin %s deleted analysis %s", admin["id"], run_id)


@router.post("/users/{user_id}/impersonate")
def start_impersonate(
    user_id: uuid.UUID,
    response: Response,
    admin: dict = Depends(require_admin),
    viewer: dict = Depends(require_user),
) -> dict:
    """Switch the session cookie to ``user_id`` while remembering the admin.

    Blocks impersonating yourself, other admins, or inactive accounts.
    Refuse if already impersonating — stop first.
    """
    from app.auth import session as session_mod
    from app.auth import service as auth_service

    if viewer.get("impersonator") is not None:
        raise HTTPException(409, "Already impersonating — stop first.")
    if user_id == uuid.UUID(admin["id"]):
        raise HTTPException(400, "Cannot impersonate yourself.")
    target = auth_service.get_user(user_id)
    if target is None:
        raise HTTPException(404, f"User {user_id} not found.")
    if target.get("role") == "admin":
        raise HTTPException(403, "Cannot impersonate another admin.")
    if not target.get("is_active", True):
        raise HTTPException(400, "Cannot impersonate a deactivated account.")

    session_mod.set_session_cookie(
        response,
        user_id,
        impersonator_id=uuid.UUID(admin["id"]),
    )
    logger.warning("admin %s started impersonating user %s", admin["id"], user_id)
    target["impersonator"] = {
        "id": admin["id"],
        "email": admin["email"],
        "name": admin.get("name"),
    }
    return target


@router.post("/impersonate/stop")
def stop_impersonate(
    response: Response,
    admin: dict = Depends(require_admin),
    viewer: dict = Depends(require_user),
) -> dict:
    """Restore the admin's own session cookie after viewing as another user."""
    from app.auth import session as session_mod

    if viewer.get("impersonator") is None:
        raise HTTPException(400, "Not currently impersonating.")
    session_mod.set_session_cookie(response, uuid.UUID(admin["id"]))
    logger.warning("admin %s stopped impersonating user %s", admin["id"], viewer["id"])
    admin_out = dict(admin)
    admin_out["impersonator"] = None
    return admin_out
