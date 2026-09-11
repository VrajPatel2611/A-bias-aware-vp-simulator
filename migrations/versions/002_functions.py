"""functions

Revision ID: 002
Revises: 001
"""

from __future__ import annotations

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # DATA_MODEL §2.7. Applied to every table carrying updated_at.
    bind.exec_driver_sql("""
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN NEW.updated_at = now(); RETURN NEW; END;
        $$ LANGUAGE plpgsql
    """)

    # Applied as BEFORE UPDATE OR DELETE on session_events and audit_log.
    # This is what makes "append-only" a property of the database rather than
    # a convention the application is trusted to honour (ADR-0003, PR-3).
    bind.exec_driver_sql("""
        CREATE OR REPLACE FUNCTION forbid_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'Table %% is append-only', TG_TABLE_NAME; END;
        $$ LANGUAGE plpgsql
    """)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP FUNCTION IF EXISTS forbid_mutation()")
    bind.exec_driver_sql("DROP FUNCTION IF EXISTS set_updated_at()")
