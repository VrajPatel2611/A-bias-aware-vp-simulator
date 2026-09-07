"""
Typed configuration — vpsim.config (BUILD_PLAN T-006).

Criterion 1 is "fails fast on boot with a clear message". These tests check
both halves: that invalid configuration is rejected, and that the message
names what is wrong. A validator that rejects with an unreadable error has
moved the debugging cost rather than removed it.

`Settings` is constructed directly here rather than using the module-level
`settings` singleton, which is loaded once at import by design.
"""

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from vpsim.config import Settings, load_settings

REPO = Path(__file__).resolve().parent.parent


def _settings(**overrides) -> Settings:
    """Build settings from explicit values, ignoring any real .env."""
    defaults = {"GROQ_API_KEY": "", "FLASK_SECRET_KEY": "", "DATABASE_URL": ""}
    return Settings(_env_file=None, **{**defaults, **overrides})


class TestDefaults:
    def test_starts_with_no_configuration_at_all(self):
        """
        An empty environment must work. A contributor who clones the repo and
        runs the tests has no .env, and that has to be a supported state.
        """
        s = _settings()
        assert s.GROQ_MODEL == "llama-3.3-70b-versatile"
        assert s.PORT == 8000
        assert s.DEBUG is False

    def test_llm_configured_reports_whether_a_patient_can_reply(self):
        assert _settings().llm_configured is False
        assert _settings(GROQ_API_KEY="gsk_realish_value").llm_configured is True

    def test_whitespace_only_key_does_not_count_as_configured(self):
        assert _settings(GROQ_API_KEY="   ").llm_configured is False


class TestTypeCoercion:
    def test_port_is_read_as_an_integer(self):
        assert _settings(PORT="9000").PORT == 9000

    @pytest.mark.parametrize("raw,expected",
                             [("true", True), ("false", False),
                              ("1", True), ("0", False)])
    def test_debug_is_read_as_a_boolean(self, raw, expected):
        """
        The bug this prevents: `os.getenv("DEBUG")` returns the STRING "false",
        which is truthy. Debug mode would be on in production.
        """
        assert _settings(DEBUG=raw).DEBUG is expected

    def test_a_non_numeric_port_is_rejected(self):
        with pytest.raises(ValidationError):
            _settings(PORT="eight thousand")

    def test_an_out_of_range_port_is_rejected(self):
        with pytest.raises(ValidationError):
            _settings(PORT=70000)


class TestPlaceholderRejection:
    @pytest.mark.parametrize("placeholder", [
        "your-groq-api-key-here", "changeme", "replace-me", "TODO", "<your-key>",
    ])
    def test_an_unfilled_placeholder_key_is_rejected(self, placeholder):
        """
        Copying .env.example and forgetting to paste a key otherwise surfaces as
        a 401 from Groq partway through a consultation.
        """
        with pytest.raises(ValidationError, match="placeholder"):
            _settings(GROQ_API_KEY=placeholder)

    def test_a_real_looking_key_is_accepted(self):
        assert _settings(GROQ_API_KEY="gsk_abc123def456").GROQ_API_KEY

    def test_the_compose_development_secret_is_rejected(self):
        """That value is in docker-compose.yml and must never ship."""
        with pytest.raises(ValidationError, match="development default"):
            _settings(FLASK_SECRET_KEY="local-development-only-not-a-secret")

    def test_a_generated_secret_is_accepted(self):
        import secrets
        assert _settings(FLASK_SECRET_KEY=secrets.token_hex(32)).FLASK_SECRET_KEY


class TestFailureMessages:
    def test_the_message_names_the_offending_variable(self):
        with pytest.raises(ValidationError) as e:
            _settings(GROQ_API_KEY="changeme")
        assert "GROQ_API_KEY" in str(e.value)

    def test_the_secret_key_message_says_how_to_generate_one(self):
        with pytest.raises(ValidationError) as e:
            _settings(FLASK_SECRET_KEY="local-development-only-not-a-secret")
        assert "secrets.token_hex" in str(e.value)

    def test_load_settings_exits_rather_than_raising(self, monkeypatch):
        """
        Criterion 1: "fails fast on boot with a clear message". In a container a
        pydantic traceback buries the one useful line, so load_settings prints
        the errors and exits with EX_CONFIG (78).
        """
        monkeypatch.setenv("GROQ_API_KEY", "changeme")
        monkeypatch.chdir(REPO.parent)      # away from any real .env
        with pytest.raises(SystemExit) as e:
            load_settings()
        assert e.value.code == 78


class TestEnvExampleStaysHonest:
    """Criterion 3 — .env.example documents every variable."""

    def test_every_declared_field_appears_in_env_example(self):
        """
        Fails when someone adds a Settings field and forgets the documentation.
        Undocumented configuration is configuration nobody sets correctly.
        """
        text = (REPO / ".env.example").read_text()
        documented = set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", text, re.M))
        missing = sorted(set(Settings.model_fields) - documented)
        assert not missing, f".env.example does not document: {missing}"

    def test_env_example_contains_no_real_looking_secret(self):
        """
        It is committed, so anything key-shaped in it is a leak.
        `gitleaks` covers this in CI; this fails locally, before the push.
        """
        text = (REPO / ".env.example").read_text()
        found = re.findall(r"gsk_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,}|sk-[A-Za-z0-9]{20,}",
                           text)
        assert not found, f".env.example contains a real-looking secret: {found}"

    def test_the_real_env_file_is_git_ignored(self):
        ignored = (REPO / ".gitignore").read_text().splitlines()
        assert ".env" in [line.strip() for line in ignored]
