"""session_results

Revision ID: 011
Revises: 010

DATA_MODEL §6.3

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE session_results (
            session_id             UUID PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,

            question_count         INTEGER NOT NULL,
            examination_count      INTEGER NOT NULL,
            investigation_count    INTEGER NOT NULL,
            duration_seconds       INTEGER,

            coverage_pct           NUMERIC(5,2) NOT NULL CHECK (coverage_pct BETWEEN 0 AND 100),
            topics_hit             TEXT[] NOT NULL,
            topics_missed          TEXT[] NOT NULL,

            diagnosis_submitted    TEXT NOT NULL,
            diagnosis_verdict      TEXT NOT NULL
                                   CHECK (diagnosis_verdict IN ('correct','partial','anchored','other')),

            -- Scalars duplicated out of bias_detail for indexed analytical queries.
            anchoring_detected           BOOLEAN NOT NULL,
            anchoring_score              NUMERIC(4,3) NOT NULL CHECK (anchoring_score BETWEEN 0 AND 1),
            premature_closure_detected   BOOLEAN NOT NULL,
            premature_closure_score      NUMERIC(4,3) NOT NULL CHECK (premature_closure_score BETWEEN 0 AND 1),
            confirmation_bias_detected   BOOLEAN NOT NULL,
            confirmation_bias_score      NUMERIC(4,3) NOT NULL CHECK (confirmation_bias_score BETWEEN 0 AND 1),

            bias_detail             JSONB NOT NULL,   -- reason + evidence, §8.5
            exam_scorecard          JSONB NOT NULL,   -- §8.6
            investigation_scorecard JSONB NOT NULL,   -- §8.6

            key_investigations_done  SMALLINT NOT NULL,
            key_investigations_total SMALLINT NOT NULL,

            engine_version_id      UUID NOT NULL REFERENCES engine_versions(id),
            computed_at            TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX ON session_results (diagnosis_verdict);
        CREATE INDEX ON session_results (anchoring_detected, premature_closure_detected, confirmation_bias_detected);
        CREATE INDEX ON session_results USING gin (bias_detail);
        CREATE INDEX ON session_results (engine_version_id);
    """)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS session_results CASCADE")
