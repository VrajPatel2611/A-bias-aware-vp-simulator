"""
Consultation sessions (BUILD_PLAN T-012).

Reads return row mappings rather than a domain object. T-013 makes the session
an event-sourced aggregate and will own that type; inventing one here would mean
building it twice and throwing the first away.

As in `profiles.py`, the queries carry no `WHERE user_id = ...`. `own_sessions`
does it. That is the claim `tests/db/test_repository_scope.py` exists to check.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

import sqlalchemy as sa

from nidan.infra.db.repositories.base import Repository

_COLUMNS = """
    id, user_id, anonymous_id, case_version_id, sequence_index, status,
    confidence_pre, started_at, ended_at, last_activity_at,
    diagnosis_submitted_at
"""


class SessionRepository(Repository):

    def get(self, session_id: UUID) -> Mapping[str, Any] | None:
        """
        One session by id, or None.

        None covers both "no such session" and "someone else's session", and
        that is the right shape: distinguishing them would tell a caller that
        an id exists, which is exactly what tenant isolation is for.
        """
        return self._conn.execute(
            sa.text(f"SELECT {_COLUMNS} FROM sessions WHERE id = :id"),
            {"id": session_id},
        ).mappings().first()

    def recent(self, limit: int = 20) -> Sequence[Mapping[str, Any]]:
        """The actor's sessions, newest first."""
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return self._conn.execute(sa.text(
            f"SELECT {_COLUMNS} FROM sessions "
            f"ORDER BY started_at DESC LIMIT :limit"
        ), {"limit": limit}).mappings().all()

    def active(self) -> Mapping[str, Any] | None:
        """The actor's in-progress session, if any."""
        return self._conn.execute(sa.text(
            f"SELECT {_COLUMNS} FROM sessions WHERE status = 'active' "
            f"ORDER BY started_at DESC LIMIT 1"
        )).mappings().first()

    def create(self, case_version_id: UUID,
               confidence_pre: int | None = None) -> Mapping[str, Any]:
        """
        Start a session for the actor.

        `sequence_index` is "this learner's Nth consultation" and feeds the
        progress table, so it is derived here rather than passed in: a caller
        that computes it is a caller that can get it wrong, and
        `user_sequence_unique` would then reject the row at the end of a
        request that had already charged the allowance.

        The max+1 is racy under a genuinely concurrent double-start, and that
        is deliberate for now -- the unique index turns the race into a failed
        INSERT rather than two sessions numbered 4. T-013 owns the retry, along
        with the same problem on `session_events.seq`.
        """
        user_id = self._user_id()
        row = self._conn.execute(sa.text(f"""
            INSERT INTO sessions (user_id, case_version_id, sequence_index,
                                  confidence_pre)
            VALUES (
                :user_id, :case_version_id,
                COALESCE((SELECT max(sequence_index) FROM sessions
                          WHERE user_id = :user_id), 0) + 1,
                :confidence_pre)
            RETURNING {_COLUMNS}
        """), {"user_id": user_id, "case_version_id": case_version_id,
               "confidence_pre": confidence_pre}).mappings().first()
        if row is None:                          # pragma: no cover
            raise PermissionError("session insert was refused by RLS")
        return row

    def touch(self, session_id: UUID) -> None:
        """Mark activity. Used by the idle-session sweep (DATA_MODEL §6.1)."""
        self._conn.execute(sa.text(
            "UPDATE sessions SET last_activity_at = now() WHERE id = :id"),
            {"id": session_id})

    def complete(self, session_id: UUID) -> bool:
        """
        Close a session after a diagnosis. Returns whether this call closed it.

        `WHERE ... AND diagnosis_submitted_at IS NULL` makes submission
        idempotent at the database rather than in a request handler: a
        double-clicked submit, or a retry after a timeout, updates no row the
        second time and gets False. `API_CONTRACT` requires that (FR-7.6), and
        a check-then-write in Python would not survive two concurrent requests.

        `ended_when_terminal` (migration 009) requires `ended_at` whenever the
        status is not active, so both are set together or neither is.
        """
        result = self._conn.execute(sa.text("""
            UPDATE sessions
               SET status = 'completed',
                   ended_at = now(),
                   diagnosis_submitted_at = now(),
                   last_activity_at = now()
             WHERE id = :id AND diagnosis_submitted_at IS NULL
        """), {"id": session_id})
        return result.rowcount == 1
