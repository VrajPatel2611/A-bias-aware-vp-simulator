"""app_roles

Revision ID: 020
Revises: 019

The database roles the application connects as (BUILD_PLAN T-012).

**Why this migration exists at all.** Migration 016 enabled Row-Level Security
and wrote the policies. Postgres then exempts two kinds of caller from every one
of them: **superusers and the table owner**. The migration runs as the owner, so
an application that reuses that connection role gets RLS silently disabled while
`pg_policies` still lists all six policies and every T-010 test still passes.
On Supabase this is not hypothetical — the direct connection string it hands you
authenticates as `postgres`, a superuser.

So the schema has to name a role that is neither, and the application has to run
its statements as that role:

| Role | RLS | Used for |
|---|---|---|
| `nidan_app`     | **applies** | every authenticated request |
| `nidan_service` | bypassed    | the anonymous-trial path, migrations, jobs |

`nidan_service` exists because the anonymous path has no `auth.uid()`, so
`own_sessions` (`user_id = auth.uid()`) evaluates to NULL and denies a trial
session to its own owner. `DATA_MODEL` §10.1 accepts that trade and requires the
path be "short, isolated, and separately tested" with an explicit
`anonymous_id` filter. See `nidan/infra/db/repositories/anonymous.py`.

**NOLOGIN group roles, not login users.** A login role needs a password, and a
password in a migration is a password in git. The application authenticates as
whatever user its `DATABASE_URL` names and then issues `SET LOCAL ROLE` per
transaction — which also means a superuser connection is demoted for the
duration of the statement, and RLS applies to it. Membership is granted to the
migrating user so a local `docker compose` stack works unconfigured.

**Why not reuse Supabase's `authenticated` / `service_role`.** Those are managed
by GoTrue and PostgREST, carry grants we do not control, and do not exist on a
plain Postgres. Owning the definition is what makes local and production the
same.
"""

from __future__ import annotations

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


# Tables the application may write. Everything else in `public` is readable and
# no more: clinical content is changed by the case editor through a service
# connection (T-021), never by a learner's request, whatever a bug asks for.
WRITABLE = (
    # learner-owned
    "profiles", "sessions", "session_events", "session_results",
    "feedback_texts", "subscriptions", "user_progress", "user_case_history",
    "idempotency_keys",
    # operational records written during a request
    "llm_calls", "leakage_flags", "audit_log",
)

_ROLES = ("nidan_app", "nidan_service")


def upgrade() -> None:
    bind = op.get_bind()

    # CREATE ROLE has no IF NOT EXISTS. The guard matters because Supabase
    # projects are migrated repeatedly and a failed CREATE would abort the
    # whole transaction -- the same reason migration 001 guards auth.uid().
    for role in _ROLES:
        bypass = "BYPASSRLS" if role == "nidan_service" else "NOBYPASSRLS"
        bind.exec_driver_sql(f"""
            DO $do$
            BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                CREATE ROLE {role} NOLOGIN {bypass};
              END IF;
            END
            $do$;
        """)

    # BYPASSRLS is an attribute, and attributes are NOT inherited through
    # membership -- only assumed via SET ROLE. That is precisely how the
    # application uses these roles, so this works; granting membership without
    # SET ROLE would not.
    bind.exec_driver_sql("ALTER ROLE nidan_service BYPASSRLS")
    bind.exec_driver_sql("ALTER ROLE nidan_app NOBYPASSRLS")

    for role in _ROLES:
        bind.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {role}")
        # Needed to call auth.uid() from inside a policy; the policies are
        # useless to a role that cannot reach the function they call.
        bind.exec_driver_sql(f"GRANT USAGE ON SCHEMA auth TO {role}")
        bind.exec_driver_sql(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {role}")
        bind.exec_driver_sql(
            f"GRANT INSERT, UPDATE, DELETE ON {', '.join(WRITABLE)} TO {role}")
        # session_events, llm_calls and audit_log are BIGSERIAL; an INSERT
        # without sequence USAGE fails at runtime, not here.
        bind.exec_driver_sql(
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}")
        # So the connecting user can SET ROLE to it. In production the app's
        # own login user is granted membership instead; locally they are the
        # same user and this makes the stack work with no extra setup.
        bind.exec_driver_sql(f"GRANT {role} TO CURRENT_USER")


def downgrade() -> None:
    bind = op.get_bind()
    for role in _ROLES:
        # DROP ROLE refuses while any privilege anywhere still references it,
        # and the error names the database rather than the grant. DROP OWNED
        # removes them; the roles own no objects, only permissions.
        bind.exec_driver_sql(f"""
            DO $do$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                EXECUTE 'REVOKE ALL ON SCHEMA public FROM {role}';
                EXECUTE 'DROP OWNED BY {role}';
                EXECUTE 'DROP ROLE {role}';
              END IF;
            END
            $do$;
        """)
