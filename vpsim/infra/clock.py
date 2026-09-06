"""
The system clock.

Reading the current time is I/O: it makes a function's output depend on
something outside its arguments. So it lives in infra/, and domain/ receives
timestamps rather than fetching them (BUILD_PLAN T-002).

That is what lets the assessment engine be replayed over stored events and
produce byte-identical results (ADR-0003, PR-3) — a function that calls the
clock cannot be replayed, only re-run.
"""

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """
    Current UTC time as an ISO 8601 string.

    `datetime.now(timezone.utc)` rather than the deprecated `utcnow()`, which
    returns a naive datetime and is removed in Python 3.12+.
    """
    return datetime.now(UTC).isoformat()
