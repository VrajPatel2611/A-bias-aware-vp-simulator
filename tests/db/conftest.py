"""
Database fixtures (BUILD_PLAN T-010).

A real PostgreSQL 16 with pgvector in a container, migrated from scratch. Not
SQLite, not a mock: every guarantee these tests check — partial unique indexes,
CHECK constraints, append-only triggers, the publication gate, RLS — is a
PostgreSQL feature. Testing them anywhere else would test nothing.

The container starts once per session and each test runs inside a transaction
that is rolled back, so tests neither wait for 16 migrations nor see each
other's rows.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import uuid

import pytest
import sqlalchemy as sa

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def pg_url() -> str:
    """A migrated database. Skips rather than fails when Docker is unavailable."""
    try:
        # The community path is the current one; the old location still works
        # but warns. Try both so the suite is quiet on either version.
        try:
            from testcontainers.community.postgres import PostgresContainer
        except ImportError:
            from testcontainers.postgres import PostgresContainer
    except ImportError:                                   # pragma: no cover
        pytest.skip("testcontainers not installed")

    try:
        container = PostgresContainer("pgvector/pgvector:pg16", driver="psycopg")
        container.start()
    except Exception as e:                                # pragma: no cover
        pytest.skip(f"Docker unavailable: {e}")

    url = container.get_connection_url()
    # sys.executable -m alembic, not bare "alembic": pytest may be running
    # without an activated venv, and then the console script is not on PATH.
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO, capture_output=True, text=True,
        env=dict(os.environ, ALEMBIC_DATABASE_URL=url),
    )
    if result.returncode != 0:
        container.stop()
        pytest.fail(f"migrations failed:\n{result.stdout}\n{result.stderr}")

    yield url
    container.stop()


# Tables holding test rows, in an order safe to truncate. Master content
# (examinations, topic_lexicon) is seeded by T-011 and deliberately absent.
_DATA_TABLES = (
    "session_events", "session_results", "feedback_texts", "sessions",
    "clinical_reviews", "case_versions", "cases",
    "subscriptions", "user_case_history", "user_progress",
    "llm_calls", "leakage_flags", "idempotency_keys", "audit_log",
    "profiles",
)


@pytest.fixture
def db(pg_url):
    """
    A connection whose work is undone afterwards.

    The default is a transaction rolled back at the end, so tests insert freely
    without cleaning up and a failure cannot leave rows that break the next one.

    A test that needs its rows visible to a SECOND connection — the RLS tests —
    must commit, which ends that transaction. The teardown therefore also
    truncates: rollback covers the normal case, truncate covers the committed
    one. Without this, an RLS test's rows stay visible to every test that runs
    afterwards and the failure surfaces somewhere unrelated.
    """
    engine = sa.create_engine(pg_url)
    conn = engine.connect()
    txn = conn.begin()

    yield conn

    # conn.in_transaction(), not txn.is_active: after the test commits, the
    # transaction object is deassociated but still reports itself active, and
    # rolling it back then warns.
    if conn.in_transaction():
        txn.rollback()
    else:
        with conn.begin():
            conn.exec_driver_sql("TRUNCATE " + ", ".join(_DATA_TABLES) + " CASCADE")
            conn.exec_driver_sql("DELETE FROM auth.users")
    conn.close()
    engine.dispose()


# ── builders ─────────────────────────────────────────────────────────
# Every table worth testing hangs off profiles -> cases -> case_versions ->
# sessions. These make a test say what it is about rather than spend ten lines
# constructing ancestors.

@pytest.fixture
def make_user(db):
    def _make() -> uuid.UUID:
        uid = uuid.uuid4()
        db.execute(sa.text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": uid})
        db.execute(sa.text("INSERT INTO profiles (id) VALUES (:id)"), {"id": uid})
        return uid
    return _make


@pytest.fixture
def make_case(db):
    def _make(slug: str | None = None) -> uuid.UUID:
        cid = uuid.uuid4()
        db.execute(sa.text("INSERT INTO cases (id, slug) VALUES (:id, :slug)"),
                   {"id": cid, "slug": slug or f"case-{cid.hex[:8]}"})
        return cid
    return _make


@pytest.fixture
def make_case_version(db, make_case):
    def _make(case_id=None, version: int = 1, status: str = "draft") -> uuid.UUID:
        case_id = case_id or make_case()
        vid = uuid.uuid4()
        # Column list taken from the migrated schema, not from memory: every
        # NOT NULL column without a default must be supplied.
        db.execute(sa.text("""
            INSERT INTO case_versions (
                id, case_id, version, status, content, title, anchor_topic,
                minimum_questions, required_topic_count, key_investigation_count,
                content_hash, published_at)
            VALUES (
                :id, :case_id, :version, CAST(:status AS case_status),
                '{}'::jsonb, 'Test case', 'cardiac', 7, 8, 4,
                :content_hash,
                CASE WHEN :status = 'published' THEN now() ELSE NULL END)
        """), {"id": vid, "case_id": case_id, "version": version,
               "status": status, "content_hash": hashlib.md5(vid.bytes).hexdigest()})
        return vid
    return _make
