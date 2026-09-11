"""
Row-Level Security actually denies (DATA_MODEL §10.1, SECURITY_SPEC L3).

This is the layer that turns a forgotten `WHERE user_id = ...` from a breach
into a non-event, so "the policy exists" is not the claim worth testing —
"another user's rows are invisible" is.

Possible only because migration 001 installs an `auth.uid()` matching
Supabase's, which reads `request.jwt.claim.sub`. Without it these policies
could first be exercised in production.

T-012 owns the repository layer and will test this against real application
queries. This is the schema-level proof that the policies are wired correctly.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa


@pytest.fixture
def rls_conn(pg_url):
    """
    A connection as a NON-superuser.

    This matters: Postgres exempts superusers and table owners from RLS, so
    running these assertions as the migration user would pass while proving
    nothing at all.
    """
    admin = sa.create_engine(pg_url)
    with admin.connect() as c:
        c.execute(sa.text("DROP ROLE IF EXISTS rls_tester"))
        c.execute(sa.text("CREATE ROLE rls_tester LOGIN PASSWORD 'x'"))
        c.execute(sa.text("GRANT USAGE ON SCHEMA public TO rls_tester"))
        c.execute(sa.text(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
            "IN SCHEMA public TO rls_tester"))
        c.commit()

    url = sa.engine.make_url(pg_url).set(username="rls_tester", password="x")
    engine = sa.create_engine(url)
    conn = engine.connect()
    yield conn
    conn.close()
    engine.dispose()
    with admin.connect() as c:
        c.execute(sa.text("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM rls_tester"))
        c.execute(sa.text("REVOKE USAGE ON SCHEMA public FROM rls_tester"))
        c.execute(sa.text("DROP ROLE IF EXISTS rls_tester"))
        c.commit()
    admin.dispose()


def _as_user(conn, user_id) -> None:
    """Impersonate a signed-in user, the way Supabase does via the JWT."""
    conn.execute(sa.text(f"SET request.jwt.claim.sub = '{user_id}'"))


class TestProfilesAreOwnerOnly:
    def test_a_user_sees_their_own_profile(self, db, rls_conn, make_user):
        user = make_user()
        db.commit()
        _as_user(rls_conn, user)
        seen = rls_conn.execute(sa.text("SELECT id FROM profiles")).scalars().all()
        assert seen == [user]

    def test_a_user_cannot_see_another_profile(self, db, rls_conn, make_user):
        mine, theirs = make_user(), make_user()
        db.commit()
        _as_user(rls_conn, mine)
        seen = rls_conn.execute(sa.text("SELECT id FROM profiles")).scalars().all()
        assert theirs not in seen, "another user's profile was visible"

    def test_with_no_identity_nothing_is_visible(self, db, rls_conn, make_user):
        """An unauthenticated connection is not a privileged one."""
        make_user()
        db.commit()
        rls_conn.execute(sa.text("SET request.jwt.claim.sub = ''"))
        assert rls_conn.execute(sa.text("SELECT count(*) FROM profiles")).scalar() == 0


class TestSessionsAreOwnerOnly:
    def _session(self, db, user, case_version) -> uuid.UUID:
        sid = uuid.uuid4()
        db.execute(sa.text("""
            INSERT INTO sessions (id, user_id, case_version_id, sequence_index)
            VALUES (:id, :u, :cv, 1)
        """), {"id": sid, "u": user, "cv": case_version})
        return sid

    def test_a_user_sees_only_their_own_sessions(
            self, db, rls_conn, make_user, make_case_version):
        mine, theirs = make_user(), make_user()
        cv = make_case_version()
        my_session = self._session(db, mine, cv)
        their_session = self._session(db, theirs, cv)
        db.commit()

        _as_user(rls_conn, mine)
        seen = rls_conn.execute(sa.text("SELECT id FROM sessions")).scalars().all()
        assert my_session in seen
        assert their_session not in seen, "another user's session was visible"

    def test_child_events_inherit_the_restriction(
            self, db, rls_conn, make_user, make_case_version):
        """
        session_events has no user_id of its own — its policy reaches through
        the parent session. That indirection is the easiest thing to get wrong.
        """
        mine, theirs = make_user(), make_user()
        cv = make_case_version()
        their_session = self._session(db, theirs, cv)
        db.execute(sa.text("""
            INSERT INTO session_events (session_id, seq, type, payload)
            VALUES (:s, 1, 'question', '{"text":"secret"}'::jsonb)
        """), {"s": their_session})
        db.commit()

        _as_user(rls_conn, mine)
        assert rls_conn.execute(sa.text("SELECT count(*) FROM session_events")).scalar() == 0


class TestPublishedContentIsWorldReadable:
    def test_a_published_version_is_visible_to_anyone(
            self, db, rls_conn, make_case, make_case_version, make_user):
        version = make_case_version(make_case(), status="draft")
        db.execute(sa.text("""
            INSERT INTO clinical_reviews (case_version_id, reviewer_id, decision, scores)
            VALUES (:v, :r, 'approved', '{}'::jsonb)
        """), {"v": version, "r": make_user()})
        db.execute(sa.text(
            "UPDATE case_versions SET status='published', published_at=now() WHERE id=:id"),
            {"id": version})
        db.commit()

        rls_conn.execute(sa.text("SET request.jwt.claim.sub = ''"))
        seen = rls_conn.execute(sa.text("SELECT id FROM case_versions")).scalars().all()
        assert version in seen, "published content must be readable without an account"

    def test_a_draft_is_not_visible(self, db, rls_conn, make_case, make_case_version):
        draft = make_case_version(make_case(), status="draft")
        db.commit()
        rls_conn.execute(sa.text("SET request.jwt.claim.sub = ''"))
        seen = rls_conn.execute(sa.text("SELECT id FROM case_versions")).scalars().all()
        assert draft not in seen, "an unpublished case was readable"
