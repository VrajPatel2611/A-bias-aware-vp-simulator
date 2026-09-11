"""
T-001 acceptance: the restructured package still serves every original route.

This is a smoke test, not a behaviour test — it proves the wiring survived the
move. Behavioural tests for the domain layer arrive with T-002.
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


def test_pre_case_post_starts_consultation(client):
    r = client.post("/pre_case/case_1", data={
        "participant_id": "TEST01", "year_of_study": "year_3", "confidence": "3",
    })
    assert r.status_code == 200


def test_start_route_bypasses_form(client):
    assert client.get("/start/case_1").status_code == 200


def test_unknown_case_redirects(client):
    assert client.get("/pre_case/case_999").status_code in (302, 404)


def test_examine_without_session_is_rejected(client):
    r = client.post("/examine", json={"system": "vitals"})
    assert r.status_code == 400


def test_examine_returns_finding_within_a_session(client):
    client.post("/pre_case/case_1", data={
        "participant_id": "TEST02", "year_of_study": "year_3", "confidence": "3"})
    r = client.post("/examine", json={"system": "vitals"})
    assert r.status_code == 200
    assert "finding" in r.get_json()


def test_investigate_returns_result_within_a_session(client):
    client.post("/pre_case/case_1", data={
        "participant_id": "TEST03", "year_of_study": "year_3", "confidence": "3"})
    r = client.post("/investigate", json={"test": "ecg"})
    assert r.status_code == 200
    assert "result" in r.get_json()


def test_unknown_investigation_key_is_rejected(client):
    client.post("/pre_case/case_1", data={
        "participant_id": "TEST04", "year_of_study": "year_3", "confidence": "3"})
    assert client.post("/investigate", json={"test": "not_a_real_test"}).status_code == 400


def test_feedback_without_session_redirects(client):
    assert client.get("/feedback").status_code == 302


def test_save_session_wrapper_responds(client):
    assert client.post("/save_session").status_code == 200
