"""
Premature closure — vpsim.domain.assessment.bias.detect_premature_closure.

  P1  question_count < minimum_questions   score = max(1 - qc/min, 0.1)
  P2  required-topic coverage < 0.60       score = 1 - coverage

case_1: minimum_questions = 7, 8 required topics.
"""

from vpsim.domain.assessment.bias import detect_premature_closure

ALL_TOPICS = ["pain_character", "meal_relationship", "radiation",
              "associated_symptoms", "medications", "family_history",
              "duration_pattern", "relieving_factors"]


class TestRuleP1TooFewQuestions:
    def test_fires_below_the_minimum(self, case, session_factory):
        s = session_factory(questions=["q"] * 3, topics=ALL_TOPICS)
        r = detect_premature_closure(s, case)
        assert r["detected"] is True
        assert r["score"] == round(1 - 3 / 7, 2)      # 0.57

    def test_silent_at_exactly_the_minimum(self, case, session_factory):
        """The rule is `<`, not `<=`. Seven questions meets the bar."""
        s = session_factory(questions=["q"] * 7, topics=ALL_TOPICS)
        assert detect_premature_closure(s, case)["detected"] is False

    def test_score_never_falls_below_the_floor(self, case, session_factory):
        """
        Six of seven questions gives 1 - 0.857 = 0.14, but the floor is 0.1 —
        so a detection can never carry a score of zero, which would contradict
        the invariant `detected ⇒ score > 0`.
        """
        s = session_factory(questions=["q"] * 6, topics=ALL_TOPICS)
        r = detect_premature_closure(s, case)
        assert r["detected"] is True
        assert r["score"] >= 0.1

    def test_zero_questions_scores_at_the_top(self, case, session_factory):
        s = session_factory(questions=[], topics=ALL_TOPICS)
        assert detect_premature_closure(s, case)["score"] == 1.0


class TestRuleP2ThinTopicCoverage:
    def test_fires_below_sixty_percent_coverage(self, case, session_factory):
        """4 of 8 topics = 0.50 coverage."""
        s = session_factory(questions=["q"] * 10, topics=ALL_TOPICS[:4])
        r = detect_premature_closure(s, case)
        assert r["detected"] is True
        assert r["score"] == 0.5

    def test_silent_above_the_threshold(self, case, session_factory):
        """5 of 8 = 0.625, above 0.60."""
        s = session_factory(questions=["q"] * 10, topics=ALL_TOPICS[:5])
        assert detect_premature_closure(s, case)["detected"] is False

    def test_full_coverage_and_enough_questions_is_silent(self, case, session_factory):
        s = session_factory(questions=["q"] * 10, topics=ALL_TOPICS)
        assert detect_premature_closure(s, case)["detected"] is False


class TestEvidenceNamesWhatWasMissed:
    def test_evidence_lists_the_missed_topics_readably(self, case, session_factory):
        s = session_factory(questions=["q"] * 10, topics=ALL_TOPICS[:4])
        ev = detect_premature_closure(s, case)["evidence"]
        assert "family history" in ev          # underscores replaced for display
        assert "family_history" not in ev

    def test_evidence_is_empty_when_everything_was_covered(self, case, session_factory):
        s = session_factory(questions=["q"] * 10, topics=ALL_TOPICS)
        assert detect_premature_closure(s, case)["evidence"] == []


class TestReasonWording:
    def test_mentions_both_rules_when_both_fire(self, case, session_factory):
        s = session_factory(questions=["q"] * 2, topics=ALL_TOPICS[:2])
        reason = detect_premature_closure(s, case)["reason"]
        assert "only 2 questions" in reason
        assert "key history areas" in reason

    def test_uses_bias_free_vocabulary(self, case, session_factory):
        """
        PRD P1 — user-facing text must never name the bias. This detector's
        reason is shown to the learner.
        """
        s = session_factory(questions=["q"] * 2, topics=[])
        reason = detect_premature_closure(s, case)["reason"].lower()
        for banned in ("bias", "anchoring", "premature closure", "confirmation"):
            assert banned not in reason
