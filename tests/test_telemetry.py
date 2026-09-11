"""
Telemetry — nidan.infra.telemetry (BUILD_PLAN T-007, TECH_SPEC §10).

Criterion 2 — "raw question text never logged at INFO; no emails, no keys" — is
the one that needs proving rather than asserting. `TestNothingSensitiveReaches`
below drives a real consultation through the app while capturing stdout, then
searches the captured JSON for the learner's own words.
"""

import io
import json
import logging

import pytest

from nidan.infra.telemetry import context
from nidan.infra.telemetry.logging import JsonFormatter, configure_logging
from nidan.infra.telemetry.redaction import (
    REDACTED,
    question_fingerprint,
    safe_extra,
    scrub,
)


@pytest.fixture
def captured():
    """Capture root-logger output as parsed JSON objects."""
    stream = io.StringIO()
    root = logging.getLogger()
    old_handlers, old_level = list(root.handlers), root.level
    for h in old_handlers:
        root.removeHandler(h)

    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    yield stream

    root.removeHandler(handler)
    for h in old_handlers:
        root.addHandler(h)
    root.setLevel(old_level)
    context.clear()


def _records(stream):
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


class TestJsonFormat:
    def test_each_line_is_one_json_object(self, captured):
        logging.getLogger("t").info("hello")
        logging.getLogger("t").info("again")
        assert len(_records(captured)) == 2

    def test_carries_the_standard_fields(self, captured):
        logging.getLogger("t").info("hello")
        r = _records(captured)[0]
        assert set(r) >= {"ts", "level", "logger", "msg"}
        assert r["level"] == "INFO"
        assert r["msg"] == "hello"

    def test_timestamp_is_iso_utc(self, captured):
        logging.getLogger("t").info("hello")
        assert _records(captured)[0]["ts"].endswith("+00:00")

    def test_extra_fields_are_included(self, captured):
        logging.getLogger("t").info("request", extra={"status": 200, "path": "/"})
        r = _records(captured)[0]
        assert r["status"] == 200 and r["path"] == "/"

    def test_exceptions_are_captured(self, captured):
        try:
            raise ValueError("boom")
        except ValueError:
            logging.getLogger("t").exception("failed")
        assert "ValueError" in _records(captured)[0]["exception"]


class TestCorrelationIds:
    """Criterion 1 — request_id, session_id, user_id on every record."""

    def test_bound_ids_appear_without_being_passed(self, captured):
        context.bind(request="req-1", session="sess-1", user="user-1")
        logging.getLogger("t").info("hello")
        r = _records(captured)[0]
        assert r["request_id"] == "req-1"
        assert r["session_id"] == "sess-1"
        assert r["user_id"] == "user-1"

    def test_unset_ids_are_omitted_not_null(self, captured):
        context.clear()
        logging.getLogger("t").info("hello")
        assert "session_id" not in _records(captured)[0]

    def test_ids_are_unique(self):
        assert context.new_request_id() != context.new_request_id()


class TestRedaction:
    @pytest.mark.parametrize("secret", [
        "gsk_abcdefghijklmnop1234",           # Groq
        "sk-abcdefghijklmnop1234",            # OpenAI
        "sk_live_51HxYzAbCdEfGhIj",           # Stripe secret (T-041)
        "pk_test_51HxYzAbCdEfGhIj",           # Stripe publishable
        "AIzaSyAbcdefghijklmnop123456",       # Google (the Gemini era)
        "AKIAIOSFODNN7EXAMPLE",               # AWS
    ])
    def test_key_shapes_are_masked(self, secret):
        assert secret not in scrub(f"using {secret} now")
        assert REDACTED in scrub(f"using {secret} now")

    def test_emails_are_masked(self):
        assert "aarav@hospital.org" not in scrub("contact aarav@hospital.org")

    def test_bearer_tokens_and_jwts_are_masked(self):
        assert REDACTED in scrub("Authorization: Bearer abcdefghijklmnop")
        assert REDACTED in scrub("eyJhbGciOi.eyJzdWIiOi.SflKxwRJSM")

    def test_private_key_headers_are_masked(self):
        assert REDACTED in scrub("-----BEGIN RSA PRIVATE KEY-----")

    def test_ordinary_text_is_untouched(self):
        text = "assessment completed for case_1 in 431ms"
        assert scrub(text) == text

    def test_short_lookalikes_are_not_over_redacted(self):
        """
        The key pattern is deliberately broad, so this guards the other side:
        ordinary words that merely start like a key must survive.
        """
        text = "the sk-ip logic and pk value are fine"
        assert scrub(text) == text

    def test_sensitive_field_names_are_replaced_wholesale(self):
        out = safe_extra({"question": "Do you get chest pain?", "case_id": "case_1"})
        assert out["question"] == REDACTED
        assert out["case_id"] == "case_1"

    def test_field_names_are_matched_case_insensitively(self):
        assert safe_extra({"GROQ_API_KEY": "gsk_x"})["GROQ_API_KEY"] == REDACTED

    def test_non_strings_pass_through(self):
        out = safe_extra({"count": 4, "ok": True, "ratio": 0.75})
        assert out == {"count": 4, "ok": True, "ratio": 0.75}

    def test_a_fingerprint_describes_a_question_without_quoting_it(self):
        fp = question_fingerprint("Do you get chest pain after meals?")
        assert fp == {"question_chars": 34, "question_words": 7}
        assert "chest" not in json.dumps(fp)


class TestSecretsCannotReachTheLog:
    def test_a_key_in_the_message_is_masked(self, captured):
        logging.getLogger("t").info("calling with gsk_abcdefghij1234567890")
        assert "gsk_abcdefghij1234567890" not in captured.getvalue()

    def test_a_key_in_an_extra_field_is_masked(self, captured):
        logging.getLogger("t").info("call", extra={"note": "key=gsk_abcdefghij1234567890"})
        assert "gsk_abcdefghij1234567890" not in captured.getvalue()

    def test_a_key_inside_a_traceback_is_masked(self, captured):
        try:
            raise RuntimeError("auth failed for gsk_abcdefghij1234567890")
        except RuntimeError:
            logging.getLogger("t").exception("boom")
        assert "gsk_abcdefghij1234567890" not in captured.getvalue()


class TestNothingSensitiveReaches:
    """
    Criterion 2, end to end.

    A real consultation is driven through the app with stdout captured, then the
    learner's own words are searched for in the output. This is the test that
    would catch someone adding `logger.info(f"question: {q}")` while debugging.
    """

    def test_a_learners_question_never_appears_in_the_log(self, monkeypatch, capsys):
        from nidan.app import create_app

        monkeypatch.setenv("GROQ_API_KEY", "test-key-never-used")
        app = create_app({"TESTING": True})
        client = app.test_client()

        secret_question = "ZZQUESTIONMARKERZZ does the pain radiate to your jaw"

        client.post("/pre_case/case_1", data={
            "participant_id": "P01", "year_of_study": "year_3", "confidence": "3"})

        # The question must actually be SENT, or this test proves nothing. An
        # earlier draft built the string and never posted it — it passed, and
        # would have kept passing with logging wide open.
        client.post("/chat", json={"message": secret_question})
        client.post("/examine", json={"system": "vitals"})
        client.post("/investigate", json={"test": "ecg"})
        client.post("/conclude", json={"diagnosis": "ZZDIAGNOSISMARKERZZ reflux"})

        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "ZZQUESTIONMARKERZZ" not in output, (
            "a learner's question reached the log — TECH_SPEC §10 forbids it"
        )
        assert "ZZDIAGNOSISMARKERZZ" not in output, (
            "a learner's diagnosis reached the log"
        )

    def test_health_probes_are_not_logged(self, monkeypatch, capsys):
        """They fire every 30 seconds and would drown the signal."""
        from nidan.app import create_app

        monkeypatch.setenv("GROQ_API_KEY", "test-key-never-used")
        client = create_app({"TESTING": True}).test_client()
        capsys.readouterr()
        client.get("/healthz")
        assert '"path": "/healthz"' not in capsys.readouterr().out


class TestHealthEndpoints:
    @pytest.fixture
    def client(self, monkeypatch):
        from nidan.app import create_app
        monkeypatch.setenv("GROQ_API_KEY", "test-key-never-used")
        return create_app({"TESTING": True}).test_client()

    def test_healthz_is_ok(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.get_json()["status"] == "ok"

    def test_healthz_reports_the_release(self, client):
        assert "release" in client.get("/healthz").get_json()

    def test_readyz_reports_individual_checks(self, client):
        body = client.get("/readyz").get_json()
        assert body["status"] == "ready"
        assert body["checks"]["cases_loaded"] is True
        assert body["checks"]["config"] is True

    def test_every_response_carries_a_request_id(self, client):
        assert client.get("/healthz").headers.get("X-Request-ID")

    def test_an_inbound_request_id_is_honoured(self, client):
        r = client.get("/", headers={"X-Request-ID": "trace-me-123"})
        assert r.headers["X-Request-ID"] == "trace-me-123"


class TestSentryConfiguration:
    def test_no_dsn_means_disabled_not_broken(self):
        from nidan.infra.telemetry.errors import configure_sentry
        assert configure_sentry("", "test", "v1") is False

    def test_before_send_scrubs_the_exception_value(self):
        from nidan.infra.telemetry.errors import _before_send
        event = {"exception": {"values": [
            {"value": "auth failed for gsk_abcdefghij1234567890"}]}}
        out = _before_send(event, None)
        assert "gsk_abcdefghij1234567890" not in out["exception"]["values"][0]["value"]

    def test_before_send_drops_the_query_string(self):
        from nidan.infra.telemetry.errors import _before_send
        out = _before_send({"request": {"query_string": "email=a@b.com"}}, None)
        assert "query_string" not in out["request"]

    def test_before_send_never_raises(self):
        """A reporting failure must not become the error being reported."""
        from nidan.infra.telemetry.errors import _before_send
        assert _before_send({"exception": "not-a-dict"}, None) is not None


def test_configure_logging_is_idempotent():
    """An app factory called twice in a test run must not double every line."""
    configure_logging("INFO")
    configure_logging("INFO")
    assert len(logging.getLogger().handlers) == 1
