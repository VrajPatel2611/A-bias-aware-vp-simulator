"""
Session persistence — nidan.infra.storage.

Regression tests for a defect found in T-004: `save_session_file` referenced
`datetime` without importing it, so every save raised NameError. A bare
`except Exception` swallowed it, the route still returned 200, and the smoke
test passed. No session file was written for the whole of T-001.

The lesson these tests encode: asserting a route returns 200 does not prove the
work behind it happened.
"""

import json

import pytest

from nidan.domain.assessment.bias import detect_all_biases
from nidan.domain.assessment.clinical import evaluate_clinical
from nidan.domain.content.cases import get_case
from nidan.domain.session import create_session
from nidan.infra.storage import count_prior_sessions, save_session_file


@pytest.fixture
def in_tmp_cwd(tmp_path, monkeypatch):
    """save_session_file writes to a relative 'sessions/' directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def completed():
    case = get_case("case_1")
    session = create_session("case_1", started_at="2026-01-01T09:00:00+00:00")
    session["questions_asked"] = ["Could this be a heart problem?"]
    session["question_count"] = 1
    session["diagnosis_submitted"] = "GERD"
    return case, session


def _save(case, session, pid="P01"):
    return save_session_file(
        "sid", "case_1", case, session, {"participant_id": pid},
        detect_all_biases(session, case), evaluate_clinical(session, case),
        ["a feedback line"],
    )


class TestAFileIsActuallyWritten:
    def test_returns_the_path_it_wrote(self, in_tmp_cwd, completed):
        assert _save(*completed) is not None

    def test_the_file_exists_on_disk(self, in_tmp_cwd, completed):
        path = _save(*completed)
        assert (in_tmp_cwd / path).exists()

    def test_the_file_is_valid_json_with_the_expected_keys(self, in_tmp_cwd, completed):
        record = json.loads((in_tmp_cwd / _save(*completed)).read_text(encoding="utf-8"))
        for key in ("case_id", "participant", "biases_detected",
                    "clinical_eval", "feedback_given"):
            assert key in record

    def test_the_learners_own_questions_are_stored(self, in_tmp_cwd, completed):
        """
        Property P3 — the record must be enough to recompute the result. That
        requires the questions, since every flag is derived from them.
        """
        record = json.loads((in_tmp_cwd / _save(*completed)).read_text(encoding="utf-8"))
        assert "Could this be a heart problem?" in json.dumps(record)


class TestParticipantSequencing:
    def test_first_session_is_sequence_one(self, in_tmp_cwd, completed):
        assert "seq1" in _save(*completed)

    def test_the_sequence_increments_per_participant(self, in_tmp_cwd, completed):
        _save(*completed, pid="P01")
        assert "seq2" in _save(*completed, pid="P01")

    def test_participants_are_counted_independently(self, in_tmp_cwd, completed):
        _save(*completed, pid="P01")
        assert "seq1" in _save(*completed, pid="P02")

    def test_a_missing_participant_id_falls_back_to_anon(self, in_tmp_cwd, completed):
        case, session = completed
        path = save_session_file("sid", "case_1", case, session, {},
                                 detect_all_biases(session, case),
                                 evaluate_clinical(session, case), [])
        assert "anon" in path

    def test_counting_an_absent_directory_returns_zero(self, in_tmp_cwd):
        assert count_prior_sessions("no_such_dir", "P01") == 0

    def test_a_malformed_file_does_not_break_counting(self, in_tmp_cwd, completed):
        _save(*completed, pid="P01")
        (in_tmp_cwd / "sessions" / "broken.json").write_text("{not json", encoding="utf-8")
        assert count_prior_sessions("sessions", "P01") == 1


class TestFailureBehaviour:
    def test_a_filesystem_error_degrades_instead_of_raising(
            self, in_tmp_cwd, completed, monkeypatch):
        """A full disk must not lose the consultation the learner just finished."""
        def _refuse(*a, **k):
            raise OSError("read-only file system")
        monkeypatch.setattr("builtins.open", _refuse)
        assert _save(*completed) is None

    def test_a_programming_error_is_not_swallowed(
            self, in_tmp_cwd, completed, monkeypatch):
        """
        The regression guard. The handler catches OSError only, so a NameError
        or TypeError surfaces instead of being reported as a disk problem.
        """
        def _bug(*a, **k):
            raise NameError("name 'datetime' is not defined")
        monkeypatch.setattr("nidan.infra.storage.count_prior_sessions", _bug)
        with pytest.raises(NameError):
            _save(*completed)
