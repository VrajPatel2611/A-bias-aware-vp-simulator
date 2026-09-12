"""
The feedback screen's content, as a pure function (BUILD_PLAN T-013).

Everything on the feedback page except the prose is **recomputed** when the
page is rendered, from the event log. None of it is stored.

That is not a performance decision, it is the point of `ADR-0003`. A stored
scorecard is a cache of a conclusion, and a cache can disagree with the log it
came from — silently, and in the direction nobody checks. Recomputing means the
page a learner sees a year from now is derived from the same events, by the
same code, as the page they saw on the day; and when a detector or a threshold
changes, the change is visible rather than frozen into old rows.

This module moved here from `api/routes.py` in T-013, where it ran once at
`/conclude` and its output was kept in memory. It is unchanged logic — the
categorisation rules are the ones the pilot ran — but it is now pure, in
`domain/`, and therefore testable without a request.

The only thing the feedback screen cannot recompute is the prose, because a
language model wrote it. That is stored (`infra/db/repositories/feedback.py`),
and the split is exactly `ADR-0005`: the model writes words, the deterministic
code decides everything that counts.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from nidan.domain.content.cases import MASTER_EXAMINATIONS, MASTER_INVESTIGATIONS
from nidan.domain.session import get_session_summary
from nidan.domain.types import Case, Session


def build_examination_scorecard(session: Session, case: Case) -> dict[str, list[str]]:
    """
    Categorise every examination performed, and every key one skipped.

    `extra_done` is neutral, not a penalty: examining a system this case does
    not turn on is thoroughness, and marking it down would teach learners to
    examine only what they already suspect — the habit the product exists to
    interrupt.
    """
    performed = session.get("exams_performed", [])
    case_exam = case.get("examination", {})

    scorecard: dict[str, list[str]] = {
        "key_done": [], "key_missed": [], "relevant_done": [], "extra_done": [],
    }

    for key in performed:
        label = _label(key, MASTER_EXAMINATIONS, case_exam)
        if key in case_exam:
            bucket = "key_done" if case_exam[key].get("key") else "relevant_done"
            scorecard[bucket].append(label)
        else:
            scorecard["extra_done"].append(label)

    for key, spec in case_exam.items():
        if spec.get("key") and key not in performed:
            scorecard["key_missed"].append(_label(key, MASTER_EXAMINATIONS, case_exam))

    return scorecard


def build_investigation_scorecard(session: Session, case: Case) -> dict[str, list[str]]:
    """
    Categorise every investigation ordered, and every key one not ordered.

    `low_value_done` is the one flagged bucket, and it is flagged because
    ordering a test that cannot change management is a reasoning error the
    learner can act on — unlike ordering one extra reasonable test.
    """
    ordered = session.get("investigations_ordered", [])
    case_inv = case.get("investigations", {})

    scorecard: dict[str, list[str]] = {
        "key_done": [], "key_missed": [], "reasonable_done": [],
        "low_value_done": [], "extra_done": [],
    }

    by_category = {"key": "key_done", "reasonable": "reasonable_done",
                   "low_value": "low_value_done"}

    for key in ordered:
        label = _label(key, MASTER_INVESTIGATIONS, case_inv)
        if key in case_inv:
            bucket = by_category.get(case_inv[key].get("category", ""))
            if bucket:
                scorecard[bucket].append(label)
        else:
            scorecard["extra_done"].append(label)

    for key, spec in case_inv.items():
        if spec.get("category") == "key" and key not in ordered:
            scorecard["key_missed"].append(
                _label(key, MASTER_INVESTIGATIONS, case_inv))

    return scorecard


def build_feedback_view(session: Session, case: Case, *, case_id: str,
                        bias_results: dict[str, Any],
                        clinical_eval: dict[str, Any],
                        feedback_lines: Sequence[str]) -> dict[str, Any]:
    """
    Everything the feedback template renders.

    Pure: the same session and case always produce the same view. The only
    input that is not derived from the event log is `feedback_lines`, which
    a model wrote and which is read back from storage.
    """
    required = case["required_topics"]
    covered = session["topics_covered"]

    return {
        "case_id": case_id,
        "case_title": case["title"],
        "diagnosis_given": session["diagnosis_submitted"],
        "questions_asked": session["question_count"],
        "biases_detected": bias_results,
        "clinical_eval": clinical_eval,
        "feedback_messages": list(feedback_lines),
        "session_summary": get_session_summary(session, case),
        "topics_hit": [t for t in required if t in covered],
        "topics_missed": [t for t in required if t not in covered],
        "exam_scorecard": build_examination_scorecard(session, case),
        "inv_scorecard": build_investigation_scorecard(session, case),
    }


def _label(key: str, master: dict[str, Any], case_specific: dict[str, Any]) -> str:
    """
    The master list's label wins, so the same test reads identically in every
    case. Falls back to the case's own label, then to the raw key.
    """
    if key in master:
        return str(master[key]["label"])
    return str(case_specific.get(key, {}).get("label", key))
