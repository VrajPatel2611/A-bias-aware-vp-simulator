"""ops

Revision ID: 015
Revises: 014

DATA_MODEL §7.1–7.5

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE llm_calls (
            id            BIGSERIAL PRIMARY KEY,
            session_id    UUID REFERENCES sessions(id) ON DELETE SET NULL,

            purpose       TEXT NOT NULL
                          CHECK (purpose IN ('patient','feedback','extraction','judge','grounding')),
            provider      TEXT NOT NULL,
            model         TEXT NOT NULL,

            prompt_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            cost_usd      NUMERIC(10,6) NOT NULL,
            latency_ms    INTEGER NOT NULL,

            status        TEXT NOT NULL CHECK (status IN ('ok','retried','failed','fallback')),
            attempt       SMALLINT NOT NULL DEFAULT 1,

            created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX ON llm_calls (created_at DESC);
        CREATE INDEX ON llm_calls (purpose, model, created_at DESC);
        CREATE INDEX ON llm_calls (session_id) WHERE session_id IS NOT NULL;

        CREATE TABLE leakage_flags (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id     UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            event_seq      INTEGER NOT NULL,

            leaked_topics  TEXT[] NOT NULL,
            severity       TEXT NOT NULL CHECK (severity IN ('low','high')),

            reviewed       BOOLEAN NOT NULL DEFAULT false,
            confirmed      BOOLEAN,
            reviewed_by    UUID REFERENCES profiles(id),
            reviewed_at    TIMESTAMPTZ,

            created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX ON leakage_flags (reviewed, severity, created_at DESC);

        CREATE TABLE idempotency_keys (
            key          TEXT PRIMARY KEY,
            user_id      UUID REFERENCES profiles(id) ON DELETE CASCADE,
            endpoint     TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            response     JSONB,
            status_code  SMALLINT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at   TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '24 hours')
        );

        CREATE INDEX ON idempotency_keys (expires_at);

        CREATE TABLE audit_log (
            id           BIGSERIAL PRIMARY KEY,
            actor_id     UUID REFERENCES profiles(id),
            action       TEXT NOT NULL,          -- 'case_version.published'
            entity_type  TEXT NOT NULL,
            entity_id    UUID,
            reason       TEXT,                   -- required for support access
            metadata     JSONB,
            ip_address   INET,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX ON audit_log (entity_type, entity_id, created_at DESC);
        CREATE INDEX ON audit_log (actor_id, created_at DESC);

        CREATE TRIGGER audit_log_append_only
          BEFORE UPDATE OR DELETE ON audit_log
          FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

        CREATE TABLE feature_flags (
            key          TEXT PRIMARY KEY,
            is_enabled   BOOLEAN NOT NULL DEFAULT false,
            rollout_pct  SMALLINT NOT NULL DEFAULT 0 CHECK (rollout_pct BETWEEN 0 AND 100),
            description  TEXT,
            updated_by   UUID REFERENCES profiles(id),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    bind.exec_driver_sql(
        "CREATE TRIGGER feature_flags_set_updated_at BEFORE UPDATE ON feature_flags "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS feature_flags CASCADE")
    bind.exec_driver_sql("DROP TABLE IF EXISTS audit_log CASCADE")
    bind.exec_driver_sql("DROP TABLE IF EXISTS idempotency_keys CASCADE")
    bind.exec_driver_sql("DROP TABLE IF EXISTS leakage_flags CASCADE")
    bind.exec_driver_sql("DROP TABLE IF EXISTS llm_calls CASCADE")
