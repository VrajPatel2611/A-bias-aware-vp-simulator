"""
Clinical scoring — vpsim.domain.assessment.clinical.

Diagnosis classification and workup coverage. Separate from bias detection: a
learner can reason poorly and still be right, and the product reports both.

`assess_diagnosis` returns one of four verdicts — correct / partial / anchored /
other — rather than a boolean, because "wrong" and "wrong in the way this case
was designed to catch" are different findings.
"""

from vpsim.domain.assessment.clinical import (
    assess_diagnosis,
    assess_examinations,
    assess_investigations,
    evaluate_clinical,
)


class TestDiagnosisVerdicts:
    def test_accepts_a_listed_phrasing(self, case):
        assert assess_diagnosis("GERD", case)["verdict"] == "correct"

    def test_accepts_an_alternative_phrasing(self, case):
        assert assess_diagnosis("gastro-oesophageal reflux", case)["verdict"] == "correct"

    def test_is_case_insensitive(self, case):
        assert assess_diagnosis("gerd", case)["verdict"] == "correct"

    def test_the_trap_diagnosis_is_anchored_not_merely_wrong(self, case):
        """
        The distinction carries the teaching. "Other" means they missed it;
        "anchored" means they fell for the trap the case was built around.
        """
        r = assess_diagnosis("Myocardial infarction", case)
        assert r["verdict"] == "anchored"
        assert r["matched"] == "myocardial"

    def test_recognises_a_partial_answer(self, case):
        assert assess_diagnosis("indigestion", case)["verdict"] == "partial"

    def test_an_unrelated_answer_is_other(self, case):
        assert assess_diagnosis("broken rib", case)["verdict"] == "other"

    def test_empty_diagnosis_is_other(self, case):
        assert assess_diagnosis("", case)["verdict"] == "other"

    def test_none_is_handled(self, case):
        assert assess_diagnosis(None, case)["verdict"] == "other"

    def test_accepted_wins_over_anchor_in_a_mixed_answer(self, case):
        """
        "Not cardiac, likely GERD" contains both an anchor keyword and an
        accepted phrase. Accepted is checked first, so the learner who ruled
        the trap out explicitly is marked correct — not anchored.
        """
        r = assess_diagnosis("Not cardiac, likely GERD", case)
        assert r["verdict"] == "correct"

    def test_every_verdict_carries_a_label(self, case):
        for text in ("GERD", "indigestion", "myocardial infarction", "broken rib"):
            assert assess_diagnosis(text, case)["label"]


class TestExaminationCoverage:
    def test_reports_what_was_performed_by_display_name(self, case, session_factory):
        r = assess_examinations(session_factory(exams=["vitals"]), case)
        assert r["performed"] == ["Vital signs"]

    def test_splits_key_examinations_into_done_and_missed(self, case, session_factory):
        r = assess_examinations(session_factory(exams=["vitals"]), case)
        assert len(r["key_done"]) + len(r["key_missed"]) == r["total_key"]

    def test_nothing_performed_means_everything_missed(self, case, session_factory):
        r = assess_examinations(session_factory(), case)
        assert r["key_done"] == []
        assert len(r["key_missed"]) == r["total_key"]


class TestInvestigationCoverage:
    def test_all_key_investigations_ordered(self, case, session_factory):
        keys = [k for k, v in case["investigations"].items() if v.get("category") == "key"]
        r = assess_investigations(session_factory(investigations=keys), case)
        assert len(r["key_done"]) == r["total_key"]
        assert r["key_missed"] == []

    def test_low_value_orders_are_reported_separately(self, case, session_factory):
        low = [k for k, v in case["investigations"].items()
               if v.get("category") == "low_value"]
        if not low:
            return
        r = assess_investigations(session_factory(investigations=low[:1]), case)
        assert r["low_value_ordered"]

    def test_the_key_denominator_is_never_zero(self, case, session_factory):
        """
        Invariant C-7 exists so this denominator is meaningful. A zero here
        would make the scorecard percentage a division by zero.
        """
        assert assess_investigations(session_factory(), case)["total_key"] > 0


class TestEvaluateClinicalContract:
    def test_returns_a_populated_dict(self, case, session_factory):
        s = session_factory(questions=["q"], diagnosis="GERD")
        assert isinstance(evaluate_clinical(s, case), dict)

    def test_does_not_mutate_the_session(self, case, session_factory):
        import copy
        s = session_factory(questions=["q"], investigations=["ecg"], diagnosis="GERD")
        before = copy.deepcopy(s)
        evaluate_clinical(s, case)
        assert s == before, "clinical scoring mutated the session it was given"
