"""Admin dashboard: cross-user monitoring + RBAC moderation actions.

Public surface:
  - routes.router — the /admin/* endpoints, mounted in app.api, gated by
    app.auth.deps.require_admin at the router level (every route under
    /admin/* is protected by construction, not by repeating the check).

See app.services.admin for the underlying queries/mutations.
"""
