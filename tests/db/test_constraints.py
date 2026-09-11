"""
T-010 criterion 2 · every constraint actually rejects.

A constraint that exists in `pg_constraint` but never fires is decoration. Each
test here asserts the database *refuses* something, because that is the only
evidence that the guarantee is real.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError, IntegrityError


class TestOwnerIsExclusive:
    """
    A session belongs to a user OR an anonymous trial, never both and never
    neither. Anonymous sessions are claimed on signup (PRD FR-2), and a row
    with both set would be claimed twice or counted twice.
    """

    def test_a_user_session_is_allowed(self, db, make_user, make_case_version):
        db.execute(sa.text("""
            INSERT INTO sessions (user_id, case_version_id, sequence_index)
            VALUES (:u, :cv, 1)
        """), {"u": make_user(), "cv": make_case_version()})

    def test_an_anonymous_session_is_allowed(self, db, make_case_version):
        db.execute(sa.text("""
            INSERT INTO sessions (anonymous_id, case_version_id, sequence_index)
            VALUES ('anon-abc', :cv, 1)
        """), {"cv": make_case_version()})

    def test_both_owners_is_rejected(self, db, make_user, make_case_version):
        with pytest.raises((IntegrityError, DBAPIError), match="owner_is_exclusive"):
            db.execute(sa.text("""
                INSERT INTO sessions (user_id, anonymous_id, case_version_id,
                                      sequence_index)
                VALUES (:u, 'anon-abc', :cv, 1)
            """), {"u": make_user(), "cv": make_case_version()})

    def test_neither_owner_is_rejected(self, db, make_case_version):
        with pytest.raises((IntegrityError, DBAPIError), match="owner_is_exclusive"):
            db.execute(sa.text("""
                INSERT INTO sessions (case_version_id, sequence_index)
                VALUES (:cv, 1)
            """), {"cv": make_case_version()})


class TestOnePublishedVersionPerCase:
    """
    Cases are immutable and versioned (ADR-0010). Two published versions of one
    case would make "which case did this learner see" unanswerable, and the
    pilot's reproducibility argument depends on that question having an answer.
    """

    def test_one_published_version_is_allowed(self, db, make_case, make_case_version):
        case = make_case()
        make_case_version(case, version=1, status="published")

    def test_drafts_alongside_a_published_version_are_allowed(
            self, db, make_case, make_case_version):
        case = make_case()
        make_case_version(case, version=1, status="published")
        make_case_version(case, version=2, status="draft")
        make_case_version(case, version=3, status="draft")

    def test_a_second_published_version_is_rejected(
            self, db, make_case, make_case_version):
        case = make_case()
        make_case_version(case, version=1, status="published")
        with pytest.raises((IntegrityError, DBAPIError),
                           match="one_published_version_per_case"):
            make_case_version(case, version=2, status="published")

    def test_a_different_case_may_also_have_one(
            self, db, make_case, make_case_version):
        make_case_version(make_case(), version=1, status="published")
        make_case_version(make_case(), version=1, status="published")


class TestOneActiveSubPerUser:
    """
    Duplicate Stripe webhooks are normal, not exceptional (BUILD_PLAN BR-6).
    Without this, an out-of-order delivery grants two concurrent subscriptions
    and the user is billed twice.
    """

    def _sub(self, db, user, status="active", sub_id=None):
        db.execute(sa.text("""
            INSERT INTO subscriptions (user_id, provider, provider_sub_id, status,
                                       tier, interval, current_period_end)
            VALUES (:u, 'stripe', :sid, :st, 'pro', 'month', now() + interval '30 days')
        """), {"u": user, "sid": sub_id or f"sub_{uuid.uuid4().hex[:12]}", "st": status})

    def test_one_active_subscription_is_allowed(self, db, make_user):
        self._sub(db, make_user())

    def test_a_second_active_subscription_is_rejected(self, db, make_user):
        user = make_user()
        self._sub(db, user)
        with pytest.raises((IntegrityError, DBAPIError),
                           match="one_active_sub_per_user"):
            self._sub(db, user)

    def test_a_cancelled_subscription_does_not_block_a_new_one(self, db, make_user):
        """Resubscribing after cancelling must work."""
        user = make_user()
        self._sub(db, user, status="cancelled")
        self._sub(db, user, status="active")


class TestProfileConstraints:
    def test_consent_requires_version_and_timestamp(self, db, make_user):
        """
        Consent without a recorded version or time is not auditable consent —
        and research consent is exactly the thing that must be provable.
        """
        with pytest.raises((IntegrityError, DBAPIError),
                           match="consent_recorded_together"):
            db.execute(sa.text("""
                UPDATE profiles SET consent_research = true WHERE id = :id
            """), {"id": make_user()})

    def test_consent_with_both_is_allowed(self, db, make_user):
        db.execute(sa.text("""
            UPDATE profiles SET consent_research = true,
                   consent_version = 'v1', consent_at = now() WHERE id = :id
        """), {"id": make_user()})

    def test_year_of_training_is_bounded(self, db, make_user):
        with pytest.raises((IntegrityError, DBAPIError)):
            db.execute(sa.text("UPDATE profiles SET year_of_training = 42 WHERE id = :id"),
                       {"id": make_user()})

    def test_research_pid_is_generated_and_unique(self, db, make_user):
        a, b = make_user(), make_user()
        pids = db.execute(sa.text(
            "SELECT research_pid FROM profiles WHERE id IN (:a, :b)"),
            {"a": a, "b": b}).scalars().all()
        assert len(set(pids)) == 2
        assert all(p.startswith("U") for p in pids)
