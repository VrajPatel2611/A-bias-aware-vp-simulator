"""
Telemetry: structured logging, error reporting, request correlation.

    from vpsim.infra.telemetry import setup_telemetry
    setup_telemetry()

`domain/` must never import this — logging is I/O (ADR-0009).
"""

from vpsim.infra.telemetry.context import bind, clear, current, new_request_id
from vpsim.infra.telemetry.errors import configure_sentry
from vpsim.infra.telemetry.logging import configure_logging, get_logger
from vpsim.infra.telemetry.redaction import question_fingerprint, safe_extra, scrub

__all__ = [
    "setup_telemetry", "get_logger", "bind", "clear", "current",
    "new_request_id", "scrub", "safe_extra", "question_fingerprint",
]


def setup_telemetry() -> dict[str, bool]:
    """Configure logging and error reporting from validated settings."""
    from vpsim.config import settings

    configure_logging(settings.LOG_LEVEL)
    sentry_enabled = configure_sentry(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.release_tag,
    )
    return {"logging": True, "sentry": sentry_enabled}
