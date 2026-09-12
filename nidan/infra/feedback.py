"""
Feedback generation — the I/O half.

Calls the language model and falls back to deterministic rule-based feedback if
it is unavailable, so no consultation ever ends without guidance.

The model writes prose only. It never influences a flag, a score or a verdict
(PR-1, ADR-0005).
"""

from typing import NamedTuple

from nidan.domain.feedback import (
    _FEEDBACK_SYSTEM_INSTRUCTION,
    build_fallback_feedback,
    build_feedback_prompt,
)
from nidan.infra.llm.gateway import call_llm


class FeedbackResult(NamedTuple):
    """
    Feedback lines and which half of this module produced them.

    `feedback_texts.generator` (migration 012) is a CHECK-constrained column
    accepting 'llm' or 'rule_fallback', and it earns its place: the fallback
    fires on a timeout or a rate limit, silently and by design, so without this
    the only record of how often the model was actually unavailable would be a
    printed line in a log nobody reads.
    """

    lines: list
    generator: str          # 'llm' | 'rule_fallback'


def generate_feedback(bias_results, clinical_eval, session, case_config):
    """
    Main entry point. Returns the lines only — see `generate_feedback_with_source`
    when the caller needs to record which generator produced them.

    Args:
        bias_results (dict):   output of detect_all_biases().
        clinical_eval (dict):  output of evaluate_clinical().
        session (dict):        completed session.
        case_config (dict):    case definition.

    Returns:
        list[str]: 3-5 feedback lines.
    """
    return generate_feedback_with_source(
        bias_results, clinical_eval, session, case_config).lines


def generate_feedback_with_source(bias_results, clinical_eval, session,
                                  case_config) -> FeedbackResult:
    """
    As `generate_feedback`, but also says which generator produced the lines.

    Returns:
        FeedbackResult: (lines, 'llm' | 'rule_fallback')
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
            return FeedbackResult(lines[:5], "llm")
        # empty response → fall through to rule-based
    except Exception as e:
        print(f"LLM feedback call failed: {e}")

    return FeedbackResult(
        build_fallback_feedback(detected_biases, clinical_eval, case_config),
        "rule_fallback")
