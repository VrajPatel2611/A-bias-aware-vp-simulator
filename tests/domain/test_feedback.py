"""
Feedback — nidan.domain.feedback (prompt building) and nidan.infra.feedback
(the model call).

The split matters: deciding *what to say* is domain logic and testable with no
network; calling the model is infrastructure. The fallback path below runs with
no model at all, which is what guarantees no consultation ends without guidance.
"""

from nidan.domain.assessment.bias import detect_all_biases
from nidan.domain.assessment.clinical import evaluate_clinical
from nidan.domain.feedback import build_fallback_feedback, build_feedback_prompt
from nidan.infra.feedback import generate_feedback
from tests.fakes.llm import FakeLLMError

BANNED = ["bias", "anchoring", "premature closure", "confirmation bias"]


def _inputs(case, session_factory):
    s = session_factory(questions=["Could this be a heart problem?"] * 4,
                        diagnosis="Myocardial infarction")
    return detect_all_biases(s, case), evaluate_clinical(s, case), s


class TestPromptBuilding:
    def test_builds_a_non_empty_prompt(self, case, session_factory):
        bias, clinical, s = _inputs(case, session_factory)
        assert build_feedback_prompt([], clinical, s, case).strip()

    def test_is_pure_and_needs_no_network(self, case, session_factory):
        """The autouse guard is active; reaching a real client would fail the test."""
        bias, clinical, s = _inputs(case, session_factory)
        detected = [{"name": n, "reason": r["reason"]}
                    for n, r in bias.items() if r["detected"]]
        assert build_feedback_prompt(detected, clinical, s, case)


class TestFallbackFeedback:
    """The path taken when the model is unavailable."""

    def test_produces_lines_with_no_model(self, case, session_factory):
        bias, clinical, s = _inputs(case, session_factory)
        detected = [{"name": n, "reason": r["reason"]}
                    for n, r in bias.items() if r["detected"]]
        assert build_fallback_feedback(detected, clinical, case)

    def test_never_returns_empty(self, case, session_factory):
        """No consultation may end without guidance, even with nothing detected."""
        bias, clinical, s = _inputs(case, session_factory)
        assert build_fallback_feedback([], clinical, case)

    def test_uses_no_bias_vocabulary(self, case, session_factory):
        """PRD P1 / contract test CT-5 — this text is shown to the learner."""
        bias, clinical, s = _inputs(case, session_factory)
        detected = [{"name": n, "reason": r["reason"]}
                    for n, r in bias.items() if r["detected"]]
        text = " ".join(build_fallback_feedback(detected, clinical, case)).lower()
        for word in BANNED:
            assert word not in text, f"user-facing feedback used the word {word!r}"


class TestGenerateFeedbackUsesTheGateway:
    def test_calls_the_model_once_for_the_feedback_purpose(self, case, session_factory, fake_llm):
        fake_llm.replies = ["You focused early on a cardiac cause.\n"
                            "Consider what argued against it.\n"
                            "The meal relationship was the key clue."]
        bias, clinical, s = _inputs(case, session_factory)
        generate_feedback(bias, clinical, s, case)
        assert fake_llm.call_count == 1
        assert fake_llm.purposes_used() == ["feedback"]

    def test_returns_the_model_lines(self, case, session_factory, fake_llm):
        fake_llm.replies = ["First observation about the reasoning.\n"
                            "Second observation about the workup."]
        bias, clinical, s = _inputs(case, session_factory)
        assert len(generate_feedback(bias, clinical, s, case)) == 2

    def test_caps_the_number_of_lines(self, case, session_factory, fake_llm):
        fake_llm.replies = ["\n".join(f"Observation number {i} about reasoning." for i in range(12))]
        bias, clinical, s = _inputs(case, session_factory)
        assert len(generate_feedback(bias, clinical, s, case)) <= 5

    def test_falls_back_when_the_model_fails(self, case, session_factory, fake_llm):
        """A provider outage must degrade, not raise. The learner still gets feedback."""
        fake_llm.fail_with = FakeLLMError("provider down")
        bias, clinical, s = _inputs(case, session_factory)
        assert generate_feedback(bias, clinical, s, case)

    def test_falls_back_when_the_model_returns_nothing_usable(self, case, session_factory, fake_llm):
        fake_llm.replies = ["   \n  \n "]
        bias, clinical, s = _inputs(case, session_factory)
        assert generate_feedback(bias, clinical, s, case)


class TestFallbackOpensAccordingToTheVerdict:
    """
    Every diagnosis verdict must produce an opening line. A missing branch
    would leave a learner with feedback that begins mid-thought.
    """

    def _fallback(self, case, session_factory, diagnosis):
        s = session_factory(questions=["q"] * 8, diagnosis=diagnosis)
        return " ".join(build_fallback_feedback([], evaluate_clinical(s, case), case))

    def test_correct_diagnosis_opens_with_praise(self, case, session_factory):
        assert "Correct diagnosis" in self._fallback(case, session_factory, "GERD")

    def test_partial_diagnosis_asks_for_specificity(self, case, session_factory):
        assert "non-specific" in self._fallback(case, session_factory, "indigestion")

    def test_anchored_diagnosis_names_the_anchor_neutrally(self, case, session_factory):
        text = self._fallback(case, session_factory, "Myocardial infarction")
        assert "other body system" in text
        assert "anchor" not in text.lower()      # PRD P1

    def test_unrecognised_diagnosis_still_opens(self, case, session_factory):
        assert self._fallback(case, session_factory, "broken rib").strip()

    def test_low_value_tests_are_called_out(self, case, session_factory):
        low = [k for k, v in case["investigations"].items()
               if v.get("category") == "low_value"]
        if not low:
            return
        s = session_factory(questions=["q"] * 8, investigations=low[:1], diagnosis="GERD")
        text = " ".join(build_fallback_feedback([], evaluate_clinical(s, case), case))
        assert "added little here" in text

    def test_a_detected_pattern_adds_a_reasoning_nudge(self, case, session_factory):
        s = session_factory(questions=["q"] * 8, diagnosis="GERD")
        detected = [{"name": "anchoring", "reason": "..."}]
        text = " ".join(build_fallback_feedback(detected, evaluate_clinical(s, case), case))
        assert "reconsider your diagnosis" in text
