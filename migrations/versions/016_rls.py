"""rls

Revision ID: 016
Revises: 015

Row-Level Security (DATA_MODEL §10.1).

Defence in depth. An application bug that forgets `WHERE user_id = ...` then
returns NOTHING rather than another user's rows — the layer that turns a routine
mistake into a non-event instead of a breach (SECURITY_SPEC L3).

`case_versions` needs RLS enabled for its read policy, but is deliberately NOT
in the §10.1 ALTER list — published content is world-readable by design.
Enabling it here without a policy would make published cases invisible, so the
policy and the enable are applied together.

The anonymous-trial path has no `auth.uid()` and is served through a
service-role connection with an explicit `anonymous_id` filter. That path is
short, isolated and separately tested (T-015), and it is the one place this
safety net is deliberately off.
"""

from __future__ import annotations

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        ALTER TABLE profiles         ENABLE ROW LEVEL SECURITY;
        ALTER TABLE sessions         ENABLE ROW LEVEL SECURITY;
        ALTER TABLE session_events   ENABLE ROW LEVEL SECURITY;
        ALTER TABLE session_results  ENABLE ROW LEVEL SECURITY;
        ALTER TABLE feedback_texts   ENABLE ROW LEVEL SECURITY;
        ALTER TABLE subscriptions    ENABLE ROW LEVEL SECURITY;
        ALTER TABLE user_progress    ENABLE ROW LEVEL SECURITY;
        ALTER TABLE user_case_history ENABLE ROW LEVEL SECURITY;

        -- Users see only themselves
        CREATE POLICY own_profile ON profiles
          FOR ALL USING (id = auth.uid());

        CREATE POLICY own_sessions ON sessions
          FOR ALL USING (user_id = auth.uid());

        -- Child tables inherit via their parent session
        CREATE POLICY own_session_events ON session_events
          FOR ALL USING (EXISTS (
            SELECT 1 FROM sessions s
            WHERE s.id = session_events.session_id AND s.user_id = auth.uid()));

        CREATE POLICY own_session_results ON session_results
          FOR ALL USING (EXISTS (
            SELECT 1 FROM sessions s
            WHERE s.id = session_results.session_id AND s.user_id = auth.uid()));

        -- Published content is world-readable; only admins write
        CREATE POLICY read_published_cases ON case_versions
          FOR SELECT USING (status = 'published');
    """)
    # Required for read_published_cases above to take effect.
    bind.exec_driver_sql("ALTER TABLE case_versions ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("ALTER TABLE case_versions DISABLE ROW LEVEL SECURITY")
    bind.exec_driver_sql("DROP POLICY IF EXISTS own_profile ON profiles")
    bind.exec_driver_sql("DROP POLICY IF EXISTS own_sessions ON sessions")
    bind.exec_driver_sql("DROP POLICY IF EXISTS own_session_events ON session_events")
    bind.exec_driver_sql("DROP POLICY IF EXISTS own_session_results ON session_results")
    bind.exec_driver_sql("DROP POLICY IF EXISTS read_published_cases ON case_versions")
    bind.exec_driver_sql("ALTER TABLE profiles DISABLE ROW LEVEL SECURITY")
    bind.exec_driver_sql("ALTER TABLE sessions DISABLE ROW LEVEL SECURITY")
    bind.exec_driver_sql("ALTER TABLE session_events DISABLE ROW LEVEL SECURITY")
    bind.exec_driver_sql("ALTER TABLE session_results DISABLE ROW LEVEL SECURITY")
    bind.exec_driver_sql("ALTER TABLE feedback_texts DISABLE ROW LEVEL SECURITY")
    bind.exec_driver_sql("ALTER TABLE subscriptions DISABLE ROW LEVEL SECURITY")
    bind.exec_driver_sql("ALTER TABLE user_progress DISABLE ROW LEVEL SECURITY")
    bind.exec_driver_sql("ALTER TABLE user_case_history DISABLE ROW LEVEL SECURITY")
