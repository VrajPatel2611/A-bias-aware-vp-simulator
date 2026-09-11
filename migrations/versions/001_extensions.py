"""extensions

Revision ID: 001
Revises:
"""

from __future__ import annotations

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # DATA_MODEL §2.8
    bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto")   # gen_random_uuid()
    bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS citext")     # case-insensitive email
    bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")     # pgvector, embeddings
    bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")    # fuzzy admin search

    # ── auth.users ───────────────────────────────────────────────────
    # profiles.id references auth.users(id), which Supabase provides and we
    # never write to (DATA_MODEL §4.1). It does not exist in a plain Postgres
    # container, so local development and the test suite would have no schema
    # to migrate against.
    #
    # IF NOT EXISTS makes this a no-op on real Supabase, where the table is
    # already there and far richer. This stub carries only what the foreign key
    # needs. Nothing in the application may read or write it.
    bind.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS auth")
    bind.exec_driver_sql("""
        CREATE TABLE IF NOT EXISTS auth.users (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email       TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # auth.uid() — the function every RLS policy in migration 016 is written
    # against. Supabase provides it; it returns the authenticated user's id
    # from the request JWT.
    #
    # Created only if absent. Deliberately NOT "CREATE OR REPLACE": on real
    # Supabase that would overwrite their implementation with this one, which
    # would be a security incident rather than a convenience.
    #
    # The body matches Supabase's own, so RLS can be exercised locally:
    #     SET LOCAL request.jwt.claim.sub = '<uuid>';
    # Without it, the policies could only ever be tested in production.
    bind.exec_driver_sql("""
        DO $do$
        BEGIN
          IF NOT EXISTS (
              SELECT 1 FROM pg_proc p
              JOIN pg_namespace n ON n.oid = p.pronamespace
              WHERE n.nspname = 'auth' AND p.proname = 'uid'
          ) THEN
            CREATE FUNCTION auth.uid() RETURNS uuid AS $fn$
              SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid;
            $fn$ LANGUAGE sql STABLE;
          END IF;
        END
        $do$;
    """)


def downgrade() -> None:
    bind = op.get_bind()
    # The stub goes; the extensions stay. Dropping pgcrypto or vector could
    # break an unrelated database that shares the instance, and an extension
    # left in place costs nothing.
    bind.exec_driver_sql("DROP FUNCTION IF EXISTS auth.uid()")
    bind.exec_driver_sql("DROP TABLE IF EXISTS auth.users")
    bind.exec_driver_sql("DROP SCHEMA IF EXISTS auth CASCADE")
