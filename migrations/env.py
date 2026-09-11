"""
Alembic environment.

The database URL comes from configuration, not from alembic.ini — the same
validated `DATABASE_URL` the application uses (T-006), so there is one source of
truth and no second place for it to drift.
"""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine, pool

from nidan.infra.db.models import metadata

target_metadata = metadata


def _url() -> str:
    """
    The database to migrate.

    ALEMBIC_DATABASE_URL wins so tests can point at a throwaway container
    without disturbing the developer's own settings.
    """
    url = os.getenv("ALEMBIC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit(
            "No database URL. Set DATABASE_URL (or ALEMBIC_DATABASE_URL).\n"
            "For the local stack: postgresql+psycopg://nidan:nidan_local_dev_only"
            "@localhost:5432/nidan"
        )
    # psycopg 3 is the driver; accept the plain form for convenience.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
