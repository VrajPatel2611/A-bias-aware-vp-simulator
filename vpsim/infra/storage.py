"""
Session persistence.

Reads and writes completed-session JSON files. This is an I/O boundary — the
domain layer must never import it (ADR-0009).

NOTE (BUILD_PLAN T-010/T-013): superseded by PostgreSQL. Kept so the prototype
keeps working during the restructure.
"""

import json
import os

from vpsim.infra.clock import utc_now_iso


def count_prior_sessions(sessions_dir, participant_id):
    """
    Counts how many saved session files already belong to a participant.

    Used to assign a session sequence number (1st case = 1, 2nd case = 2, ...)
    so that a participant's Case 1 (before feedback) and Case 2 (after feedback)
    sessions can be linked for the within-subject pre/post analysis.

    Matching is exact on the stored participant.participant_id field. Files that
    cannot be read or have no participant id are skipped.

    Args:
        sessions_dir (str): Folder holding the session JSON files.
        participant_id (str): The participant to count sessions for.

    Returns:
        int: Number of existing sessions for this participant (0 if the id is
             blank or the folder does not exist).
    """
    if not participant_id:
        return 0
    if not os.path.isdir(sessions_dir):
        return 0

    count = 0
    for fname in os.listdir(sessions_dir):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(sessions_dir, fname)
        try:
            with open(path, encoding="utf-8") as f:
                record = json.load(f)
        except Exception:
            continue  # skip unreadable / malformed files
        if record.get("participant", {}).get("participant_id", "") == participant_id:
            count += 1
    return count


def save_session_file(session_id, case_id, case, session_data,
                       pre_case_data, bias_results, clinical_eval,
                       feedback_messages):
    """
    Saves completed session as JSON in sessions/ folder.
    Includes pre-case questionnaire + clinical evaluation for analysis.

    Returns:
        str | None: the path written, or None if the filesystem refused it.
        The return value is what lets a test assert a file was actually
        produced — asserting the route returned 200 does not, which is how a
        broken save went unnoticed for a whole task.
    """
    try:
        os.makedirs("sessions", exist_ok=True)
        # Compact stamp for the filename, derived from the ISO clock string
        # (2026-01-01T09:00:00+00:00 -> 20260101_090000).
        iso = utc_now_iso()
        timestamp = iso[:19].replace("-", "").replace(":", "").replace("T", "_")

        # ── Participant linking (for within-subject pre/post analysis) ────
        # Sequence = how many sessions this participant has already completed,
        # plus one. Computed BEFORE writing this file so it is not counted.
        participant_id = (pre_case_data.get("participant_id", "") or "").strip()
        session_sequence = count_prior_sessions("sessions", participant_id) + 1
        # Filesystem-safe participant id for the filename (falls back to "anon").
        safe_pid = "".join(
            c for c in participant_id if c.isalnum() or c in "-_"
        ) or "anon"

        stem     = f"{safe_pid}_{case_id}_seq{session_sequence}_{timestamp}"
        filename = f"sessions/{stem}.json"

        log = {
            "session_id":       stem,
            "case_id":          case_id,
            "case_title":       case["title"],
            "correct_diagnosis": case["correct_diagnosis"],
            # Pre-case questionnaire data (evaluation metadata)
            "participant": {
                "participant_id":   participant_id,
                "session_sequence": session_sequence,
                "year_of_study":    pre_case_data.get("year_of_study", ""),
                "confidence_pre":   pre_case_data.get("confidence", ""),
            },
            "start_time":       session_data.get("start_time"),
            "end_time":         session_data.get("end_time"),
            "question_count":   session_data["question_count"],
            "questions_asked":  session_data["questions_asked"],
            "topics_covered":   session_data["topics_covered"],
            "exams_performed":  session_data.get("exams_performed", []),
            "investigations_ordered": session_data.get("investigations_ordered", []),
            "early_diagnosis":  session_data.get("early_diagnosis"),
            "diagnosis_submitted": session_data["diagnosis_submitted"],
            "diagnosis_verdict": clinical_eval["diagnosis"]["verdict"],
            "biases_detected":  bias_results,
            "clinical_eval":    clinical_eval,
            "feedback_given":   feedback_messages,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

        print(f"Session saved: {filename}")
        return filename

    except OSError as e:
        # Disk full, permissions, read-only filesystem — degrade rather than
        # lose the consultation the learner just finished.
        #
        # Deliberately NOT `except Exception`. A bare catch here hid a NameError
        # for the whole of T-001: every save failed, the route still returned
        # 200, and no session file was ever written. A programming error must
        # surface, not be reported as a disk problem.
        print(f"Warning: could not write session file: {e}")
        return None
