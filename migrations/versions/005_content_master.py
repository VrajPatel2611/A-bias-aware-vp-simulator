"""content_master

Revision ID: 005
Revises: 004

DATA_MODEL §5.3, §5.4

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE examinations (
            key            TEXT PRIMARY KEY,        -- 'vitals'  — immutable once used
            label          TEXT NOT NULL,
            group_name     TEXT NOT NULL,
            normal_result  TEXT NOT NULL,
            display_order  SMALLINT NOT NULL,
            is_active      BOOLEAN NOT NULL DEFAULT true,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE investigations (
            key             TEXT PRIMARY KEY,       -- 'ecg'
            label           TEXT NOT NULL,
            group_name      TEXT NOT NULL,
            normal_result   TEXT NOT NULL,
            reference_range TEXT,
            display_order   SMALLINT NOT NULL,
            is_active       BOOLEAN NOT NULL DEFAULT true,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX ON examinations (group_name, display_order) WHERE is_active;
        CREATE INDEX ON investigations (group_name, display_order) WHERE is_active;

        CREATE TABLE topic_lexicon (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            topic_key     TEXT NOT NULL UNIQUE,     -- 'meal_relationship'
            display_name  TEXT NOT NULL,            -- 'Relationship to meals'
            description   TEXT,                     -- canonical sentence, embedded later
            is_active     BOOLEAN NOT NULL DEFAULT true,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE topic_phrases (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            topic_id        UUID NOT NULL REFERENCES topic_lexicon(id) ON DELETE CASCADE,
            phrase          TEXT NOT NULL,
            embedding       vector(384),            -- null until ADR-0013 phase 2

            -- Populated by a nightly job. Drives the dead-phrase report (UX A-06).
            match_count     INTEGER NOT NULL DEFAULT 0,
            last_matched_at TIMESTAMPTZ,

            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (topic_id, phrase)
        );

        CREATE INDEX ON topic_phrases USING hnsw (embedding vector_cosine_ops);
        CREATE INDEX ON topic_phrases (topic_id);
    """)
    bind.exec_driver_sql(
        "CREATE TRIGGER examinations_set_updated_at BEFORE UPDATE ON examinations "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )
    bind.exec_driver_sql(
        "CREATE TRIGGER investigations_set_updated_at BEFORE UPDATE ON investigations "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )
    bind.exec_driver_sql(
        "CREATE TRIGGER topic_lexicon_set_updated_at BEFORE UPDATE ON topic_lexicon "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS topic_phrases CASCADE")
    bind.exec_driver_sql("DROP TABLE IF EXISTS topic_lexicon CASCADE")
    bind.exec_driver_sql("DROP TABLE IF EXISTS investigations CASCADE")
    bind.exec_driver_sql("DROP TABLE IF EXISTS examinations CASCADE")
