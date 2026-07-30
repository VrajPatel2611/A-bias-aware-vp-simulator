"""
clinical_evaluator.py
----------------------
Evaluates the CLINICAL quality of a consultation (Sprint 3), complementing
the cognitive-bias detection in bias_detector.py.

Three assessments:
  1. assess_diagnosis        — was the submitted diagnosis correct / partial /
                               anchored (the trap) / off-target?
  2. assess_examinations     — which KEY examinations were performed vs skipped?
  3. assess_investigations   — which KEY investigations were ordered, which were
                               missed, and were low-value tests over-ordered?

Called by app.py /conclude. Output is consumed by feedback_generator.py
(for tone + content) and the feedback page (for display).
"""


# ── Diagnosis correctness ─────────────────────────────────────────────

def assess_diagnosis(diagnosis, case_config):
    """
    Classifies the submitted diagnosis.

    Verdicts:
      "correct"  — matches an accepted diagnosis phrase
      "partial"  — on the right track but non-specific
      "anchored" — matches the case's anchor (the diagnostic trap)
      "other"    — none of the above

    Accepted phrases are checked FIRST so "not cardiac, likely GERD"
    scores as correct rather than anchored.

    Returns:
        dict: {verdict, label, matched}
    """
    text = (diagnosis or "").lower()

    accepted = case_config.get("accepted_diagnoses", [])
    partial  = case_config.get("partial_diagnoses", [])
    anchor   = case_config.get("anchor_keywords", [])

    for phrase in accepted:
        if phrase in text:
            return {"verdict": "correct", "label": "Correct diagnosis",
                    "matched": phrase}

    for phrase in partial:
        if phrase in text:
            return {"verdict": "partial", "label": "On the right track",
                    "matched": phrase}

    for phrase in anchor:
        if phrase in text:
            return {"verdict": "anchored",
                    "label": f"Anchored on {case_config.get('anchor_topic', 'the obvious cause')}",
                    "matched": phrase}

    return {"verdict": "other", "label": "Worth reconsidering", "matched": None}


# ── Examination coverage ──────────────────────────────────────────────

def assess_examinations(session, case_config):
    """
    Compares examinations performed against the KEY examinations for the case.

    Returns:
        dict: {
            performed:   [labels performed],
            key_done:    [labels of key exams performed],
            key_missed:  [labels of key exams skipped],
            total_key:   int
        }
    """
    exam_defs = case_config.get("examination", {})
    performed_keys = session.get("exams_performed", [])

    key_keys = [k for k, v in exam_defs.items() if v.get("key")]

    performed_labels = [
        exam_defs[k]["label"] for k in performed_keys if k in exam_defs
    ]
    key_done = [
        exam_defs[k]["label"] for k in key_keys if k in performed_keys
    ]
    key_missed = [
        exam_defs[k]["label"] for k in key_keys if k not in performed_keys
    ]

    return {
        "performed":  performed_labels,
        "key_done":   key_done,
        "key_missed": key_missed,
        "total_key":  len(key_keys),
    }


# ── Investigation appropriateness ─────────────────────────────────────

def assess_investigations(session, case_config):
    """
    Compares investigations ordered against the case's categorised tests.

    Categories per test: "key", "reasonable", "low_value".

    Returns:
        dict: {
            ordered:           [labels ordered],
            key_done:          [labels of key tests ordered],
            key_missed:        [labels of key tests not ordered],
            low_value_ordered: [labels of low-value tests ordered],
            total_key:         int
        }
    """
    inv_defs = case_config.get("investigations", {})
    ordered_keys = session.get("investigations_ordered", [])

    key_keys = [k for k, v in inv_defs.items() if v.get("category") == "key"]

    ordered_labels = [
        inv_defs[k]["label"] for k in ordered_keys if k in inv_defs
    ]
    key_done = [
        inv_defs[k]["label"] for k in key_keys if k in ordered_keys
    ]
    key_missed = [
        inv_defs[k]["label"] for k in key_keys if k not in ordered_keys
    ]
    low_value_ordered = [
        inv_defs[k]["label"] for k in ordered_keys
        if k in inv_defs and inv_defs[k].get("category") == "low_value"
    ]

    return {
        "ordered":           ordered_labels,
        "key_done":          key_done,
        "key_missed":        key_missed,
        "low_value_ordered": low_value_ordered,
        "total_key":         len(key_keys),
    }


def evaluate_clinical(session, case_config):
    """
    Convenience wrapper — runs all three clinical assessments.

    Returns:
        dict: {diagnosis, examinations, investigations}
    """
    return {
        "diagnosis":      assess_diagnosis(session.get("diagnosis_submitted"),
                                           case_config),
        "examinations":   assess_examinations(session, case_config),
        "investigations": assess_investigations(session, case_config),
    }
