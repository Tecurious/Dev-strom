"""Alembic migration environment.

Reads DATABASE_URL from the project .env file so no credentials are
hardcoded in alembic.ini.  Both offline (SQL dump) and online (live DB)
migration modes are supported.
"""

import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── alembic config object ──────────────────────────────────────────────────────
config = context.config

# Wire the DATABASE_URL environment variable into Alembic's config so both
# run_migrations_offline() and engine_from_config() pick it up automatically.
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── target metadata ────────────────────────────────────────────────────────────
# Import Base from services/db.py so Alembic can compare ORM models against the
# live database when using --autogenerate.
from app.services.db import Base  # noqa: E402

target_metadata = Base.metadata


# ── migration runners ──────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Offline mode: emit raw SQL to stdout instead of running against a live DB.

    Useful for generating SQL scripts to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online mode: connect to the live database and run migrations directly."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
