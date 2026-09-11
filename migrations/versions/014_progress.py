"""progress

Revision ID: 014
Revises: 013

DATA_MODEL §4.3, §4.4

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE user_progress (
            user_id              UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,

            sessions_completed   INTEGER NOT NULL DEFAULT 0,
            current_streak_days  INTEGER NOT NULL DEFAULT 0,
            longest_streak_days  INTEGER NOT NULL DEFAULT 0,
            last_session_date    DATE,          -- in the user's timezone, see §2.2

            -- Rolling window over the last 10 completed sessions.
            -- {"anchoring":{"last10":0.2,"prev10":0.5},...}  — shape in §8.3
            bias_trends          JSONB NOT NULL DEFAULT '{}'::jsonb,
            mean_coverage_last10 NUMERIC(5,2),

            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE user_case_history (
            user_id         UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            case_id         UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            times_attempted INTEGER NOT NULL DEFAULT 1,
            first_attempt   TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_attempt    TIMESTAMPTZ NOT NULL DEFAULT now(),
            best_verdict    TEXT,
            PRIMARY KEY (user_id, case_id)
        );
    """)
    bind.exec_driver_sql(
        "CREATE TRIGGER user_progress_set_updated_at BEFORE UPDATE ON user_progress "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS user_case_history CASCADE")
    bind.exec_driver_sql("DROP TABLE IF EXISTS user_progress CASCADE")
