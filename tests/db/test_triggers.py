"""
T-010 criteria 3 and 4 · the triggers actually fire.

These two are not conveniences. The append-only guarantee is what makes
property P3 true — *the event log is the source of truth, derived state is
reproducible from it* (ADR-0003). If a row can be edited after the fact, a
result can no longer be recomputed and shown to match, which is the argument
the pilot's data-integrity check rests on.

The publication gate is the same idea for clinical safety: it makes "no case
reaches a learner without an approving clinical review" a property of the
database rather than a promise about the admin console.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError


class TestSessionEventsAreAppendOnly:
    """ADR-0003. The event log is the source of truth, so it cannot be edited."""

    def _session(self, db, make_user, make_case_version) -> uuid.UUID:
        sid = uuid.uuid4()
        db.execute(sa.text("""
            INSERT INTO sessions (id, user_id, case_version_id, sequence_index)
            VALUES (:id, :u, :cv, 1)
        """), {"id": sid, "u": make_user(), "cv": make_case_version()})
        return sid

    def _event(self, db, session_id, seq=1):
        db.execute(sa.text("""
            INSERT INTO session_events (session_id, seq, type, payload)
            VALUES (:s, :q, 'question', '{"text":"does it radiate?"}'::jsonb)
        """), {"s": session_id, "q": seq})

    def test_appending_is_allowed(self, db, make_user, make_case_version):
        s = self._session(db, make_user, make_case_version)
        self._event(db, s, 1)
        self._event(db, s, 2)
        n = db.execute(sa.text("SELECT count(*) FROM session_events WHERE session_id=:s"),
                       {"s": s}).scalar()
        assert n == 2

    def test_update_is_refused(self, db, make_user, make_case_version):
        s = self._session(db, make_user, make_case_version)
        self._event(db, s)
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(sa.text(
                "UPDATE session_events SET payload = '{}'::jsonb WHERE session_id=:s"),
                {"s": s})

    def test_delete_is_refused(self, db, make_user, make_case_version):
        s = self._session(db, make_user, make_case_version)
        self._event(db, s)
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(sa.text("DELETE FROM session_events WHERE session_id=:s"),
                       {"s": s})

    def test_the_sequence_number_is_unique_per_session(
            self, db, make_user, make_case_version):
        """
        T-013 appends concurrently. Two events claiming seq 3 would make replay
        order ambiguous, and replay order is the whole guarantee.
        """
        s = self._session(db, make_user, make_case_version)
        self._event(db, s, 1)
        with pytest.raises(DBAPIError):
            self._event(db, s, 1)


class TestAuditLogIsAppendOnly:
    """Every admin action is recorded. A record that can be edited is not one."""

    def _entry(self, db, actor):
        db.execute(sa.text("""
            INSERT INTO audit_log (actor_id, action, entity_type, entity_id, reason)
            VALUES (:a, 'case_version.published', 'case_version', :e, 'test')
        """), {"a": actor, "e": uuid.uuid4()})

    def test_appending_is_allowed(self, db, make_user):
        self._entry(db, make_user())

    def test_update_is_refused(self, db, make_user):
        actor = make_user()
        self._entry(db, actor)
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(sa.text("UPDATE audit_log SET reason = 'changed' WHERE actor_id=:a"),
                       {"a": actor})

    def test_delete_is_refused(self, db, make_user):
        actor = make_user()
        self._entry(db, actor)
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(sa.text("DELETE FROM audit_log WHERE actor_id=:a"), {"a": actor})


class TestPublicationGate:
    """
    T-010 criterion 4 — publishing without an approving clinical review is
    blocked by the database, not merely by the admin console (T-023).
    """

    def test_publishing_without_a_review_is_refused(
            self, db, make_case, make_case_version):
        version = make_case_version(make_case(), status="draft")
        with pytest.raises(DBAPIError, match="approving clinical review"):
            db.execute(sa.text("""
                UPDATE case_versions SET status = 'published', published_at = now()
                WHERE id = :id
            """), {"id": version})

    def test_publishing_with_an_approving_review_is_allowed(
            self, db, make_user, make_case, make_case_version):
        version = make_case_version(make_case(), status="draft")
        db.execute(sa.text("""
            INSERT INTO clinical_reviews (case_version_id, reviewer_id, decision, scores)
            VALUES (:v, :r, 'approved', '{}'::jsonb)
        """), {"v": version, "r": make_user()})
        db.execute(sa.text("""
            UPDATE case_versions SET status = 'published', published_at = now()
            WHERE id = :id
        """), {"id": version})
        status = db.execute(sa.text("SELECT status FROM case_versions WHERE id=:id"),
                            {"id": version}).scalar()
        assert status == "published"

    def test_a_rejecting_review_does_not_permit_publication(
            self, db, make_user, make_case, make_case_version):
        """A review that exists is not a review that approved."""
        version = make_case_version(make_case(), status="draft")
        db.execute(sa.text("""
            INSERT INTO clinical_reviews (case_version_id, reviewer_id, decision, scores)
            VALUES (:v, :r, 'changes_requested', '{}'::jsonb)
        """), {"v": version, "r": make_user()})
        with pytest.raises(DBAPIError, match="approving clinical review"):
            db.execute(sa.text("""
                UPDATE case_versions SET status = 'published', published_at = now()
                WHERE id = :id
            """), {"id": version})

    def test_remaining_a_draft_needs_no_review(self, db, make_case, make_case_version):
        version = make_case_version(make_case(), status="draft")
        db.execute(sa.text("UPDATE case_versions SET title = 'Renamed' WHERE id=:id"),
                   {"id": version})
