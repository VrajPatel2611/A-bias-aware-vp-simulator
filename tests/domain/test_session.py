"""
Session state — vpsim.domain.session.

Also covers T-002 criterion 2: the clock is injected, so a session's timestamps
depend only on what the caller passed in.
"""

import pytest

from vpsim.domain.session import (
    create_session,
    get_session_summary,
    record_exam,
    record_investigation,
    update_session,
)

FIXED = "2026-01-01T09:00:00+00:00"


class TestClockInjection:
    """Criterion 2 — no datetime.now() in domain/."""

    def test_start_time_is_exactly_what_the_caller_passed(self):
        assert create_session("case_1", started_at=FIXED)["start_time"] == FIXED

    def test_started_at_is_required(self):
        """
        Keyword-only and required, so a caller cannot silently fall back to the
        system clock. That is what makes assessment replayable (ADR-0003).
        """
        with pytest.raises(TypeError):
            create_session("case_1")

    def test_two_sessions_created_with_the_same_time_are_identical(self):
        a = create_session("case_1", started_at=FIXED)
        b = create_session("case_1", started_at=FIXED)
        assert a == b


class TestRecording:
    def test_records_an_examination(self, blank_session):
        assert record_exam(blank_session, "vitals")["exams_performed"] == ["vitals"]

    def test_examinations_are_deduplicated(self, blank_session):
        record_exam(blank_session, "vitals")
        record_exam(blank_session, "vitals")
        assert blank_session["exams_performed"] == ["vitals"]

    def test_investigations_are_deduplicated(self, blank_session):
        record_investigation(blank_session, "ecg")
        record_investigation(blank_session, "ecg")
        assert blank_session["investigations_ordered"] == ["ecg"]

    def test_order_is_preserved(self, blank_session):
        for k in ("vitals", "cardiovascular", "abdominal"):
            record_exam(blank_session, k)
        assert blank_session["exams_performed"] == ["vitals", "cardiovascular", "abdominal"]


class TestUpdateSession:
    def test_increments_the_question_count(self, blank_session):
        update_session(blank_session, "Any family history?")
        assert blank_session["question_count"] == 1

    def test_stores_the_question_verbatim(self, blank_session):
        """P2 requires citing the learner's own words, so they must be kept as typed."""
        q = "Does it get WORSE after meals?!"
        update_session(blank_session, q)
        assert blank_session["questions_asked"] == [q]

    def test_extracts_topics(self, blank_session):
        update_session(blank_session, "Any family history of heart disease?")
        assert "family_history" in blank_session["topics_covered"]

    def test_topics_are_not_duplicated_across_questions(self, blank_session):
        update_session(blank_session, "Any family history?")
        update_session(blank_session, "And family history on your mother's side?")
        assert blank_session["topics_covered"].count("family_history") == 1

    def test_empty_message_still_counts_as_a_question(self, blank_session):
        update_session(blank_session, "")
        assert blank_session["question_count"] == 1


class TestSummary:
    def test_coverage_percentage(self, case, session_factory):
        s = session_factory(topics=case["required_topics"][:4])   # 4 of 8
        assert get_session_summary(s, case)["coverage_percent"] == 50

    def test_missed_topics_are_human_readable(self, case, session_factory):
        s = session_factory(topics=[])
        assert "family history" in get_session_summary(s, case)["topics_missed"]

    def test_time_taken_is_computed_from_the_two_timestamps(self, case, session_factory):
        s = session_factory(start="2026-01-01T09:00:00+00:00",
                            end="2026-01-01T09:12:30+00:00")
        assert get_session_summary(s, case)["time_taken_seconds"] == 750

    def test_time_taken_is_none_while_the_session_is_open(self, case, session_factory):
        s = session_factory(end=None)
        assert get_session_summary(s, case)["time_taken_seconds"] is None

    def test_a_malformed_timestamp_does_not_crash_the_summary(self, case, session_factory):
        """Feedback must still render — a bad timestamp is not worth losing a session over."""
        s = session_factory(start="not-a-date", end="also-not-a-date")
        assert get_session_summary(s, case)["time_taken_seconds"] is None


class TestEarlyDiagnosis:
    """
    A learner who names a diagnosis mid-consultation has effectively closed
    early. Recording it is what lets feedback distinguish "concluded at
    question 3" from "concluded at question 15".
    """

    def test_detects_a_diagnosis_stated_mid_consultation(self, blank_session):
        update_session(blank_session, "I think this is a heart attack")
        assert blank_session["early_diagnosis"] is not None

    def test_stores_the_message_verbatim(self, blank_session):
        msg = "I think this is a heart attack"
        update_session(blank_session, msg)
        assert blank_session["early_diagnosis"] == msg

    def test_an_ordinary_question_is_not_an_early_diagnosis(self, blank_session):
        update_session(blank_session, "How long has the pain been there?")
        assert blank_session["early_diagnosis"] is None

    def test_only_the_first_is_kept(self, blank_session):
        update_session(blank_session, "I think this is a heart attack")
        update_session(blank_session, "I think this is reflux")
        assert blank_session["early_diagnosis"] == "I think this is a heart attack"
