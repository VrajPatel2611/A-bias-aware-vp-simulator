"""
bias_detector.py
----------------
Detects three cognitive biases from a completed consultation session.
Called by app.py after user submits diagnosis via POST /conclude.

Three bias types detected:
  1. Anchoring — fixating on the most obvious symptom
  2. Premature closure — concluding before thorough workup
  3. Confirmation bias — only seeking confirming evidence

All detection logic is derived from docs/pseudocode.md Section MODULE 2.
Each detector returns a dict:
  {detected: bool, score: float 0-1, reason: str, evidence: list}
"""


def detect_all_biases(session, case_config):
    """
    Main entry point. Runs all three bias detectors and returns combined
    results. This is the only function app.py calls from this module.

    Args:
        session (dict): Completed session from session_tracker.
        case_config (dict): Case definition from cases.py.

    Returns:
        dict: {
            "anchoring": {detected, score, reason, evidence},
            "premature_closure": {detected, score, reason, evidence},
            "confirmation_bias": {detected, score, reason, evidence}
        }
    """
    return {
        "anchoring": detect_anchoring(session, case_config),
        "premature_closure": detect_premature_closure(session, case_config),
        "confirmation_bias": detect_confirmation_bias(session, case_config),
    }


def detect_anchoring(session, case_config):
    """
    Checks if user over-focused on the anchor topic without
    exploring alternative explanations.

    Rule A1: More than 60% of questions about anchor topic
             (requires at least 4 total questions to avoid noise)
    Rule A2: Asked 3+ anchor questions but zero alternative questions
             (strong signal even if overall question count is low)

    Args:
        session (dict): Session dict with questions_asked list.
        case_config (dict): Has anchor_keywords and alternative_topics.

    Returns:
        dict: {detected: bool, score: float 0-1, reason: str, evidence: list}
    """
    anchor_keywords = case_config["anchor_keywords"]
    alternative_topics = case_config["alternative_topics"]
    all_questions = session["questions_asked"]
    total_questions = session["question_count"]

    # Count questions containing anchor keywords
    anchor_question_count = 0
    anchor_evidence = []

    for question in all_questions:
        q_lower = question.lower()
        for kw in anchor_keywords:
            if kw in q_lower:
                anchor_question_count += 1
                anchor_evidence.append(question)
                break  # count each question once

    # Count questions containing alternative topic keywords
    alternative_question_count = 0
    for question in all_questions:
        q_lower = question.lower()
        for kw in alternative_topics:
            if kw in q_lower:
                alternative_question_count += 1
                break  # count each question once

    # Rule A1: topic concentration > 60%
    detected_A1 = False
    score_A1 = 0.0
    if total_questions >= 4:
        concentration = anchor_question_count / total_questions
        if concentration > 0.60:
            detected_A1 = True 
            score_A1 = round(concentration, 2)

    # Rule A2: 3+ anchor questions with zero alternative exploration
    detected_A2 = False
    score_A2 = 0.0
    if anchor_question_count >= 3 and alternative_question_count == 0:
        detected_A2 = True
        score_A2 = 0.85

    detected = detected_A1 or detected_A2
    score = max(score_A1, score_A2)

    if detected:
        reason = (
            f"{anchor_question_count} of your {total_questions} questions "
            f"focused on {case_config['anchor_topic']} symptoms. "
            f"You asked {alternative_question_count} questions exploring "
            f"alternative causes."
        )
    else:
        reason = "No significant anchoring pattern detected."

    return {
        "detected": detected,
        "score": score,
        "reason": reason,
        "evidence": anchor_evidence[:3],  # max 3 examples to keep output concise
    }


def detect_premature_closure(session, case_config):
    """
    Checks if user concluded before conducting a thorough workup.

    Rule P1: Fewer total questions than the minimum threshold
    Rule P2: Covered fewer than 60% of required clinical history topics

    Args:
        session (dict): Session dict with question_count and topics_covered.
        case_config (dict): Has minimum_questions and required_topics.

    Returns:
        dict: {detected: bool, score: float 0-1, reason: str, evidence: list}
              evidence contains list of missed topic names
    """
    minimum_questions = case_config["minimum_questions"]
    required_topics = case_config["required_topics"]
    topics_covered = session["topics_covered"]
    question_count = session["question_count"]

    # Rule P1: too few total questions asked
    detected_P1 = False
    score_P1 = 0.0
    if question_count < minimum_questions:
        detected_P1 = True
        score_P1 = max(
            round(1.0 - (question_count / minimum_questions), 2),
            0.1   # minimum score of 0.1 if detected
        )

    # Rule P2: too few required topics covered
    topics_hit = [t for t in required_topics if t in topics_covered]
    total_required = len(required_topics)
    coverage_ratio = len(topics_hit) / total_required if total_required > 0 else 1.0

    detected_P2 = False
    score_P2 = 0.0
    if coverage_ratio < 0.60:
        detected_P2 = True
        score_P2 = round(1.0 - coverage_ratio, 2)

    detected = detected_P1 or detected_P2
    score = max(score_P1, score_P2)

    topics_missed = [t for t in required_topics if t not in topics_covered]
    # Human-readable names for missed topics
    missed_display = [t.replace("_", " ") for t in topics_missed]

    if detected_P1 and detected_P2:
        reason = (
            f"You asked only {question_count} questions "
            f"(minimum recommended: {minimum_questions}) and covered "
            f"{len(topics_hit)} of {total_required} key history areas. "
            f"Areas not explored: {', '.join(missed_display)}."
        )
    elif detected_P1:
        reason = (
            f"You submitted a diagnosis after only {question_count} questions. "
            f"A thorough workup typically requires at least {minimum_questions}."
        )
    elif detected_P2:
        reason = (
            f"You covered {len(topics_hit)} of {total_required} key history "
            f"areas before concluding. "
            f"Areas not explored: {', '.join(missed_display)}."
        )
    else:
        reason = "No premature closure detected — thorough workup completed."

    return {
        "detected": detected,
        "score": score,
        "reason": reason,
        "evidence": missed_display,
    }


def detect_confirmation_bias(session, case_config):
    """
    Checks if user only sought confirming evidence for their
    initial assumption and never explored contradictory information.

    Rule C1: Submitted an anchor diagnosis AND explored 0 contradictory clues
    Rule C2: Explored fewer than 25% of contradictory clues overall
             (regardless of diagnosis, if at least 5 questions asked)

    Contradictory clue detection uses significant words (length > 4)
    extracted from each clue description string in case_config.

    Args:
        session (dict): Session dict with questions_asked and diagnosis_submitted.
        case_config (dict): Has contradictory_clues and anchor_keywords.

    Returns:
        dict: {detected: bool, score: float 0-1, reason: str, evidence: list}
    """
    contradictory_clues = case_config["contradictory_clues"]
    anchor_keywords = case_config["anchor_keywords"]
    all_questions = session["questions_asked"]
    diagnosis = session.get("diagnosis_submitted") or ""
    total_clues = len(contradictory_clues)

    # Count how many contradictory clue topics the user asked about
    clues_explored = 0
    for clue in contradictory_clues:
        clue_lower = clue.lower()
        # Extract words > 4 chars as significant clinical terms
        significant_words = [w for w in clue_lower.split() if len(w) > 4]
        clue_found = False
        for question in all_questions:
            q_lower = question.lower()
            for word in significant_words:
                if word in q_lower:
                    clues_explored += 1
                    clue_found = True
                    break
            if clue_found:
                break  # count each clue once

    # Rule C1: diagnosed anchor topic but never explored any contradictory clues
    detected_C1 = False
    score_C1 = 0.0
    diagnosis_matches_anchor = False

    if diagnosis:
        d_lower = diagnosis.lower()
        for kw in anchor_keywords:
            if kw in d_lower:
                diagnosis_matches_anchor = True
                break

    if diagnosis_matches_anchor and clues_explored == 0:
        detected_C1 = True
        score_C1 = 0.90

    # Rule C2: less than 25% of contradictory clues explored
    detected_C2 = False
    score_C2 = 0.0
    if total_clues > 0:
        exploration_ratio = clues_explored / total_clues
        if exploration_ratio < 0.25 and len(all_questions) >= 5:
            detected_C2 = True
            score_C2 = round(1.0 - exploration_ratio, 2)

    detected = detected_C1 or detected_C2
    score = max(score_C1, score_C2)

    if detected:
        reason = (
            f"You explored {clues_explored} of {total_clues} key pieces of "
            f"information that could have challenged your initial assumption. "
            f"Confirmation bias occurs when we seek only evidence that supports "
            f"our first instinct."
        )
    else:
        reason = "No significant confirmation bias detected."

    return {
        "detected": detected,
        "score": score,
        "reason": reason,
        "evidence": [
            f"Only {clues_explored}/{total_clues} contradictory areas explored"
        ],
    }
