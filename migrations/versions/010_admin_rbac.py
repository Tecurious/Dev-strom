"""Admin RBAC: role + is_active on users.

- users.role: TEXT, default 'user'. Plain text rather than a Postgres enum,
  matching this codebase's existing convention for small fixed value sets
  (see 005_jobs's Job.status). Checked by app.auth.deps.require_admin.
- users.is_active: BOOLEAN, default true. A deactivated/banned account
  fails app.auth.deps.require_user on every gated route, not just admin
  ones.

Revision: 010
"""

import sqlalchemy as sa
from alembic import op

revision = "010_admin_rbac"
down_revision = "009_drop_legacy_run_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.Text, nullable=False, server_default="user"))
    op.add_column("users", sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("users", "is_active")
    op.drop_column("users", "role")
