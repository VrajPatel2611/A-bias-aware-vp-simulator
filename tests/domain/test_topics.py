"""
Topic extraction — nidan.domain.assessment.topics.

Every coverage figure and the premature-closure detector depend on this. If it
under-matches, learners are told they missed areas they actually explored.
"""

from nidan.domain.assessment.topics import TOPIC_KEYWORDS, extract_topics


class TestExtraction:
    def test_finds_a_topic_from_a_natural_question(self):
        assert "family_history" in extract_topics("Any family history of heart disease?")

    def test_one_question_can_cover_several_topics(self):
        found = extract_topics("Is the burning pain worse after meals?")
        assert len(found) >= 2

    def test_returns_empty_for_an_unrelated_question(self):
        assert extract_topics("What is your name?") == []

    def test_is_case_insensitive(self):
        assert extract_topics("ANY FAMILY HISTORY?") == extract_topics("any family history?")

    def test_returns_no_duplicates(self):
        found = extract_topics("family history, and any family history at all?")
        assert len(found) == len(set(found))


class TestEdgeCases:
    def test_empty_string(self):
        assert extract_topics("") == []

    def test_whitespace_only(self):
        assert extract_topics("   \n\t ") == []

    def test_punctuation_does_not_prevent_a_match(self):
        assert extract_topics("family history???") == extract_topics("family history")

    def test_very_long_input_does_not_crash(self):
        assert isinstance(extract_topics("pain " * 5000), list)


class TestLexiconIntegrity:
    def test_every_returned_topic_is_a_known_key(self):
        found = extract_topics("burning pain after meals radiating to the arm, "
                               "any medication, family history, how long")
        assert set(found) <= set(TOPIC_KEYWORDS)

    def test_no_topic_has_an_empty_keyword_list(self):
        empty = [t for t, kws in TOPIC_KEYWORDS.items() if not kws]
        assert not empty, f"topics that can never match: {empty}"

    def test_no_keyword_is_blank(self):
        blank = [t for t, kws in TOPIC_KEYWORDS.items()
                 if any(not k or not k.strip() for k in kws)]
        assert not blank, f"blank keyword matches everything: {blank}"
