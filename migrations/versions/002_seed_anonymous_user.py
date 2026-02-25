"""Seed anonymous user.

Inserts a well-known anonymous user row into the `users` table so that
all runs can satisfy the foreign key constraint before auth is implemented.
This is idempotent — running it multiple times is safe.

Revision: 002
"""

import sqlalchemy as sa
from alembic import op

revision = "002_seed_anonymous_user"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None

# Must match services/models.py → ANONYMOUS_USER_ID
_ANON_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO users (id, google_id, email, name)
            VALUES (:id, :google_id, :email, :name)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(
            id=_ANON_ID,
            google_id="anonymous",
            email="anonymous@devstrom.local",
            name="Anonymous",
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM users WHERE id = :id").bindparams(id=_ANON_ID)
    )
