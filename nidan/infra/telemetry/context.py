"""
Per-request correlation identifiers (BUILD_PLAN T-007).

`contextvars`, not thread locals: they are the mechanism asyncio propagates
correctly, so this keeps working if any part of the app becomes async. Each
request sets them once; every log record emitted while handling that request
picks them up automatically.

Without correlation ids, a production log is a stream of unrelated lines and
"what happened to this learner" is unanswerable.
"""

from __future__ import annotations

import contextvars
import uuid

request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None)
session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "session_id", default=None)
user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None)


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def bind(*, request: str | None = None, session: str | None = None,
         user: str | None = None) -> None:
    """Attach identifiers to the current context. Only sets what is given."""
    if request is not None:
        request_id.set(request)
    if session is not None:
        session_id.set(session)
    if user is not None:
        user_id.set(user)


def current() -> dict[str, str]:
    """The identifiers set on this context, omitting any that are unset."""
    values = {
        "request_id": request_id.get(),
        "session_id": session_id.get(),
        "user_id": user_id.get(),
    }
    return {k: v for k, v in values.items() if v}


def clear() -> None:
    for var in (request_id, session_id, user_id):
        var.set(None)
