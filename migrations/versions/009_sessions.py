"""sessions

Revision ID: 009
Revises: 008

DATA_MODEL §6.1

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE sessions (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- Exactly one of these is set. Anonymous trial sessions (PRD FR-2) have
            -- anonymous_id; on signup the session is claimed and user_id is populated.
            user_id           UUID REFERENCES profiles(id) ON DELETE CASCADE,
            anonymous_id      TEXT,

            case_version_id   UUID NOT NULL REFERENCES case_versions(id) ON DELETE RESTRICT,

            sequence_index    INTEGER NOT NULL,
            status            session_status NOT NULL DEFAULT 'active',

            confidence_pre    SMALLINT CHECK (confidence_pre BETWEEN 1 AND 5),

            started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            ended_at          TIMESTAMPTZ,
            last_activity_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

            -- Set on first successful /diagnosis. Makes submission idempotent (FR-7.6).
            diagnosis_submitted_at TIMESTAMPTZ,

            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT owner_is_exclusive CHECK (
                (user_id IS NOT NULL AND anonymous_id IS NULL) OR
                (user_id IS NULL AND anonymous_id IS NOT NULL)
            ),
            CONSTRAINT ended_when_terminal CHECK (
                (status = 'active') OR (ended_at IS NOT NULL)
            )
        );

        CREATE UNIQUE INDEX user_sequence_unique
            ON sessions (user_id, sequence_index) WHERE user_id IS NOT NULL;

        CREATE INDEX ON sessions (user_id, started_at DESC) WHERE user_id IS NOT NULL;
        CREATE INDEX ON sessions (anonymous_id) WHERE anonymous_id IS NOT NULL;
        CREATE INDEX ON sessions (status, last_activity_at) WHERE status = 'active';
        CREATE INDEX ON sessions (case_version_id);
    """)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS sessions CASCADE")
