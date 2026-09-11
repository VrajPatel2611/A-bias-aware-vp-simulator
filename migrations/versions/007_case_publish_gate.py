"""case_publish_gate

Revision ID: 007
Revises: 006

DATA_MODEL §5.1 — must follow 006: the trigger references clinical_reviews

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        -- Enforces PRD FR-12.5: no case reaches a user without clinical sign-off.
        CREATE OR REPLACE FUNCTION require_clinical_approval() RETURNS trigger AS $$
        BEGIN
          IF NEW.status = 'published' AND OLD.status <> 'published' THEN
            IF NOT EXISTS (
              SELECT 1 FROM clinical_reviews
              WHERE case_version_id = NEW.id AND decision = 'approved'
            ) THEN
              RAISE EXCEPTION 'Case version %% has no approving clinical review', NEW.id;
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER enforce_clinical_approval
          BEFORE UPDATE ON case_versions
          FOR EACH ROW EXECUTE FUNCTION require_clinical_approval();
    """)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TRIGGER IF EXISTS enforce_clinical_approval ON case_versions")
    bind.exec_driver_sql("DROP FUNCTION IF EXISTS require_clinical_approval()")
