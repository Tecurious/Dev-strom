"""Admin dashboard: cross-user listings, moderation actions, and stats.

Distinct from app.auth.service, which is scoped to auth identity/session
concerns — this module is user *moderation* (role/active) plus the
cross-user views only an admin (app.auth.deps.require_admin) can reach.
Follows the same get_session()/ORM idiom as app.services.run_service and
app.cartographer.analysis_store.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.cartographer.analysis_store import PostgresJsonbStore
from app.services.db import get_session
from app.services.jobs import JobStatus
from app.services.models import AnalysisRun, Job, Run, User
from app.services.run_service import load_history
from app.services.slugs import get_by_public_id

_analysis_store = PostgresJsonbStore()


class LastAdminError(Exception):
    """Revoking this role change would leave the system with zero admins."""


class SelfDeactivationError(Exception):
    """An admin tried to deactivate their own account."""


def list_users(*, limit: int = 50, offset: int = 0) -> list[dict]:
    with get_session() as session:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        rows = session.execute(stmt).scalars().all()
        return [_user_to_dict(u) for u in rows]


def set_user_role(*, admin_id: uuid.UUID, target_id: uuid.UUID, role: str) -> dict:
    """Raises LastAdminError rather than letting the system end up with zero
    admins — an unrecoverable-without-DB-access lockout."""
    with get_session() as session:
        target = session.get(User, target_id)
        if target is None:
            raise ValueError(f"User {target_id} not found.")
        if target_id == admin_id and role != "admin":
            admin_count = session.execute(
                select(func.count()).select_from(User).where(User.role == "admin")
            ).scalar_one()
            if admin_count <= 1:
                raise LastAdminError("Cannot revoke the last remaining admin's role.")
        target.role = role
        session.flush()
        return _user_to_dict(target)


def set_user_active(*, admin_id: uuid.UUID, target_id: uuid.UUID, is_active: bool) -> dict:
    """Raises SelfDeactivationError before touching the DB — an admin
    locking themselves out has no recovery path short of DB access."""
    if target_id == admin_id and not is_active:
        raise SelfDeactivationError("Cannot deactivate your own account.")
    with get_session() as session:
        target = session.get(User, target_id)
        if target is None:
            raise ValueError(f"User {target_id} not found.")
        target.is_active = is_active
        session.flush()
        return _user_to_dict(target)


def delete_run_admin(*, run_id: str) -> bool:
    """Hard delete (matches this schema's CASCADE-everywhere philosophy —
    no soft-delete column exists anywhere in the design). Returns False if
    the run doesn't exist, for the route to turn into a 404."""
    with get_session() as session:
        run = get_by_public_id(session, Run, run_id)
        if run is None:
            return False
        session.delete(run)
        return True


def delete_analysis_admin(*, run_id: str) -> bool:
    with get_session() as session:
        row = get_by_public_id(session, AnalysisRun, run_id)
        if row is None:
            return False
        session.delete(row)
        return True


def get_dashboard_stats() -> dict:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    with get_session() as session:
        total_users = session.execute(select(func.count()).select_from(User)).scalar_one()
        runs_today = session.execute(
            select(func.count()).select_from(Run).where(Run.created_at >= today_start)
        ).scalar_one()
        analyses_today = session.execute(
            select(func.count()).select_from(AnalysisRun).where(AnalysisRun.created_at >= today_start)
        ).scalar_one()
        job_counts = dict(session.execute(select(Job.status, func.count()).group_by(Job.status)).all())
    return {
        "total_users": total_users,
        "runs_today": runs_today,
        "analyses_today": analyses_today,
        "jobs_pending": job_counts.get(JobStatus.PENDING.value, 0),
        "jobs_running": job_counts.get(JobStatus.RUNNING.value, 0),
        "jobs_failed": job_counts.get(JobStatus.ERROR.value, 0),
    }


def list_all_requests(*, limit: int = 50, offset: int = 0, kind: str | None = None) -> list[dict]:
    """Merged idea-run + analysis feed across every user, newest first, each
    row tagged kind="idea"|"analysis" and carrying the owner's email.

    Fetches both sources and merges/sorts in Python rather than a SQL UNION
    — simple and correct at admin-dashboard scale (limit is capped at 200
    by the route); revisit with a real UNION query if this ever needs to
    page through serious volume.
    """
    rows: list[dict] = []
    if kind in (None, "idea"):
        for r in load_history(user_id=None, limit=offset + limit, offset=0):
            r["kind"] = "idea"
            r["summary"] = r["tech_stack"]
            rows.append(r)
    if kind in (None, "analysis"):
        for r in _analysis_store.list_runs(limit=offset + limit, offset=0, owner_id=None):
            r["kind"] = "analysis"
            r["summary"] = r["repo_url"]
            rows.append(r)
    rows.sort(key=lambda r: r["created_at"], reverse=True)
    page = rows[offset : offset + limit]

    ids = {uuid.UUID(r["user_id"]) for r in page if r.get("user_id")}
    emails = _emails_for(ids)
    for r in page:
        r["email"] = emails.get(uuid.UUID(r["user_id"])) if r.get("user_id") else None
    return page


def _emails_for(user_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Batch email lookup — avoids an N+1 query per row in list_all_requests."""
    if not user_ids:
        return {}
    with get_session() as session:
        rows = session.execute(select(User.id, User.email).where(User.id.in_(user_ids))).all()
        return {row.id: row.email for row in rows}


def _user_to_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }
