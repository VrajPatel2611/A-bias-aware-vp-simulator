"""
Feedback generation — the I/O half.

Calls the language model and falls back to deterministic rule-based feedback if
it is unavailable, so no consultation ever ends without guidance.

The model writes prose only. It never influences a flag, a score or a verdict
(PR-1, ADR-0005).
"""

from nidan.domain.feedback import (
    _FEEDBACK_SYSTEM_INSTRUCTION,
    build_fallback_feedback,
    build_feedback_prompt,
)
from nidan.infra.llm.gateway import call_llm


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
        feedback_text = call_llm(
            messages=[{"role": "user", "content": prompt}],
            system_instruction=_FEEDBACK_SYSTEM_INSTRUCTION,
            purpose="feedback",
            max_tokens=450,
            temperature=0.7,
        )
        lines = [line.strip(" -•\t") for line in feedback_text.split("\n")
                 if len(line.strip()) > 10]
        if lines:
            return lines[:5]
        # empty response → fall through to rule-based
    except Exception as e:
        print(f"LLM feedback call failed: {e}")

    return build_fallback_feedback(detected_biases, clinical_eval, case_config)
