"""cases

Revision ID: 006
Revises: 005

DATA_MODEL §5.1, §5.2

SQL is verbatim from the specification. Where they diverge, the specification
is the contract and this file is the bug.

`exec_driver_sql`, not `op.execute`: the spec's DDL contains comments with
JSON like {"last10":0.2}, and op.execute reads `:0` as a bind parameter.
Raw DDL must reach the driver uninterpreted.
"""

from __future__ import annotations

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""
        CREATE TABLE cases (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug        TEXT NOT NULL UNIQUE,       -- 'chest-pain-gerd'
            specialty   TEXT,
            origin      case_origin NOT NULL DEFAULT 'hand_authored',
            created_by  UUID REFERENCES profiles(id),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE case_versions (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id              UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            version              INTEGER NOT NULL,
            status               case_status NOT NULL DEFAULT 'draft',

            -- Full case payload. Schema in §8.1.
            content              JSONB NOT NULL,

            -- Denormalised from content for querying without JSON extraction.
            title                TEXT NOT NULL,
            anchor_topic         TEXT NOT NULL,
            minimum_questions    SMALLINT NOT NULL CHECK (minimum_questions BETWEEN 3 AND 20),
            required_topic_count SMALLINT NOT NULL,
            key_investigation_count SMALLINT NOT NULL,

            content_hash         TEXT NOT NULL,          -- sha256 of canonical content
            embedding            vector(384),            -- near-duplicate detection

            -- Provenance (populated only for generated cases)
            source_dataset       TEXT,
            source_record_id     TEXT,
            qa_report            JSONB,
            trap_selftest_passed BOOLEAN,

            published_at         TIMESTAMPTZ,
            retired_at           TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE (case_id, version),

            CONSTRAINT published_requires_timestamp
                CHECK (status <> 'published' OR published_at IS NOT NULL)
        );

        CREATE UNIQUE INDEX one_published_version_per_case
            ON case_versions (case_id) WHERE status = 'published';

        CREATE INDEX published_cases
            ON case_versions (id) WHERE status = 'published';

        CREATE INDEX ON case_versions USING hnsw (embedding vector_cosine_ops);

        CREATE TABLE clinical_reviews (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_version_id UUID NOT NULL REFERENCES case_versions(id) ON DELETE CASCADE,
            reviewer_id     UUID NOT NULL REFERENCES profiles(id),

            decision        TEXT NOT NULL
                            CHECK (decision IN ('approved','changes_requested','rejected')),

            -- Structured rubric, 1-5 each. Shape in §8.4.
            scores          JSONB NOT NULL,
            comments        TEXT,

            reviewed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX ON clinical_reviews (case_version_id, reviewed_at DESC);
        CREATE INDEX ON clinical_reviews (reviewer_id, reviewed_at DESC);
    """)
    bind.exec_driver_sql(
        "CREATE TRIGGER case_versions_set_updated_at BEFORE UPDATE ON case_versions "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE IF EXISTS clinical_reviews CASCADE")
    bind.exec_driver_sql("DROP TABLE IF EXISTS case_versions CASCADE")
    bind.exec_driver_sql("DROP TABLE IF EXISTS cases CASCADE")
