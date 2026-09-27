"""Drop unused cartograph_runs and advisor_runs.

Both were replaced by analysis_runs. Nothing in the app reads or writes them.

Revision: 009
"""

from alembic import op

revision = "009_drop_legacy_run_tables"
down_revision = "008_provider_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_advisor_runs_cartograph_run_id", table_name="advisor_runs")
    op.drop_index("idx_advisor_runs_created_at", table_name="advisor_runs")
    op.drop_index("uq_advisor_runs_slug", table_name="advisor_runs")
    op.drop_table("advisor_runs")

    op.drop_index("idx_cartograph_runs_created_at", table_name="cartograph_runs")
    op.drop_index("uq_cartograph_runs_slug", table_name="cartograph_runs")
    op.drop_table("cartograph_runs")


def downgrade() -> None:
    raise NotImplementedError("legacy cartograph/advisor tables are not restored")
