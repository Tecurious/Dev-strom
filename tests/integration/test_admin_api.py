"""/admin/* endpoints: the require_admin gate, and each moderation action."""

import uuid

import pytest

from app import api as api_module
from app.admin import routes as admin_routes_module
from app.auth import deps as deps_module
from app.auth import session as session_module
from app.services import admin as admin_service


@pytest.fixture()
def auth_on(monkeypatch):
    """Enable the login gate with a known session secret (same shape as
    test_auth_api.py's fixture of the same name — not shared via conftest,
    matching that file's own precedent). deps_module.settings and
    session_module.settings are the same app.config.settings singleton, so
    patching it once covers both require_user's check and session.py's
    token signing."""
    monkeypatch.setattr(deps_module.settings, "auth_enabled", True, raising=False)
    monkeypatch.setattr(deps_module.settings, "session_secret",
                         "integration-secret-at-least-32-bytes-padded", raising=False)
    return "integration-secret-at-least-32-bytes-padded"


def _cookie_for(user_id: str) -> dict:
    return {session_module.COOKIE_NAME: session_module.issue_token(uuid.UUID(user_id))}


def _user(uid: str, *, role: str = "user", is_active: bool = True) -> dict:
    return {
        "id": uid, "email": f"{uid}@example.com", "name": "Test User", "avatar_url": None,
        "auth_provider": "google", "created_at": "2026-01-01T00:00:00+00:00",
        "role": role, "is_active": is_active,
    }


def _sign_in_as(monkeypatch, *, role: str = "user", is_active: bool = True) -> dict:
    """Monkeypatch service.get_user to return a fixed user for any id, and
    return {cookies: ...} ready to pass to the test client."""
    uid = str(uuid.uuid4())
    monkeypatch.setattr(deps_module.service, "get_user", lambda _id: _user(uid, role=role, is_active=is_active))
    return {"uid": uid, "cookies": _cookie_for(uid)}


# ── require_admin gate ───────────────────────────────────────────────────────

def test_non_admin_403_on_stats(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="user")
    assert client.get("/admin/stats", cookies=sess["cookies"]).status_code == 403


def test_anonymous_403_when_auth_disabled(client, monkeypatch):
    # AUTH_ENABLED=false (the suite's default) -> every request is the
    # seeded anonymous user, role="system", never admin.
    assert client.get("/admin/stats").status_code == 403


def test_unauthenticated_401_before_403(client, auth_on):
    # No session cookie at all -> require_user's 401 fires before
    # require_admin's role check ever runs.
    assert client.get("/admin/stats").status_code == 401


def test_deactivated_user_401_on_any_gated_route_not_just_admin(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="user", is_active=False)
    monkeypatch.setattr(api_module, "load_history", lambda **kw: [])
    resp = client.get("/history", cookies=sess["cookies"])
    assert resp.status_code == 401
    assert "deactivated" in resp.json()["detail"].lower()


def test_admin_can_reach_stats(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="admin")
    monkeypatch.setattr(admin_routes_module.admin_service, "get_dashboard_stats",
                         lambda: {"total_users": 3, "runs_today": 1, "analyses_today": 0,
                                  "jobs_pending": 0, "jobs_running": 0, "jobs_failed": 0})
    resp = client.get("/admin/stats", cookies=sess["cookies"])
    assert resp.status_code == 200
    assert resp.json()["total_users"] == 3


# ── requests listing ─────────────────────────────────────────────────────────

def test_list_requests_tags_kind_and_owner_email(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="admin")
    rows = [{"run_id": "r1", "user_id": str(uuid.uuid4()), "kind": "idea",
             "summary": "FastAPI backend", "email": "a@b.c", "created_at": "2026-01-02T00:00:00+00:00"}]
    monkeypatch.setattr(admin_routes_module.admin_service, "list_all_requests", lambda **kw: rows)
    resp = client.get("/admin/requests", cookies=sess["cookies"])
    assert resp.status_code == 200
    assert resp.json()["requests"] == rows


def test_list_requests_rejects_bad_kind(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="admin")
    resp = client.get("/admin/requests", params={"kind": "bogus"}, cookies=sess["cookies"])
    assert resp.status_code == 400


# ── role / active mutations ──────────────────────────────────────────────────

def test_set_role_last_admin_guard_returns_409_not_500(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="admin")

    def _raise_last_admin(**kw):
        raise admin_service.LastAdminError("Cannot revoke the last remaining admin's role.")

    monkeypatch.setattr(admin_routes_module.admin_service, "set_user_role", _raise_last_admin)
    resp = client.put(f"/admin/users/{sess['uid']}/role", json={"role": "user"}, cookies=sess["cookies"])
    assert resp.status_code == 409


def test_set_active_self_deactivation_guard_returns_409(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="admin")

    def _raise_self_deactivate(**kw):
        raise admin_service.SelfDeactivationError("Cannot deactivate your own account.")

    monkeypatch.setattr(admin_routes_module.admin_service, "set_user_active", _raise_self_deactivate)
    resp = client.put(f"/admin/users/{sess['uid']}/active", json={"is_active": False}, cookies=sess["cookies"])
    assert resp.status_code == 409


def test_set_role_unknown_user_404(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="admin")

    def _raise_not_found(**kw):
        raise ValueError("not found")

    monkeypatch.setattr(admin_routes_module.admin_service, "set_user_role", _raise_not_found)
    resp = client.put(f"/admin/users/{uuid.uuid4()}/role", json={"role": "admin"}, cookies=sess["cookies"])
    assert resp.status_code == 404


# ── deletes ───────────────────────────────────────────────────────────────────

def test_delete_run_204_when_found(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="admin")
    monkeypatch.setattr(admin_routes_module.admin_service, "delete_run_admin", lambda **kw: True)
    resp = client.delete("/admin/runs/some-run", cookies=sess["cookies"])
    assert resp.status_code == 204


def test_delete_run_404_when_missing(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="admin")
    monkeypatch.setattr(admin_routes_module.admin_service, "delete_run_admin", lambda **kw: False)
    resp = client.delete("/admin/runs/nope", cookies=sess["cookies"])
    assert resp.status_code == 404


def test_delete_analysis_204_when_found(client, auth_on, monkeypatch):
    sess = _sign_in_as(monkeypatch, role="admin")
    monkeypatch.setattr(admin_routes_module.admin_service, "delete_analysis_admin", lambda **kw: True)
    resp = client.delete("/admin/analyses/some-run", cookies=sess["cookies"])
    assert resp.status_code == 204


def test_impersonate_sets_cookie_with_imp_claim(client, auth_on, monkeypatch):
    admin = _sign_in_as(monkeypatch, role="admin")
    target_id = uuid.uuid4()
    target = _user(str(target_id), role="user")

    def _get(uid):
        if uid == uuid.UUID(admin["uid"]):
            return _user(admin["uid"], role="admin")
        if uid == target_id:
            return target
        return None

    monkeypatch.setattr(deps_module.service, "get_user", _get)
    resp = client.post(f"/admin/users/{target_id}/impersonate", cookies=admin["cookies"])
    assert resp.status_code == 200
    assert resp.json()["id"] == str(target_id)
    assert resp.json()["impersonator"]["id"] == admin["uid"]
    cookie = resp.cookies.get(session_module.COOKIE_NAME)
    assert cookie
    claims = session_module.read_claims(cookie)
    assert claims.user_id == target_id
    assert claims.impersonator_id == uuid.UUID(admin["uid"])


def test_impersonate_blocks_other_admin(client, auth_on, monkeypatch):
    admin = _sign_in_as(monkeypatch, role="admin")
    other_id = uuid.uuid4()

    def _get(uid):
        if uid == uuid.UUID(admin["uid"]):
            return _user(admin["uid"], role="admin")
        if uid == other_id:
            return _user(str(other_id), role="admin")
        return None

    monkeypatch.setattr(deps_module.service, "get_user", _get)
    resp = client.post(f"/admin/users/{other_id}/impersonate", cookies=admin["cookies"])
    assert resp.status_code == 403
