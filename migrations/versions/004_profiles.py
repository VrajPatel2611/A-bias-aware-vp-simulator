"""profiles

Revision ID: 004
Revises: 003

DATA_MODEL §4.1

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE profiles (
            id                  UUID PRIMARY KEY
                                REFERENCES auth.users(id) ON DELETE CASCADE,

            display_name        TEXT,
            professional_role   professional_role,
            year_of_training    SMALLINT CHECK (year_of_training BETWEEN 1 AND 10),
            country             CHAR(2),                     -- ISO 3166-1 alpha-2
            timezone            TEXT NOT NULL DEFAULT 'UTC', -- IANA, e.g. 'Asia/Kolkata'

            -- Pseudonymous identifier. Used in every analytics and research export.
            -- Never appears alongside email in the same query result.
            research_pid        TEXT NOT NULL UNIQUE
                                DEFAULT ('U' || upper(substr(replace(gen_random_uuid()::text,'-',''),1,10))),

            subscription_tier   subscription_tier NOT NULL DEFAULT 'free',
            subscription_ends   TIMESTAMPTZ,

            -- Nullable: individual users have no institution (ADR-0015).
            institution_id      UUID,

            onboarded_at        TIMESTAMPTZ,
            last_active_at      TIMESTAMPTZ,

            consent_research    BOOLEAN NOT NULL DEFAULT false,
            consent_version     TEXT,
            consent_at          TIMESTAMPTZ,

            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at          TIMESTAMPTZ,

            CONSTRAINT consent_recorded_together
                CHECK ((consent_research = false) OR
                       (consent_version IS NOT NULL AND consent_at IS NOT NULL))
        );

        CREATE INDEX ON profiles (subscription_tier) WHERE deleted_at IS NULL;
        CREATE INDEX ON profiles (last_active_at DESC) WHERE deleted_at IS NULL;
    """)
    bind.exec_driver_sql(
        "CREATE TRIGGER profiles_set_updated_at BEFORE UPDATE ON profiles "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS profiles CASCADE")
