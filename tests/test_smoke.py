"""
T-001 acceptance: the restructured package still serves every original route.

This is a smoke test, not a behaviour test — it proves the wiring survived the
move. Behavioural tests for the domain layer arrive with T-002.

**What is left here needs no database.** T-013 moved session state into an
append-only event log, so the consultation routes now replay that log on every
request and cannot be exercised without PostgreSQL. Those tests live in
`tests/db/test_routes.py`. Keeping them here behind a container would have cost
this file the one property that makes it worth running on every change — it
finishes in under a second, with nothing installed.

What remains is exactly the set of routes that touch no session: the case list,
the pre-case form, and the three refusals that happen before any state is read.
"""

import pytest

from nidan.app import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-used")
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret")
    app = create_app({"TESTING": True})
    return app.test_client()


def test_index_lists_cases(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"VP" in r.data


@pytest.mark.parametrize("case_id", ["case_1", "case_2", "case_3", "case_4", "case_5"])
def test_pre_case_renders_for_every_case(client, case_id):
    r = client.get(f"/pre_case/{case_id}")
    assert r.status_code == 200
    assert b'name="participant_id"' in r.data


def test_unknown_case_redirects(client):
    assert client.get("/pre_case/case_999").status_code in (302, 404)


def test_investigate_without_session_is_rejected(client):
    """Refused before any state is read, so no database is involved."""
    assert client.post("/investigate", json={"test": "ecg"}).status_code == 400


def test_examine_without_session_is_rejected(client):
    r = client.post("/examine", json={"system": "vitals"})
    assert r.status_code == 400


def test_feedback_without_session_redirects(client):
    assert client.get("/feedback").status_code == 302


def test_save_session_wrapper_responds(client):
    assert client.post("/save_session").status_code == 200
