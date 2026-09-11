"""
Shared fixtures (BUILD_PLAN T-002).

The `_no_real_llm` fixture below is autouse: it applies to every test in the
suite whether the test asks for it or not. That is deliberate — criterion 1 is
that *no test makes a network call*, and a guarantee that depends on each test
author remembering to opt in is not a guarantee.
"""

import pytest

from nidan.domain.content.cases import get_case
from nidan.domain.session import create_session
from tests.fakes.llm import FakeLLM

# Every domain test that needs a timestamp uses this one. Fixed, so any test
# that accidentally depends on wall-clock time fails consistently rather than
# once a year at midnight.
FIXED_START = "2026-01-01T09:00:00+00:00"


# ── the network guard ────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _no_real_llm(monkeypatch):
    """
    Make a real model call impossible.

    Patches the gateway's client factory rather than `call_llm`, because that
    is the single point where a network connection is actually constructed.
    Anything that reaches it — including code a future test forgets to stub —
    fails loudly here instead of quietly spending Groq quota.
    """
    def _forbidden():
        raise AssertionError(
            "A test tried to construct a real LLM client. Tests must never call "
            "a live model — use the `fake_llm` fixture, or FakeLLM directly."
        )

    monkeypatch.setattr("nidan.infra.llm.gateway._get_client", _forbidden)
    monkeypatch.setenv("GROQ_API_KEY", "test-key-never-used")


@pytest.fixture
def fake_llm(monkeypatch):
    """
    A FakeLLM patched in at every import site.

    `call_llm` is imported by name into the modules that use it, so patching
    `gateway.call_llm` alone would not affect those already-bound references.
    Each site is patched explicitly; the list is asserted against reality by
    test_no_network.py so it cannot silently go stale.
    """
    llm = FakeLLM()
    for site in ("nidan.infra.feedback.call_llm", "nidan.api.routes.call_llm"):
        monkeypatch.setattr(site, llm)
    return llm


# ── content and session fixtures ─────────────────────────────────────

@pytest.fixture
def case():
    """case_1 — the chest pain trap. Cardiac anchor, reflux truth."""
    return get_case("case_1")


@pytest.fixture
def blank_session():
    """A session with nothing recorded yet."""
    return create_session("case_1", started_at=FIXED_START)


@pytest.fixture
def session_factory():
    """
    Builds a session in whatever state a test needs.

        session_factory(questions=["..."], investigations=["ecg"])

    Sessions are plain dicts, so a test could build one literally — but then
    every test would encode the dict's shape, and changing that shape (T-013
    will) would mean editing every test rather than this one function.
    """
    def _make(case_id="case_1", questions=None, exams=None,
              investigations=None, diagnosis=None, topics=None,
              start=FIXED_START, end=None):
        questions = list(questions or [])
        return {
            "case_id": case_id,
            "question_count": len(questions),
            "questions_asked": questions,
            "topics_covered": list(topics or []),
            "exams_performed": list(exams or []),
            "investigations_ordered": list(investigations or []),
            "early_diagnosis": None,
            "diagnosis_submitted": diagnosis,
            "start_time": start,
            "end_time": end,
        }
    return _make
