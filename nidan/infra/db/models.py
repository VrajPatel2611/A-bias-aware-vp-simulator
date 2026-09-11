"""
SQLAlchemy metadata anchor (BUILD_PLAN T-010).

**The migrations are the source of truth for the schema.** They are hand-written
(DATA_MODEL §9.1) because autogenerate cannot express partial indexes, CHECK
constraints, append-only triggers, the publication gate or RLS policies — and
would silently drop them on the next revision.

This module currently holds only the `MetaData` object that `migrations/env.py`
imports. **It deliberately does not define the 21 tables.**

Defining them here would duplicate the schema, and a duplicate drifts. T-012
builds the repository layer and will add whatever table objects it actually
queries — at which point a test comparing this metadata against a freshly
migrated database earns its place. Adding 21 table definitions now, before
anything reads them, would be 21 opportunities to disagree with the migrations
for no benefit.

Until then: to see the schema, read `migrations/versions/` or
`docs/spec/DATA_MODEL.md` §4–7.
"""

from __future__ import annotations

from sqlalchemy import MetaData

# Deterministic constraint names, so this metadata and the migrated database
# are comparable when T-012 adds the drift check.
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})
