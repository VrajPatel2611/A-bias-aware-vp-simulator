"""
Replay and the event definitions (BUILD_PLAN T-013, ADR-0003).

The third of the three properties in CLAUDE.md is that the event log is the
source of truth and derived state is reproducible from it. `replay` is the
function that makes that literally true, so these tests are about the property
rather than about the code: replaying the same log twice must give the same
session, and a session replayed from a log must be indistinguishable from one
built as the consultation happened.

No database. `replay` is pure, which is the whole reason it lives in `domain/`.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from nidan.domain.content.cases import get_case
from nidan.domain.events import EVENT_TYPES, Event, validate_payload
from nidan.domain.session import (
    conversation_from,
    create_session,
    replay,
    update_session,
)

START = "2026-01-01T09:00:00+00:00"


def _q(seq: int, text: str) -> Event:
    return Event(seq, "question", {"text": text, "char_count": len(text)})


def _reply(seq: int, text: str, topics: list[str] | None = None) -> Event:
    return Event(seq, "patient_reply",
                 {"text": text, "matched_topics": topics or []})


# ── the shape contract ───────────────────────────────────────────────

def test_an_empty_log_replays_to_a_fresh_session():
    """
    The identity case, and the one that pins the contract: a replayed session
    must have exactly the keys `create_session` produces, or the detectors and
    templates would see a different object depending on where it came from.
    """
    replayed = replay([], case_id="case_1", started_at=START)
    fresh = create_session("case_1", started_at=START)
    assert replayed == fresh


def test_a_replayed_session_matches_one_built_as_it_happened():
    """
    The claim the whole task rests on. The left-hand side is how the pilot ran;
    the right-hand side is how Nidan runs now. They must be the same session.
    """
    questions = ["Does the pain burn after meals?",
                 "Does anything relieve it?",
                 "Any family history of heart problems?"]

    live = create_session("case_1", started_at=START)
    for q in questions:
        update_session(live, q)

    events: list[Event] = []
    for i, q in enumerate(questions):
        events.append(_q(2 * i + 1, q))
        # The writer records what it understood at the time; here that is the
        # same extraction update_session does, which is what makes the two
        # sides comparable at all.
        from nidan.domain.assessment.topics import extract_topics
        events.append(_reply(2 * i + 2, "…", extract_topics(q)))

    replayed = replay(events, case_id="case_1", started_at=START)

    assert replayed["question_count"] == live["question_count"]
    assert replayed["questions_asked"] == live["questions_asked"]
    assert sorted(replayed["topics_covered"]) == sorted(live["topics_covered"])


def test_replaying_twice_gives_the_same_session():
    """Purity, stated as a test rather than as a comment."""
    events = [_q(1, "does it burn"), _reply(2, "yes", ["pain_character"]),
              Event(3, "examination",
                    {"key": "vitals", "label": "Vitals", "finding": "HR 78"}),
              Event(4, "diagnosis", {"text": "GERD"})]
    assert replay(events, case_id="case_1", started_at=START) == \
           replay(events, case_id="case_1", started_at=START)


# ── what each event does ─────────────────────────────────────────────

def test_topics_come_from_the_reply_not_from_re_extraction():
    """
    DATA_MODEL §8.2. The question below mentions meals, which the lexicon maps
    to a topic — but the reply recorded something else, and replay must honour
    what was recorded. Re-extracting here would make every replay agree with
    today's lexicon by construction and destroy the drift signal T-016 needs.
    """
    events = [_q(1, "does the pain come after meals?"),
              _reply(2, "yes", ["something_recorded_at_the_time"])]
    session = replay(events, case_id="case_1", started_at=START)
    assert session["topics_covered"] == ["something_recorded_at_the_time"]


def test_duplicate_topics_examinations_and_investigations_are_deduplicated():
    events = [
        _reply(1, "a", ["pain_character"]),
        _reply(2, "b", ["pain_character"]),
        Event(3, "examination", {"key": "vitals", "label": "V", "finding": "f"}),
        Event(4, "examination", {"key": "vitals", "label": "V", "finding": "f"}),
        Event(5, "investigation", {"key": "ecg", "label": "E", "result": "r"}),
        Event(6, "investigation", {"key": "ecg", "label": "E", "result": "r"}),
    ]
    session = replay(events, case_id="case_1", started_at=START)
    assert session["topics_covered"] == ["pain_character"]
    assert session["exams_performed"] == ["vitals"]
    assert session["investigations_ordered"] == ["ecg"]


def test_the_first_early_diagnosis_wins():
    events = [Event(1, "early_diagnosis", {"text": "I think this is reflux"}),
              Event(2, "early_diagnosis", {"text": "actually an ulcer"})]
    session = replay(events, case_id="case_1", started_at=START)
    assert session["early_diagnosis"] == "I think this is reflux"


def test_a_diagnosis_sets_the_end_time_from_its_own_timestamp():
    """
    The end time is the event's, not the clock's. A session replayed next year
    must report when it actually ended.
    """
    at = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)
    session = replay([Event(1, "diagnosis", {"text": "GERD"}, created_at=at)],
                     case_id="case_1", started_at=START)
    assert session["diagnosis_submitted"] == "GERD"
    assert session["end_time"] == at.isoformat()


def test_feedback_viewed_and_input_blocked_change_no_state():
    """
    Both are recorded for their own sake — one is analytics, the other is the
    record that something was refused. Neither is part of the consultation.
    """
    before = replay([], case_id="case_1", started_at=START)
    after = replay([Event(1, "feedback_viewed", {}),
                    Event(2, "input_blocked", {"reason": "suspected_identifier"})],
                   case_id="case_1", started_at=START)
    assert before == after


def test_the_conversation_is_rebuilt_in_order():
    events = [_q(1, "first"), _reply(2, "one"), _q(3, "second"), _reply(4, "two")]
    assert conversation_from(events) == [
        {"role": "user", "content": "first"},
        {"role": "model", "content": "one"},
        {"role": "user", "content": "second"},
        {"role": "model", "content": "two"},
    ]


# ── a property over arbitrary logs ───────────────────────────────────

@given(st.lists(st.sampled_from(EVENT_TYPES), max_size=40))
def test_question_count_always_equals_the_number_of_question_events(types):
    """
    Over any log at all. `question_count` drives premature closure (P1:
    q < q_min), so a replay that miscounts changes a flag a learner sees —
    and it would do so silently, since nothing else in the system knows what
    the number should have been.
    """
    payloads = {
        "question": {"text": "q", "char_count": 1},
        "patient_reply": {"text": "r"},
        "examination": {"key": "k", "label": "l", "finding": "f"},
        "investigation": {"key": "k", "label": "l", "result": "r"},
        "early_diagnosis": {"text": "d"},
        "diagnosis": {"text": "d"},
        "feedback_viewed": {},
        "input_blocked": {"reason": "r"},
    }
    events = [Event(i + 1, t, payloads[t]) for i, t in enumerate(types)]
    session = replay(events, case_id="case_1", started_at=START)
    assert session["question_count"] == types.count("question")


# ── payload validation ───────────────────────────────────────────────

def test_every_event_type_has_a_declared_shape():
    """
    A type added to the enum without a shape would be rejected at write time
    with "unknown event type" — confusing, since it is in the enum. This makes
    the two lists agree or fail here.
    """
    for event_type in EVENT_TYPES:
        validate_payload(event_type, _minimal_payload(event_type))


def _minimal_payload(event_type: str) -> dict:
    return {
        "question": {"text": "q", "char_count": 1},
        "patient_reply": {"text": "r"},
        "examination": {"key": "k", "label": "l", "finding": "f"},
        "investigation": {"key": "k", "label": "l", "result": "r"},
        "early_diagnosis": {"text": "d"},
        "diagnosis": {"text": "d"},
        "feedback_viewed": {},
        "input_blocked": {"reason": "r"},
    }[event_type]


def test_a_missing_required_key_is_refused():
    with pytest.raises(ValueError, match="missing"):
        validate_payload("question", {"text": "no count"})


def test_an_unknown_key_is_refused():
    """
    A typo'd key in a JSONB column is accepted silently, survives every test,
    and is found by a replay months later that cannot see the field it wants.
    """
    with pytest.raises(ValueError, match="unexpected"):
        validate_payload("diagnosis", {"text": "GERD", "confidance": 4})


def test_input_blocked_may_never_carry_the_blocked_text():
    """
    PRD FR-4 blocks suspected real patient data. Storing the text would put the
    very thing we refused into the table we keep forever.
    """
    for key in ("text", "content", "message", "input"):
        with pytest.raises(ValueError, match="defeat the block"):
            validate_payload("input_blocked", {"reason": "identifier", key: "J Smith"})


def test_an_unknown_event_type_is_refused():
    with pytest.raises(ValueError, match="unknown event type"):
        validate_payload("celebration", {})


def test_the_case_used_by_these_tests_still_exists():
    """Guards the fixtures above against a case being renamed."""
    assert get_case("case_1") is not None
