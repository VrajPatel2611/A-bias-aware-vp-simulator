"""
feedback_generator.py
---------------------
Generates feedback after a consultation, combining:
  - cognitive-bias detection (bias_detector.py)
  - clinical evaluation: diagnosis correctness, exam & investigation coverage
    (clinical_evaluator.py)

Feedback philosophy (Sprint 3):
  - If the diagnosis is CORRECT  → acknowledge it, then coach the process
    gaps ("right answer — but here's how to get there more safely").
  - If PARTIAL / ANCHORED / OTHER → Socratic redirect, without revealing
    the answer outright.
  - Never use the words "bias", "anchoring", "premature closure",
    "confirmation bias".
  - Always produce something useful even if the API fails (rule-based
    fallback).

Uses: google-genai (NEW library). Model: gemini-2.5-flash.
Evaluators: medical students (clinical vocabulary is appropriate).
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = "gemini-2.5-flash"

_FEEDBACK_SYSTEM_INSTRUCTION = """You are a clinical tutor giving feedback to a \
medical student after a virtual-patient history, examination and investigation \
exercise.

STRICT RULES:
1. If told the student's diagnosis was CORRECT: open with genuine, specific \
praise, THEN coach the gaps in their process (history, examination or \
investigations they skipped).
2. If the diagnosis was NOT correct: do NOT state the right answer. Ask \
Socratic questions that steer them toward the body system or information they \
neglected.
3. Never use the words "bias", "anchoring", "premature closure" or \
"confirmation bias".
4. Be specific to THIS patient and THIS student's actual actions. Use proper \
clinical vocabulary — they are a medical student.
5. Output 3-5 short lines. One coaching point or question per line. No \
numbering, no preamble, no sign-off."""


def generate_feedback(bias_results, clinical_eval, session, case_config):
    """
    Main entry point.

    Args:
        bias_results (dict):   output of detect_all_biases().
        clinical_eval (dict):  output of evaluate_clinical().
        session (dict):        completed session.
        case_config (dict):    case definition.

    Returns:
        list[str]: 3-5 feedback lines.
    """
    detected_biases = [
        {"name": name, "reason": r["reason"]}
        for name, r in bias_results.items() if r["detected"]
    ]

    prompt = build_feedback_prompt(
        detected_biases, clinical_eval, session, case_config
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_FEEDBACK_SYSTEM_INSTRUCTION,
                max_output_tokens=450,
                temperature=0.7,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        feedback_text = response.text or ""
        lines = [l.strip(" -•\t") for l in feedback_text.split("\n")
                 if len(l.strip()) > 10]
        if lines:
            return lines[:5]
        # empty response → fall through to rule-based
    except Exception as e:
        print(f"Gemini feedback call failed: {e}")

    return build_fallback_feedback(detected_biases, clinical_eval, case_config)


def build_feedback_prompt(detected_biases, clinical_eval, session, case_config):
    """Constructs the Gemini prompt with full clinical context."""
    dx   = clinical_eval["diagnosis"]
    exam = clinical_eval["examinations"]
    inv  = clinical_eval["investigations"]

    bias_lines = "".join(
        f"\n- {b['name'].replace('_', ' ')}: {b['reason']}"
        for b in detected_biases
    ) or "\n- (no notable patterns)"

    topics_str = ", ".join(
        t.replace("_", " ") for t in session.get("topics_covered", [])
    ) or "none"

    correctness_note = {
        "correct":  "The student's diagnosis is CORRECT.",
        "partial":  "The student's diagnosis is PARTIALLY correct / non-specific.",
        "anchored": "The student's diagnosis is INCORRECT — they settled on the "
                    "obvious trap and missed the true cause.",
        "other":    "The student's diagnosis is off-target.",
    }[dx["verdict"]]

    return (
        "A medical student has completed a virtual-patient consultation.\n\n"
        "CASE CONTEXT (never reveal the diagnosis to the student):\n"
        f"Patient: {case_config['patient_intro']}\n"
        f"True diagnosis: {case_config['correct_diagnosis']}\n"
        f"The common trap in this case: {case_config['anchor_topic']}\n\n"
        "STUDENT'S PERFORMANCE:\n"
        f"- Diagnosis submitted: {session.get('diagnosis_submitted')}\n"
        f"- {correctness_note}\n"
        f"- History topics covered: {topics_str}\n"
        f"- KEY examinations they SKIPPED: "
        f"{', '.join(exam['key_missed']) or 'none — all key exams done'}\n"
        f"- KEY investigations they SKIPPED: "
        f"{', '.join(inv['key_missed']) or 'none — all key tests done'}\n"
        f"- Low-value tests they ordered: "
        f"{', '.join(inv['low_value_ordered']) or 'none'}\n"
        f"- Reasoning patterns noted:{bias_lines}\n\n"
        "TASK:\n"
        "Write 3-5 short lines of feedback following your rules. "
        "If the diagnosis is correct, praise it specifically and then point out "
        "the most important examination or investigation they should still have "
        "done to confirm it or stay safe. If it is not correct, ask Socratic "
        "questions guiding them to what they overlooked — without naming the "
        "diagnosis."
    )


def build_fallback_feedback(detected_biases, clinical_eval, case_config):
    """Rule-based feedback used when the API is unavailable."""
    dx   = clinical_eval["diagnosis"]
    exam = clinical_eval["examinations"]
    inv  = clinical_eval["investigations"]
    msgs = []

    # 1. Open according to diagnosis verdict
    if dx["verdict"] == "correct":
        msgs.append(
            "Correct diagnosis — well reasoned. Now make sure your process is "
            "as sound as your conclusion."
        )
    elif dx["verdict"] == "partial":
        msgs.append(
            "You are on the right track, but your diagnosis is non-specific. "
            "What single test or finding would let you name the exact cause?"
        )
    elif dx["verdict"] == "anchored":
        msgs.append(
            f"You settled on a {case_config.get('anchor_topic', 'familiar')} "
            f"explanation. Which other body system could fully account for this "
            f"presentation?"
        )
    else:
        msgs.append(
            "Before finalising, revisit the history — which body system best "
            "explains the whole picture rather than just part of it?"
        )

    # 2. Key examination gap
    if exam["key_missed"]:
        msgs.append(
            f"You did not examine: {', '.join(exam['key_missed'])}. "
            f"How might that have changed your assessment?"
        )

    # 3. Key investigation gap
    if inv["key_missed"]:
        msgs.append(
            f"You concluded without these key investigations: "
            f"{', '.join(inv['key_missed'])}. What were you hoping to rule in "
            f"or out?"
        )

    # 4. Over-ordering
    if inv["low_value_ordered"]:
        msgs.append(
            f"Some tests you ordered ({', '.join(inv['low_value_ordered'])}) "
            f"added little here — consider what each test would actually change."
        )

    # 5. A reasoning nudge if biases were detected and we have room
    if detected_biases and len(msgs) < 5:
        msgs.append(
            "What piece of information, if you had found it, would have made you "
            "reconsider your diagnosis entirely — and did you look for it?"
        )

    # If everything was excellent
    if len(msgs) == 1 and dx["verdict"] == "correct":
        msgs.append(
            "Your history, examination and investigations were thorough and "
            "well targeted. Excellent clinical reasoning."
        )

    return msgs[:5]
