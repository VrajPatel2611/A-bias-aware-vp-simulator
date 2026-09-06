"""
Confirmation bias — vpsim.domain.assessment.bias.detect_confirmation_bias.

  C1  diagnosis matches an anchor keyword AND zero clues explored   score 0.90
  C2  < 25% of clues explored AND ≥ 5 questions      score = 1 - ratio

case_1 has 6 contradictory clues, all reflux evidence.
This is the detector that sat at 14% sensitivity; the tests below encode why.
"""

from vpsim.domain.assessment.bias import clue_keywords, detect_confirmation_bias

# Each question below matches EXACTLY ONE contradictory clue. That matters:
# "Do you get heartburn after meals?" looks like one question but matches two
# clues (heartburn, and the meal-relationship clue), which silently doubles the
# exploration ratio and makes a threshold test assert the wrong number.
BURNING_Q = "Would you call the pain burning?"        # clue 0
MEAL_Q = "Do you eat spicy food?"                     # clue 1
NSAID_Q = "Are you taking ibuprofen?"                 # clue 2
ANTACID_Q = "Does gaviscon help?"                     # clue 3
POSTURE_Q = "Is it worse when you recline?"           # clue 4
REGURG_Q = "Any regurgitation?"                       # clue 5
FILLER = "How old are you?"


class TestRuleC1DiagnosedTheTrapWithoutLooking:
    def test_fires_on_anchor_diagnosis_with_no_clues_explored(self, case, session_factory):
        s = session_factory(questions=[FILLER] * 4, diagnosis="Myocardial infarction")
        r = detect_confirmation_bias(s, case)
        assert r["detected"] is True
        assert r["score"] == 0.90

    def test_silent_when_the_trap_diagnosis_was_reached_after_looking(self, case, session_factory):
        """Exploring the counter-evidence and still concluding cardiac is not this bias."""
        s = session_factory(
            questions=[BURNING_Q, MEAL_Q, NSAID_Q, ANTACID_Q, POSTURE_Q, REGURG_Q],
            diagnosis="Myocardial infarction")
        assert detect_confirmation_bias(s, case)["detected"] is False

    def test_silent_when_the_diagnosis_is_not_the_anchor(self, case, session_factory):
        s = session_factory(questions=[FILLER] * 4, diagnosis="GERD")
        assert detect_confirmation_bias(s, case)["detected"] is False


class TestRuleC2ThinClueExploration:
    def test_fires_below_twentyfive_percent(self, case, session_factory):
        """1 of 6 clues = 0.167."""
        s = session_factory(questions=[BURNING_Q] + [FILLER] * 4)
        r = detect_confirmation_bias(s, case)
        assert r["detected"] is True
        assert r["score"] == round(1 - 1 / 6, 2)

    def test_silent_at_or_above_the_threshold(self, case, session_factory):
        """2 of 6 = 0.33, above 0.25."""
        s = session_factory(questions=[BURNING_Q, NSAID_Q] + [FILLER] * 3)
        assert detect_confirmation_bias(s, case)["detected"] is False

    def test_needs_at_least_five_questions(self, case, session_factory):
        """Below five questions this is premature closure, not confirmation bias."""
        s = session_factory(questions=[FILLER] * 4)
        assert detect_confirmation_bias(s, case)["detected"] is False


class TestClueMatching:
    """The mechanics that the 14%-sensitivity bug lived in."""

    def test_each_clue_counts_only_once_however_often_asked(self, case, session_factory):
        s = session_factory(questions=[BURNING_Q, BURNING_Q, BURNING_Q] + [FILLER] * 3)
        r = detect_confirmation_bias(s, case)
        assert r["score"] == round(1 - 1 / 6, 2)     # still 1 clue, not 3

    def test_any_keyword_in_a_clue_marks_it_explored(self, case, session_factory):
        """Clues are curated keyword lists; matching any one is enough."""
        clue = case["contradictory_clues"][2]        # the NSAID clue
        for kw in clue_keywords(clue)[:3]:
            s = session_factory(questions=[f"Do you take {kw}?"] + [FILLER] * 4)
            assert detect_confirmation_bias(s, case)["score"] < 1.0

    def test_exploring_everything_is_silent(self, case, session_factory):
        s = session_factory(questions=[BURNING_Q, MEAL_Q, NSAID_Q,
                                       ANTACID_Q, POSTURE_Q, REGURG_Q])
        assert detect_confirmation_bias(s, case)["detected"] is False

    def test_matching_is_case_insensitive(self, case, session_factory):
        s = session_factory(questions=["WOULD YOU CALL THE PAIN BURNING?"] + [FILLER] * 4)
        assert detect_confirmation_bias(s, case)["score"] == round(1 - 1 / 6, 2)


class TestEdgeCases:
    def test_no_diagnosis_and_no_questions_is_silent(self, case, session_factory):
        r = detect_confirmation_bias(session_factory(questions=[]), case)
        assert r["detected"] is False
        assert r["score"] == 0.0

    def test_reason_uses_bias_free_vocabulary_in_headline_terms(self, case, session_factory):
        """
        The reason names the mechanism in plain words. PRD P1 bans the
        vocabulary in *headings*; this asserts the learner-facing sentence does
        not lead with jargon like "anchoring" or "premature closure".
        """
        s = session_factory(questions=[FILLER] * 4, diagnosis="Myocardial infarction")
        reason = detect_confirmation_bias(s, case)["reason"].lower()
        assert "anchoring" not in reason
        assert "premature closure" not in reason


class TestLegacyStringClues:
    """
    Backwards compatibility. Clues used to be free-text sentences, split into
    words longer than 4 characters — which is exactly how they came to share
    vocabulary with the anchor keywords and dropped sensitivity to 14%.

    The path still exists for old content, so it is still tested.
    """

    def test_a_string_clue_is_split_into_long_words(self):
        assert clue_keywords("Pain relieved by antacid medication") == [
            "relieved", "antacid", "medication"
        ]

    def test_short_words_are_dropped(self):
        """This is the lossy step that made legacy clues unreliable."""
        assert clue_keywords("it is due to the food") == []

    def test_a_curated_list_is_used_verbatim_and_lowercased(self):
        assert clue_keywords(["Burning", "HEARTBURN", "pH"]) == ["burning", "heartburn", "ph"]

    def test_a_string_clue_still_matches_a_question(self, case, session_factory):
        legacy = dict(case)
        legacy["contradictory_clues"] = ["relieved by antacid medication"] * 6
        s = session_factory(questions=["Is it relieved by anything?"] + [FILLER] * 4)
        assert detect_confirmation_bias(s, legacy)["detected"] is False
