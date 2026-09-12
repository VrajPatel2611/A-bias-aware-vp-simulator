"""
Session state.

Tracks what the learner does during one consultation: questions asked, topics
covered, examinations performed, investigations ordered, diagnosis submitted.

Pure — no I/O. Persistence lives in infra/storage.py.

NOTE (BUILD_PLAN T-013): this module currently mutates a dict held in memory.
It will be replaced by reconstruction from an append-only event log (ADR-0003).
The function signatures are kept stable so that change is contained.
"""

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from nidan.domain.assessment.topics import extract_topics
from nidan.domain.events import Event
from nidan.domain.types import Case, Session


def create_session(case_id: str, *, started_at: str) -> Session:
    """
    Creates a fresh session dictionary for a new consultation.

    Args:
        case_id (str): e.g. "case_1"
        started_at (str): ISO 8601 timestamp. Passed in rather than read from
            the clock so that this function is pure and its output depends only
            on its arguments — see nidan.infra.clock for why.

    Returns:
        dict: Empty session with all tracking fields initialized.
    """
    return {
        "case_id": case_id,
        "question_count": 0,
        "questions_asked": [],      # list of all user message strings
        "topics_covered": [],       # list of topic names detected so far
        "exams_performed": [],      # list of examination keys performed
        "investigations_ordered": [],  # list of investigation keys ordered
        "early_diagnosis": None,    # if user mentions diagnosis mid-consult
        "diagnosis_submitted": None,  # final diagnosis string from /conclude
        "start_time": started_at,
        "end_time": None,
    }


def record_exam(session: Session, exam_key: str) -> Session:
    """Records an examination performed (deduplicated). Returns session."""
    if exam_key not in session["exams_performed"]:
        session["exams_performed"].append(exam_key)
    return session


def record_investigation(session: Session, investigation_key: str) -> Session:
    """Records an investigation ordered (deduplicated). Returns session."""
    if investigation_key not in session["investigations_ordered"]:
        session["investigations_ordered"].append(investigation_key)
    return session


# Phrases that mark a learner committing to a diagnosis mid-consultation. Not a
# judgement on its own — anchoring is about what they asked afterwards.
EARLY_DIAGNOSIS_PHRASES: tuple[str, ...] = (
    "i think it is", "i think this is", "this looks like",
    "probably ", "could be ", "i believe", "my diagnosis",
    "seems like", "this is a case of", "i suspect",
    "it is likely", "most likely",
)


def mentions_early_diagnosis(user_message: str) -> bool:
    """
    Whether this message commits to a diagnosis.

    Split out of `update_session` in T-013 so the event writer can ask the same
    question before appending an `early_diagnosis` event. One phrase list, so
    a session replayed from events and a session built in memory cannot
    disagree about what counts.
    """
    lowered = user_message.lower()
    return any(phrase in lowered for phrase in EARLY_DIAGNOSIS_PHRASES)


def update_session(session: Session, user_message: str) -> Session:
    """
    Updates session after every user message.
    Increments question count, extracts topics, checks for early diagnosis.

    Args:
        session (dict): Current session dict from server-side store.
        user_message (str): The raw text the user just sent.

    Returns:
        dict: Updated session dict (mutated in place, also returned).
    """
    # Step 1: increment question counter
    session["question_count"] += 1

    # Step 2: add raw message to history
    session["questions_asked"].append(user_message)

    # Step 3: extract topics from this message
    new_topics = extract_topics(user_message)

    # Step 4: add any new topics not already in covered list
    for topic in new_topics:
        if topic not in session["topics_covered"]:
            session["topics_covered"].append(topic)

    # Step 5: check for early diagnosis mention
    if session["early_diagnosis"] is None and mentions_early_diagnosis(user_message):
        session["early_diagnosis"] = user_message

    return session


def get_session_summary(session: Session, case_config: Case) -> dict[str, Any]:
    """
    Returns a readable summary dict for the post-session display screen.
    Used to show the user what they covered and missed.

    Args:
        session (dict): Completed session dict.
        case_config (dict): The case definition from cases.py.

    Returns:
        dict: Summary with coverage stats and missed topics.
    """
    required = case_config["required_topics"]
    covered = session["topics_covered"]

    topics_hit = [t for t in required if t in covered]
    topics_missed = [t for t in required if t not in covered]
    coverage_percent = (
        round((len(topics_hit) / len(required)) * 100) if required else 0
    )

    # Calculate time taken
    time_taken = None
    end_time = session.get("end_time")
    start_time = session.get("start_time")
    if end_time and start_time:
        try:
            end_dt = datetime.fromisoformat(end_time)
            start_dt = datetime.fromisoformat(start_time)
            time_taken = int((end_dt - start_dt).total_seconds())
        except Exception:
            time_taken = None

    return {
        "questions_asked": session["question_count"],
        "topics_covered_count": len(topics_hit),
        "topics_required_count": len(required),
        "coverage_percent": coverage_percent,
        "topics_missed": [t.replace("_", " ") for t in topics_missed],
        "exams_performed_count": len(session.get("exams_performed", [])),
        "investigations_ordered_count": len(session.get("investigations_ordered", [])),
        "diagnosis_given": session["diagnosis_submitted"],
        "time_taken_seconds": time_taken,
    }


# ── replay (BUILD_PLAN T-013, ADR-0003) ──────────────────────────────

def replay(events: Iterable[Event], *, case_id: str, started_at: str) -> Session:
    """
    Rebuild session state from the append-only event log.

    Returns exactly the shape `create_session` produces, so the assessment
    engine, the feedback builder and the templates are unaffected by where the
    state came from. That was the promise this module made in T-001 when it
    said the signatures were kept stable so the change would be contained.

    **A pure fold. Nothing is re-derived.** Topics come from
    `patient_reply.matched_topics` rather than from re-running `extract_topics`
    over the questions, and an early diagnosis comes from its own event rather
    than from re-scanning the text. `DATA_MODEL` §8.2 is explicit about why:
    those payloads record *what the system understood at the time*, under the
    engine version then current. Recomputing them here would make a replay
    agree with today's code by construction, and destroy the drift signal that
    recomputation exists to detect (T-016).

    `case_id` and `started_at` come from the `sessions` row, which is the only
    state a consultation keeps outside the log.
    """
    session = create_session(case_id, started_at=started_at)

    for event in events:
        payload = event.payload

        if event.type == "question":
            session["question_count"] += 1
            session["questions_asked"].append(payload["text"])

        elif event.type == "patient_reply":
            for topic in payload.get("matched_topics", []):
                if topic not in session["topics_covered"]:
                    session["topics_covered"].append(topic)

        elif event.type == "examination":
            record_exam(session, payload["key"])

        elif event.type == "investigation":
            record_investigation(session, payload["key"])

        elif event.type == "early_diagnosis":
            # First one wins, matching update_session: the point is what they
            # committed to first, not what they revised it to.
            if session["early_diagnosis"] is None:
                session["early_diagnosis"] = payload["text"]

        elif event.type == "diagnosis":
            session["diagnosis_submitted"] = payload["text"]
            if event.created_at is not None:
                session["end_time"] = event.created_at.isoformat()

        # feedback_viewed and input_blocked change no state by design. The
        # first is analytics; the second deliberately records that something
        # was refused without recording what it was.

    return session


def conversation_from(events: Iterable[Event]) -> list[dict[str, str]]:
    """
    Rebuild the chat transcript for the next LLM call.

    Roles are "user"/"model" because that is what the templates and the
    existing gateway mapping expect.
    """
    conversation: list[dict[str, str]] = []
    for event in events:
        if event.type == "question":
            conversation.append({"role": "user", "content": event.payload["text"]})
        elif event.type == "patient_reply":
            conversation.append({"role": "model", "content": event.payload["text"]})
    return conversation
