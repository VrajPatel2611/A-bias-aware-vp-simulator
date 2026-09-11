"""feedback

Revision ID: 012
Revises: 011

DATA_MODEL §6.5

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE feedback_texts (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id    UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

            lines         TEXT[] NOT NULL,
            generator     TEXT NOT NULL CHECK (generator IN ('llm','rule_fallback')),
            prompt_version TEXT,

            -- User feedback on the feedback (UX-3)
            was_helpful   BOOLEAN,
            rated_at      TIMESTAMPTZ,

            created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX ON feedback_texts (session_id);
        CREATE INDEX ON feedback_texts (generator, created_at DESC);
    """)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS feedback_texts CASCADE")
