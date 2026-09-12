"""
The connection pool (BUILD_PLAN T-012).

**This module is private to `nidan.infra.db`.** Nothing outside it may import
`engine` -- `tests/test_db_access.py` fails the build if anything does. That
restriction is the whole of acceptance criterion 1: "no query bypasses" the
repository layer is not a convention anyone can follow or forget, it is the
observation that there is no other way to obtain a connection.

The engine is built on first use rather than at import, so importing
`nidan.app` in a test that never touches the database does not require a
database to exist.
"""

from __future__ import annotations

import threading

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from nidan.config import settings

_engine: Engine | None = None
_lock = threading.Lock()


def _url() -> str:
    url = settings.DATABASE_URL.strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set, so no repository can open a transaction. "
            "Locally: docker compose up -d db. See docs/process/COMMANDS.md."
        )
    # SQLAlchemy defaults `postgresql://` to psycopg2, which is not a
    # dependency here. Compose and Supabase both hand out the bare scheme, so
    # normalise rather than make every caller remember the suffix.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_engine() -> Engine:
    """
    The process-wide engine. Built once, under a lock.

    Without the lock, two gunicorn threads arriving together each build an
    engine and one is silently discarded along with its pool -- connections
    that are never returned and never closed, which surfaces much later as
    Supabase refusing new ones.
    """
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = sa.create_engine(
                    _url(),
                    # Supabase closes idle connections server-side. Without
                    # pre-ping the first request after a quiet period fails
                    # with a closed-connection error that looks like a bug in
                    # whatever it happened to interrupt.
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=5,
                    pool_recycle=1800,
                    future=True,
                )
    return _engine


def dispose_engine() -> None:
    """Close the pool. For tests and for a clean shutdown."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
