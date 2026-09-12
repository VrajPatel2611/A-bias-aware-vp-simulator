"""
SQLAlchemy metadata anchor (BUILD_PLAN T-010).

**The migrations are the source of truth for the schema.** They are hand-written
(DATA_MODEL §9.1) because autogenerate cannot express partial indexes, CHECK
constraints, append-only triggers, the publication gate or RLS policies — and
would silently drop them on the next revision.

This module holds only the `MetaData` object that `migrations/env.py` imports.
**It deliberately does not define the 21 tables.**

Defining them here would duplicate the schema, and a duplicate drifts.

T-010 left this open, expecting T-012 to add table objects for whatever the
repositories query and a test diffing them against a freshly migrated database.
T-012 built the repositories with textual SQL instead (`infra/db/repositories/`),
which settles it the other way: those `Table` objects would be read by nothing
and would exist only to be compared — a second copy of the schema, which is the
outcome this module was written to avoid.

The drift check still exists, in the form the code actually takes.
`tests/db/test_repository_scope.py::test_every_repository_query_still_matches_the_schema`
executes every public repository method against a real migrated database, so a
renamed or dropped column fails the build rather than the first request that
touches it. That tests the SQL that ships, which the metadata diff would not
have.

To see the schema, read `migrations/versions/` or `docs/spec/DATA_MODEL.md` §4–7.
"""

from __future__ import annotations

from sqlalchemy import MetaData

# Deterministic constraint names. Unused by the drift check in the end (see
# above), but kept: they are what makes any future metadata comparable to the
# migrated database, and changing them later would rename live constraints.
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})
