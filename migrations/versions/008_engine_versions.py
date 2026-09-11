"""engine_versions

Revision ID: 008
Revises: 007

DATA_MODEL §6.4

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE engine_versions (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            version           TEXT NOT NULL UNIQUE,      -- '1.3.0'
            detector_version  TEXT NOT NULL,
            lexicon_version   TEXT NOT NULL,
            encoder_model     TEXT,                      -- null while keyword-only

            -- The exact thresholds used. Shape in §8.7.
            thresholds        JSONB NOT NULL,

            is_current        BOOLEAN NOT NULL DEFAULT false,
            notes             TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE UNIQUE INDEX only_one_current_engine
            ON engine_versions (is_current) WHERE is_current;
    """)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS engine_versions CASCADE")
