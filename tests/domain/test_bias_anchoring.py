"""
Anchoring detector — vpsim.domain.assessment.bias.detect_anchoring.

Two OR'd rules (TECH_SPEC §4.3):
  A1  ≥ 4 questions AND anchor concentration > 0.60   score = concentration
  A2  ≥ 3 anchor questions AND zero alternatives      score = 0.85

Tests are written against the rules rather than against remembered outputs, so
a threshold change fails the test that encodes that threshold and no others.
"""


from vpsim.domain.assessment.bias import detect_anchoring

CARDIAC = "Could this be a heart problem?"
CARDIAC_2 = "Any history of angina?"
CARDIAC_3 = "Should we check troponin?"
CARDIAC_4 = "Does it feel like cardiac pain?"
REFLUX = "Do you get heartburn after meals?"
NEUTRAL = "How old are you?"


class TestRuleA1ConcentrationThreshold:
    """A1 fires above 60% anchor concentration, with at least four questions."""

    def test_fires_above_threshold(self, case, session_factory):
        """
        3 of 4 anchor questions = 0.75 concentration.

        The reflux question is what isolates A1: without it A2 would also fire
        (3 anchors, no alternatives) and `score` would be max(0.75, 0.85).
        """
        s = session_factory(questions=[CARDIAC, CARDIAC_2, CARDIAC_3, REFLUX])
        r = detect_anchoring(s, case)
        assert r["detected"] is True
        assert r["score"] == 0.75          # 3/4, A1 only

    def test_silent_at_exactly_sixty_percent(self, case, session_factory):
        """The rule is `> 0.60`, not `>=`. 3 of 5 is 0.60 and must not fire."""
        s = session_factory(questions=[CARDIAC, CARDIAC_2, CARDIAC_3,
                                       REFLUX, NEUTRAL])
        r = detect_anchoring(s, case)
        assert r["detected"] is False

    def test_needs_at_least_four_questions(self, case, session_factory):
        """Three of three is 100% concentration but too small a sample for A1."""
        s = session_factory(questions=[CARDIAC, CARDIAC_2, REFLUX])
        assert detect_anchoring(s, case)["detected"] is False


class TestRuleA2NoAlternativesExplored:
    """A2 fires on three anchor questions with no alternative exploration."""

    def test_fires_on_three_anchor_questions_and_no_alternatives(self, case, session_factory):
        s = session_factory(questions=[CARDIAC, CARDIAC_2, CARDIAC_3])
        r = detect_anchoring(s, case)
        assert r["detected"] is True
        assert r["score"] == 0.85

    def test_silent_when_an_alternative_was_explored(self, case, session_factory):
        """One reflux question is enough to show the learner considered another cause."""
        s = session_factory(questions=[CARDIAC, CARDIAC_2, CARDIAC_3, REFLUX,
                                       NEUTRAL, NEUTRAL, NEUTRAL])
        assert detect_anchoring(s, case)["detected"] is False


class TestScoreIsTheMaximumOfBothRules:
    def test_takes_the_higher_of_the_two(self, case, session_factory):
        """4 anchor / 4 total: A1 gives 1.0, A2 gives 0.85. Expect 1.0."""
        s = session_factory(questions=[CARDIAC, CARDIAC_2, CARDIAC_3, CARDIAC_4])
        assert detect_anchoring(s, case)["score"] == 1.0


class TestEvidenceAndTraceability:
    """Property P2 — a flag cites the learner's own questions."""

    def test_evidence_quotes_actual_questions(self, case, session_factory):
        s = session_factory(questions=[CARDIAC, CARDIAC_2, CARDIAC_3, NEUTRAL])
        r = detect_anchoring(s, case)
        assert r["evidence"]
        for quoted in r["evidence"]:
            assert quoted in s["questions_asked"]

    def test_evidence_is_capped_at_three(self, case, session_factory):
        s = session_factory(questions=[CARDIAC, CARDIAC_2, CARDIAC_3,
                                       CARDIAC_4, CARDIAC, CARDIAC_2])
        assert len(detect_anchoring(s, case)["evidence"]) <= 3

    def test_reflux_questions_are_never_cited_as_cardiac_fixation(self, case, session_factory):
        """
        Regression guard for the C-4 bug found in T-003: 'heart' matched
        'heartburn', so a learner correctly chasing reflux was flagged as
        anchored on cardiac disease and shown their own good questions as proof.
        """
        s = session_factory(questions=[REFLUX,
                                       "Is the heartburn worse lying down?",
                                       "Does the heartburn bring a sour taste?",
                                       NEUTRAL])
        r = detect_anchoring(s, case)
        assert r["detected"] is False, (
            "reflux questions were counted as cardiac anchoring — C-4 has regressed"
        )
        assert r["evidence"] == []


class TestEdgeCases:
    def test_empty_session_does_not_crash(self, case, session_factory):
        r = detect_anchoring(session_factory(questions=[]), case)
        assert r["detected"] is False
        assert r["score"] == 0.0

    def test_matching_is_case_insensitive(self, case, session_factory):
        s = session_factory(questions=["COULD THIS BE A HEART PROBLEM?",
                                       "ANY HISTORY OF ANGINA?",
                                       "SHOULD WE CHECK TROPONIN?"])
        assert detect_anchoring(s, case)["detected"] is True

    def test_a_question_with_two_anchor_words_counts_once(self, case, session_factory):
        """Otherwise concentration could exceed 1.0."""
        s = session_factory(questions=["Is this cardiac angina from a coronary artery?",
                                       NEUTRAL, NEUTRAL, NEUTRAL])
        assert detect_anchoring(s, case)["score"] <= 1.0

    def test_reason_is_present_whether_or_not_detected(self, case, session_factory):
        for qs in ([], [CARDIAC, CARDIAC_2, CARDIAC_3]):
            assert detect_anchoring(session_factory(questions=qs), case)["reason"]
