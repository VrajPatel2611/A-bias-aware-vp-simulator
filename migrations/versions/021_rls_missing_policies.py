"""rls_missing_policies

Revision ID: 021
Revises: 020

The four policies DATA_MODEL §10.1 left out (found in BUILD_PLAN T-013).

§10.1 enables Row-Level Security on eight tables and then writes policies for
four of them. **In PostgreSQL, RLS enabled with no policy denies everything**
to any role that is not the owner or a superuser. So `feedback_texts`,
`subscriptions`, `user_progress` and `user_case_history` were not
under-protected -- they were completely unreadable and unwritable by the
application.

Nothing had noticed because nothing had reached them yet. T-010 tested the
policies that exist; T-012 exercised sessions and profiles; the anonymous-trial
path runs as a bypassing role and would have worked regardless. T-013 is the
first task to write a `feedback_texts` row, and the first authenticated write
would have been T-014's problem to debug -- one table at a time, each looking
like a fresh mystery.

The four policies below follow §10.1's own two patterns exactly: child tables
inherit through their parent session, and user-owned tables compare `user_id`
against `auth.uid()`. Nothing novel is being decided here; the omission was an
oversight, and `DATA_MODEL` §10.1 is updated in the same commit.

`tests/db/test_rls.py::test_every_rls_enabled_table_has_at_least_one_policy`
is the guard that makes the class of mistake loud instead of silent.
"""

from __future__ import annotations

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None

_POLICIES = ("own_feedback_texts", "own_subscriptions", "own_progress",
             "own_case_history")


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        -- Inherits through the parent session, exactly like own_session_results.
        CREATE POLICY own_feedback_texts ON feedback_texts
          FOR ALL USING (EXISTS (
            SELECT 1 FROM sessions s
            WHERE s.id = feedback_texts.session_id AND s.user_id = auth.uid()));

        -- Directly user-owned, exactly like own_sessions.
        CREATE POLICY own_subscriptions ON subscriptions
          FOR ALL USING (user_id = auth.uid());

        CREATE POLICY own_progress ON user_progress
          FOR ALL USING (user_id = auth.uid());

        CREATE POLICY own_case_history ON user_case_history
          FOR ALL USING (user_id = auth.uid());
    """)


def downgrade() -> None:
    bind = op.get_bind()
    tables = ("feedback_texts", "subscriptions", "user_progress",
              "user_case_history")
    for policy, table in zip(_POLICIES, tables, strict=True):
        bind.exec_driver_sql(f"DROP POLICY IF EXISTS {policy} ON {table}")
