"""seed_engine

Revision ID: 018
Revises: 017

Engine version 1.0.0 — the thresholds every detector decision is made against
(DATA_MODEL §8.7).

**Why these live in the database rather than in code.** Every result written to
`session_results` carries the `engine_version_id` it was produced under. That is
what makes a past result interpretable: a score of 0.75 means nothing unless you
know the concentration threshold was 0.60 at the time.

It is also what makes threshold calibration (Phase 5) a data operation — replay
stored events under a candidate row and compare — rather than an edit to
`bias.py` that invalidates every historical result at once.

The values below are the ones currently hard-coded in
`nidan/domain/assessment/bias.py`. They are seeded, not adopted: T-016 is where
the engine starts reading them instead of its constants. Until then this row is
a record of what the constants are, and `tests/db/test_seed.py` fails if the two
drift apart.
"""

from __future__ import annotations

import json

from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None

# DATA_MODEL §8.7. Every constant that affects a result is here.
THRESHOLDS = {
    "anchoring": {
        "concentration": 0.60,   # bias.py: concentration > 0.60 fires rule A1
        "min_questions": 4,      #          A1 needs >= 4 questions
        "a2_min_anchor": 3,      #          A2 needs >= 3 anchor questions
        "a2_score": 0.85,        #          and scores a flat 0.85
    },
    "premature_closure": {
        "coverage": 0.60,        # bias.py: coverage_ratio < 0.60 fires rule P2
        "score_floor": 0.10,     #          a detection never scores below this
    },
    "confirmation_bias": {
        "clue_ratio": 0.25,      # bias.py: exploration_ratio < 0.25 fires C2
        "min_questions": 5,      #          C2 needs >= 5 questions asked
        "c1_score": 0.90,        #          C1 scores a flat 0.90
    },
    "topic_matching": {
        "mode": "keyword",       # substring matching; embeddings are Phase 5
        "similarity_threshold": None,
    },
}


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        INSERT INTO engine_versions
            (version, detector_version, lexicon_version, encoder_model,
             thresholds, is_current, notes)
        VALUES (%s, %s, %s, NULL, %s::jsonb, true, %s)
        """,
        (
            "1.0.0", "1.0.0", "1.0.0",
            json.dumps(THRESHOLDS),
            "Thresholds as validated in the pilot: 51/54 = 94% across all "
            "detector decisions over 18 labelled transcripts. Keyword matching; "
            "no encoder model until Phase 5.",
        ),
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "DELETE FROM engine_versions WHERE version = '1.0.0'")
