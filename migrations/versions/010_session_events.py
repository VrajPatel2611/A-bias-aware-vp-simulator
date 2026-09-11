"""session_events

Revision ID: 010
Revises: 009

DATA_MODEL §6.2 — append-only, enforced by trigger (ADR-0003)

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE session_events (
            id          BIGSERIAL PRIMARY KEY,
            session_id  UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            seq         INTEGER NOT NULL,
            type        event_type NOT NULL,
            payload     JSONB NOT NULL,           -- shape per type in §8.2
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE (session_id, seq)
        );

        CREATE INDEX ON session_events (session_id, seq);

        CREATE TRIGGER session_events_append_only
          BEFORE UPDATE OR DELETE ON session_events
          FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
    """)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS session_events CASCADE")
