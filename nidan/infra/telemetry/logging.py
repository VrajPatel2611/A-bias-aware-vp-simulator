"""
Structured JSON logging (BUILD_PLAN T-007, TECH_SPEC §10).

One JSON object per line, to stdout. Not a file: the container is the unit of
deployment, and a process that writes its own log files has to solve rotation,
permissions and disk space — all of which the platform already solves for
stdout.

Every record carries the correlation ids bound for the current request, so a
single learner's path through the system can be reconstructed from a grep.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import sys
from typing import Any

from nidan.infra.telemetry import context
from nidan.infra.telemetry.redaction import safe_extra, scrub

# Attributes LogRecord always carries. Anything else was passed as `extra` and
# belongs in the output.
_STANDARD = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None)))| {
    "message", "asctime", "taskName",
}


class JsonFormatter(logging.Formatter):
    """Render a LogRecord as one JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": _dt.datetime.fromtimestamp(
                record.created, tz=_dt.UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": scrub(record.getMessage()),
        }

        payload.update(context.current())

        extras = {k: v for k, v in vars(record).items() if k not in _STANDARD}
        if extras:
            payload.update(safe_extra(extras))

        if record.exc_info:
            # Scrubbed: a traceback can contain argument values, and an argument
            # can be an API key.
            payload["exception"] = scrub(self.formatException(record.exc_info))

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """
    Install the JSON handler on the root logger.

    Idempotent: existing handlers are removed first, so calling this twice (an
    app factory in a test, say) does not produce doubled output.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Werkzeug's per-request line duplicates our own request log and is not
    # JSON. Warnings and above still come through.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.LoggerAdapter | logging.Logger:
    return logging.getLogger(name)
