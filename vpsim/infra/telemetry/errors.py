"""
Error reporting (BUILD_PLAN T-007, TECH_SPEC §10).

Sentry, configured so that it never becomes a second copy of the data the rest
of the system protects.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def configure_sentry(dsn: str, environment: str, release: str) -> bool:
    """
    Initialise Sentry. Returns whether it was enabled.

    No DSN means no reporting — that is the normal state locally and in tests,
    and it must not be an error.
    """
    if not dsn:
        return False

    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        # Releases tagged so a spike can be attributed to a deploy.
        release=release,
        # THE important setting. With PII on, Sentry attaches request bodies,
        # headers and cookies — which for this app means the learner's questions
        # and their session cookie (SECURITY_SPEC §2, assets A2 and A3).
        send_default_pii=False,
        # Performance sampling off by default; cost, not privacy.
        traces_sample_rate=0.0,
        before_send=_before_send,
    )
    return True


def _before_send(event, hint):
    """
    Last-chance scrub on the way out.

    `send_default_pii=False` already excludes bodies and headers. This covers
    what it does not: a key interpolated into an exception message, or a query
    string on the URL.
    """
    from vpsim.infra.telemetry.redaction import scrub

    try:
        for exception in event.get("exception", {}).get("values", []):
            if isinstance(exception.get("value"), str):
                exception["value"] = scrub(exception["value"])

        if isinstance(event.get("message"), str):
            event["message"] = scrub(event["message"])

        request = event.get("request", {})
        if isinstance(request.get("url"), str):
            request["url"] = scrub(request["url"])
        # Never send a query string: SECURITY_SPEC forbids personal data in URLs,
        # so anything here is already a mistake — do not compound it.
        request.pop("query_string", None)
    except Exception:          # noqa: BLE001 - reporting must never raise
        pass

    return event
