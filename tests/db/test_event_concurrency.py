"""
T-013 criterion 3, and the test BUILD_PLAN names:

    Concurrency test: 10 parallel appends produce seq 1..10 with no gaps or
    duplicates.

`UNIQUE (session_id, seq)` is the concurrency control (`DATA_MODEL` §6.2). Two
requests computing the same `max(seq) + 1` collide, one fails, and the
application retries. What makes this worth testing with real threads is the
shape of the failure: in PostgreSQL a unique violation aborts the **whole
transaction**, so a retry written the obvious way — catch, try the INSERT again
on the same connection — cannot work, and cannot be shown not to work by any
single-threaded test.

The savepoint in `EventRepository.append` is what makes the retry possible.
`test_the_retry_needs_its_savepoint` below removes it and shows the failure.
"""

from __future__ import annotations

import threading
import uuid

import pytest
import sqlalchemy as sa

from nidan.infra.db.repositories.anonymous import anonymous_scope
from nidan.infra.db.repositories.events import events_are_contiguous


@pytest.fixture
def trial_session(app_db, published_case):
    """One trial session to append to, and the visitor who owns it."""
    cv = published_case()
    with anonymous_scope("concurrency-visitor") as db:
        return db.sessions.create(cv)["id"]


def _append_many(session_id, count, *, visitor="concurrency-visitor"):
    """Fire `count` appends from `count` threads, each in its own transaction."""
    errors: list[BaseException] = []
    barrier = threading.Barrier(count)

    def worker(n: int) -> None:
        try:
            # Every thread waits here, so they contend rather than queue. Without
            # the barrier the appends serialise by accident and the test passes
            # without ever producing a collision.
            barrier.wait(timeout=10)
            with anonymous_scope(visitor) as db:
                db.events.append(session_id, "question",
                                 {"text": f"question {n}", "char_count": 10})
        except BaseException as e:      # noqa: BLE001 - re-raised below
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return errors


def test_ten_parallel_appends_produce_seq_one_to_ten(app_db, trial_session):
    """The criterion, verbatim."""
    errors = _append_many(trial_session, 10)
    assert not errors, f"appends failed: {errors!r}"

    with anonymous_scope("concurrency-visitor") as db:
        events = db.events.all_for(trial_session)

    assert len(events) == 10
    assert events_are_contiguous(events), (
        f"expected seq 1..10, got {[e.seq for e in events]} — a gap means an "
        f"append was lost, a duplicate means the unique index is not holding")


def test_no_two_events_share_a_sequence_number(app_db, trial_session):
    """
    The duplicate half, asserted at the database rather than through the
    repository, so a bug in `all_for` cannot hide it.
    """
    _append_many(trial_session, 10)
    with app_db.connect() as c:
        duplicates = c.execute(sa.text("""
            SELECT seq, count(*) FROM session_events
            WHERE session_id = :sid GROUP BY seq HAVING count(*) > 1
        """), {"sid": trial_session}).all()
    assert duplicates == []


def test_appends_to_different_sessions_do_not_contend(app_db, published_case):
    """
    `seq` is per session, so two consultations numbering their own events 1, 2,
    3 in parallel is correct and must not be slowed or failed by the retry.
    """
    cv = published_case()
    with anonymous_scope("visitor-x") as db:
        first = db.sessions.create(cv)["id"]
    with anonymous_scope("visitor-y") as db:
        second = db.sessions.create(cv)["id"]

    errors = _append_many(first, 5, visitor="visitor-x")
    errors += _append_many(second, 5, visitor="visitor-y")
    assert not errors

    with anonymous_scope("visitor-x") as db:
        assert events_are_contiguous(db.events.all_for(first))
    with anonymous_scope("visitor-y") as db:
        assert events_are_contiguous(db.events.all_for(second))


def test_the_retry_needs_its_savepoint(app_db, trial_session, monkeypatch):
    """
    Why `append` uses `begin_nested()`.

    A unique violation aborts the entire transaction in PostgreSQL, not just
    the failing statement. Retrying on the same connection without rolling back
    to a savepoint raises `InFailedSqlTransaction` on the *next* statement —
    which is a different error, in a different place, from the one that
    actually happened.

    This is the single-threaded proof of that, because the threaded test above
    cannot distinguish "the retry worked" from "no collision occurred".
    """
    from sqlalchemy.exc import IntegrityError

    with anonymous_scope("concurrency-visitor") as db:
        db.events.append(trial_session, "question",
                         {"text": "first", "char_count": 5})

        # Force the collision the retry is designed to absorb, without the
        # savepoint that lets it recover.
        #
        # `IntegrityError` specifically, not `Exception`. The first version of
        # this test caught `Exception` and passed while the INSERT never ran at
        # all — SQLAlchemy rejected the statement before execution, so the
        # transaction stayed healthy and the assertion below found nothing
        # wrong. A test that accepts any error cannot tell "the thing I meant
        # happened" from "something else did".
        with pytest.raises(IntegrityError):
            db.conn.execute(sa.text(
                "INSERT INTO session_events (session_id, seq, type, payload) "
                "VALUES (:sid, 1, 'question', '{}'::jsonb)"),
                {"sid": trial_session})

        # The transaction is now poisoned: every further statement fails until
        # it is rolled back. This is what a naive retry loop would hit on its
        # next statement — reporting an error unrelated to the collision that
        # actually happened.
        with pytest.raises(sa.exc.DBAPIError):
            db.conn.execute(sa.text("SELECT 1"))


def test_a_visitor_cannot_append_to_another_visitors_session(
        app_db, trial_session):
    """
    RLS is bypassed on this path, so the `anonymous_id` predicate in
    `AnonymousEventRepository` is the only thing preventing it. The INSERT
    matches no session and writes nothing, rather than writing into someone
    else's consultation.
    """
    with anonymous_scope("a-different-visitor") as db:
        with pytest.raises(PermissionError, match="not this actor"):
            db.events.append(trial_session, "question",
                             {"text": "not mine", "char_count": 8})

    with anonymous_scope("concurrency-visitor") as db:
        assert db.events.all_for(trial_session) == []


def test_appending_to_a_session_that_does_not_exist_is_refused(app_db):
    with anonymous_scope("concurrency-visitor") as db:
        with pytest.raises(PermissionError):
            db.events.append(uuid.uuid4(), "question",
                             {"text": "nowhere", "char_count": 7})
