"""
Who is asking (BUILD_PLAN T-012, criterion 1).

Every database transaction in Nidan is opened on behalf of exactly one of three
actors, and the actor decides two things before a single statement runs: which
Postgres role the transaction assumes, and whether `auth.uid()` returns
anything. Get those wrong and Row-Level Security is either silently off or
denying a user their own rows.

The types are deliberately separate classes rather than one class with an
optional `user_id`. An optional field invites `if actor.user_id:` at the call
site and a forgotten `else` branch; three types make the anonymous path
impossible to reach by accident, because it does not type-check.

This module is pure data -- no SQLAlchemy, no connection. `repositories/base.py`
turns an actor into a configured transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import UUID

# The only role names that may ever reach a SET ROLE statement. SET ROLE takes
# no bind parameter, so the name is interpolated -- this frozenset is what keeps
# that from being an injection point. Nothing outside this module may add to it.
APP_ROLE: Final = "nidan_app"
SERVICE_ROLE: Final = "nidan_service"
ALLOWED_ROLES: Final = frozenset({APP_ROLE, SERVICE_ROLE})


@dataclass(frozen=True)
class AuthenticatedUser:
    """
    A signed-in learner. The ordinary case.

    Runs as `nidan_app`, with `request.jwt.claim.sub` set so `auth.uid()`
    matches this id and the policies from migration 016 apply. A query that
    forgets its `WHERE user_id = ...` returns nothing rather than someone
    else's consultation.
    """

    user_id: UUID

    db_role: Final = APP_ROLE

    def __post_init__(self) -> None:
        # A string here would be accepted by psycopg and compared as text
        # against a uuid column, which errors at the database rather than at
        # the boundary where the mistake was made.
        if not isinstance(self.user_id, UUID):
            raise TypeError(
                f"user_id must be a UUID, not {type(self.user_id).__name__}")


@dataclass(frozen=True)
class AnonymousVisitor:
    """
    A trial session with no account (PRD FR-2).

    There is no `auth.uid()` to match, so `own_sessions` evaluates NULL and
    denies the visitor their own session. `DATA_MODEL` §10.1 accepts that and
    requires the compensating control: a service-role connection with an
    explicit `anonymous_id` filter, on a path that is short, isolated and
    separately tested.

    That path is `repositories/anonymous.py` and nothing else. This actor
    cannot open a general repository scope -- `repo_scope` rejects it -- because
    the whole safety argument rests on the filter being unmissable, and it is
    only unmissable while the code that must not forget it is four methods long.
    """

    anonymous_id: str

    db_role: Final = SERVICE_ROLE

    def __post_init__(self) -> None:
        if not self.anonymous_id or not self.anonymous_id.strip():
            # Empty would filter `anonymous_id = ''`, which matches no row
            # today and would match every badly-inserted row tomorrow.
            raise ValueError("anonymous_id must be a non-empty string")


@dataclass(frozen=True)
class ServiceActor:
    """
    Something with no user at all: migrations, scheduled jobs, the case editor.

    Runs as `nidan_service`, which bypasses RLS entirely. That is the whole
    safety net switched off, so the type asks for a reason and stores it -- not
    for the database, which never reads it, but so that every bypass in the
    codebase is greppable and says out loud what it is for. A constructor that
    takes no argument gets used casually; one that demands a sentence does not.
    """

    reason: str

    db_role: Final = SERVICE_ROLE

    def __post_init__(self) -> None:
        if len(self.reason.strip()) < 8:
            raise ValueError(
                "ServiceActor(reason=...) needs a real explanation of why this "
                "work cannot run as the user -- it is turning RLS off")


Actor = AuthenticatedUser | AnonymousVisitor | ServiceActor
