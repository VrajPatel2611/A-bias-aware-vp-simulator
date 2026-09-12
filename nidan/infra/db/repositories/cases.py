"""
Clinical content (BUILD_PLAN T-012).

Read-only, and read-only twice over: there is no write method here, and
migration 020 grants the application role SELECT and nothing else on `cases` and
`case_versions`. Content changes through the case editor's service connection
after a clinician's review (T-021, T-023) -- never through a learner's request,
whatever a bug in a request handler asks for.

**Every query filters `status = 'published'` explicitly, and the
`read_published_cases` policy filters it again.** The duplication is deliberate:
the policy is the stronger guarantee but it is not always in force -- a
`ServiceActor` runs as `nidan_service`, which bypasses RLS, and the
anonymous-trial path reuses this repository through exactly such a connection.
Relying on the policy alone would mean unreviewed draft cases became visible to
trial visitors, which is the one audience with no account and no way to report
it. The policy still earns its place: it is what catches a query written later
that forgets the filter.

The five cases seeded by migration 019 are drafts on purpose (DATA_MODEL §9.2),
so these methods correctly return nothing until a clinician approves them -- the
tests publish a fixture case rather than reaching for the seeded five.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

import sqlalchemy as sa

from nidan.infra.db.repositories.base import Repository

_SUMMARY = """
    cv.id, cv.case_id, cv.version, cv.title, cv.anchor_topic,
    cv.minimum_questions, cv.required_topic_count, cv.key_investigation_count,
    cv.content_hash, cv.published_at, c.slug, c.specialty
"""


class CaseRepository(Repository):

    def published(self) -> Sequence[Mapping[str, Any]]:
        """Every published case version, without the content payload."""
        return self._conn.execute(sa.text(f"""
            SELECT {_SUMMARY}
            FROM case_versions cv JOIN cases c ON c.id = cv.case_id
            WHERE cv.status = 'published' AND cv.retired_at IS NULL
            ORDER BY c.slug
        """)).mappings().all()

    def by_slug(self, slug: str) -> Mapping[str, Any] | None:
        """
        The current published version of a case.

        Highest version rather than the only one: a case may be republished,
        and both versions stay published so that sessions already referencing
        the old one keep resolving (DATA_MODEL §5.2).
        """
        return self._conn.execute(sa.text(f"""
            SELECT {_SUMMARY}
            FROM case_versions cv JOIN cases c ON c.id = cv.case_id
            WHERE c.slug = :slug AND cv.status = 'published'
              AND cv.retired_at IS NULL
            ORDER BY cv.version DESC LIMIT 1
        """), {"slug": slug}).mappings().first()

    def content(self, case_version_id: UUID) -> Mapping[str, Any] | None:
        """
        The full case payload (DATA_MODEL §8.1).

        Separate from the summary because it is large and most callers -- case
        lists, progress screens, a session's header -- do not want it.
        """
        return self._conn.execute(sa.text(
            "SELECT id, case_id, version, title, content "
            "FROM case_versions WHERE id = :id AND status = 'published'"),
            {"id": case_version_id},
        ).mappings().first()

    def prototype_version_id(self, slug: str) -> UUID | None:
        """
        Resolve a case version by slug **regardless of publication status**.

        Transitional, and deliberately awkward to reach.

        The Jinja prototype runs its consultations from
        `domain/content/cases.py`, but a row in `sessions` needs a real
        `case_version_id` — and migration 019 seeded all five cases as
        **drafts**, on purpose: `DATA_MODEL` §9.2 says publishing them without
        review would make the publication gate a formality. They stay drafts
        until a clinician approves them (T-023).

        So between T-013 and T-023 there is no published version to point at,
        and this is the one method allowed to say so. It returns an id and
        nothing else — no content, no title — so it cannot become a way to read
        unreviewed clinical material.

        Restricted to a `ServiceActor` so that every caller has to name a
        reason, and so a learner's scope cannot reach it even by mistake.
        Delete this when T-023 publishes the cases.
        """
        from nidan.infra.db.actor import ServiceActor

        if not isinstance(self._actor, ServiceActor):
            raise PermissionError(
                "prototype_version_id resolves unpublished cases and needs a "
                "ServiceActor with a stated reason")

        return self._conn.execute(sa.text("""
            SELECT cv.id FROM case_versions cv JOIN cases c ON c.id = cv.case_id
            WHERE c.slug = :slug AND cv.retired_at IS NULL
            ORDER BY cv.version DESC LIMIT 1
        """), {"slug": slug}).scalar()
