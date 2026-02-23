"""Initial schema: all 5 Dev-Strom V3 tables.

Creates: users, user_api_keys, runs, expanded_ideas, web_chunks.
See md/TableDesign.md for full rationale on every design decision.

Revision: 001
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pgvector extension (already enabled in V3-2, idempotent) ──────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── users ─────────────────────────────────────────────────────────────────
    # Identity anchor. One row per Google-authenticated user.
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("google_id", sa.Text, unique=True, nullable=False),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── user_api_keys ─────────────────────────────────────────────────────────
    # Encrypted API key store. provider is open TEXT (openai, tavily, etc.)
    # No UNIQUE(user_id, provider) — allows multiple keys per provider if needed.
    op.create_table(
        "user_api_keys",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("encrypted_key", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── runs ──────────────────────────────────────────────────────────────────
    # One row per idea-generation call. ideas stored as JSONB (nested structure).
    op.create_table(
        "runs",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tech_stack", sa.Text, nullable=False),
        sa.Column("domain", sa.Text, nullable=True),
        sa.Column("level", sa.Text, nullable=True),
        sa.Column("count", sa.Integer, server_default="3", nullable=False),
        sa.Column(
            "enable_multi_query",
            sa.Boolean,
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "ideas",
            sa.dialects.postgresql.JSONB,
            nullable=False,
        ),
        sa.Column("web_context", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # Indexes for history queries
    op.create_index("idx_runs_user_id", "runs", ["user_id"])
    op.create_index(
        "idx_runs_created_at",
        "runs",
        [sa.text("created_at DESC")],
    )

    # ── expanded_ideas ────────────────────────────────────────────────────────
    # Stores LLM expansion output for a specific idea position within a run.
    # Multiple expansions of the same (run_id, pid) are allowed — no UNIQUE constraint.
    # Query: WHERE run_id=X AND pid=Y ORDER BY created_at DESC LIMIT 1
    op.create_table(
        "expanded_ideas",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pid", sa.Integer, nullable=False),  # 1-based idea position
        sa.Column(
            "extended_plan",
            sa.dialects.postgresql.JSONB,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_expanded_ideas_run_pid",
        "expanded_ideas",
        ["run_id", "pid"],
    )

    # ── web_chunks ─────────────────────────────────────────────────────────────
    # Tavily web content chunked and embedded for RAG retrieval.
    # Embedding stored as pgvector vector(1536) — OpenAI text-embedding-3-small.
    # Embeddings are inserted by a FastAPI BackgroundTask after the response is
    # returned — the user never waits for this.
    op.create_table(
        "web_chunks",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
    )
    # IVFFlat index for fast cosine similarity search.
    # lists=50 is optimal for tables under ~500k rows.
    op.execute(
        "CREATE INDEX idx_web_chunks_embedding ON web_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)"
    )


def downgrade() -> None:
    # Drop in reverse order of creation (respects FK dependencies)
    op.execute("DROP INDEX IF EXISTS idx_web_chunks_embedding")
    op.drop_table("web_chunks")

    op.drop_index("idx_expanded_ideas_run_pid", table_name="expanded_ideas")
    op.drop_table("expanded_ideas")

    op.drop_index("idx_runs_created_at", table_name="runs")
    op.drop_index("idx_runs_user_id", table_name="runs")
    op.drop_table("runs")

    op.drop_table("user_api_keys")
    op.drop_table("users")
