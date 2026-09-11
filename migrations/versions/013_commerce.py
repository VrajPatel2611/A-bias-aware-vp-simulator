"""commerce

Revision ID: 013
Revises: 012

DATA_MODEL §4.2

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE subscriptions (
            id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id               UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,

            provider              TEXT NOT NULL
                                  CHECK (provider IN ('stripe','apple','google','manual')),
            provider_customer_id  TEXT,
            provider_sub_id       TEXT,

            tier                  subscription_tier NOT NULL,
            status                TEXT NOT NULL
                                  CHECK (status IN ('active','past_due','cancelled','expired','trialing')),
            interval              TEXT CHECK (interval IN ('month','year')),

            currency              CHAR(3),
            amount_minor          INTEGER,     -- smallest currency unit; avoids float
            country               CHAR(2),     -- for regional pricing analysis

            current_period_start  TIMESTAMPTZ,
            current_period_end    TIMESTAMPTZ,
            cancel_at_period_end  BOOLEAN NOT NULL DEFAULT false,
            grace_until           TIMESTAMPTZ,

            created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE (provider, provider_sub_id)
        );

        CREATE INDEX ON subscriptions (user_id, status);
        CREATE UNIQUE INDEX one_active_sub_per_user
            ON subscriptions (user_id) WHERE status IN ('active','trialing','past_due');
    """)
    bind.exec_driver_sql(
        "CREATE TRIGGER subscriptions_set_updated_at BEFORE UPDATE ON subscriptions "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS subscriptions CASCADE")
