#!/usr/bin/env python3
"""
Generate migration 019 — the five clinical cases, from cases.py into
`cases` / `case_versions` (DATA_MODEL §8.1, §9.2).

    python scripts/generate_case_migration.py

This is the task that matters. Until it runs, clinical content lives inside a
2,421-line Python file and only a programmer can read a case — which is exactly
why the two clinician reviewers are blocked. It is the first step of the chain
T-021 (case editor) -> T-023 (review) -> ten reviewed cases -> launch.

Cases enter as **draft**, never published, including the ones that already ran
in the pilot. DATA_MODEL §9.2: "Publishing them without review would make the
trigger a formality."
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from nidan.domain.content.cases import CASES, get_case  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "migrations" / "versions" / "019_seed_cases.py"

# ── patient demographics ─────────────────────────────────────────────
# DATA_MODEL §8.1 wants patient.{name, age, sex}; cases.py holds that only in
# prose, and the five intros use five different sentence shapes. Parsing them
# with a regex would be fragile in a way nobody would notice, so they are
# transcribed here — each is stated unambiguously in the case's own intro and
# can be checked by reading it.
#
# NOT authored: every value below appears verbatim in patient_intro. The case
# editor (T-021) is where a clinician can correct or extend them.
PATIENT = {
    "case_1": {"name": "Ramesh Kumar", "age": 48, "sex": "male",
               "presenting_complaint": "Chest pain for 3 days"},
    "case_2": {"name": "Kavya Menon", "age": 29, "sex": "female",
               "presenting_complaint": "Breathlessness for 2 days"},
    "case_3": {"name": "Gopal Mehta", "age": 74, "sex": "male",
               "presenting_complaint": "Confusion, brought in by family"},
    "case_4": {"name": "Meera Patel", "age": 35, "sex": "female",
               "presenting_complaint": "Persistent tiredness"},
    "case_5": {"name": "Aisha Khan", "age": 21, "sex": "female",
               "presenting_complaint": "Vomiting and severe thirst"},
}

# Stable, human-readable slugs. `cases.slug` is UNIQUE and is what a URL and the
# admin console will use, so "case_1" would be a poor permanent identifier.
SLUG = {
    "case_1": "chest-pain-gerd",
    "case_2": "breathlessness-pulmonary-embolism",
    "case_3": "confusion-delirium-uti",
    "case_4": "fatigue-hypothyroidism",
    "case_5": "vomiting-diabetic-ketoacidosis",
}


def to_content(case: dict, case_id: str) -> dict:
    """Map a cases.py dict onto the §8.1 JSONB schema."""
    p = PATIENT[case_id]
    return {
        "title": case["title"],
        "patient": {
            "name": p["name"], "age": p["age"], "sex": p["sex"],
            "presenting_complaint": p["presenting_complaint"],
            "intro": case["patient_intro"],
            "opening_line": case["opening_line"],
        },
        "system_prompt": case["system_prompt"],
        "correct_diagnosis": case["correct_diagnosis"],
        "accepted_diagnoses": case["accepted_diagnoses"],
        "partial_diagnoses": case["partial_diagnoses"],
        "anchor_topic": case["anchor_topic"],
        "anchor_keywords": case["anchor_keywords"],
        "alternative_topics": case["alternative_topics"],
        "required_topics": case["required_topics"],
        "minimum_questions": case["minimum_questions"],
        "contradictory_clues": case["contradictory_clues"],
        # Shapes already match §8.1 — examination entries carry key/finding,
        # investigations carry category/result. Copied, not transformed.
        "examination": case["examination"],
        "investigations": case["investigations"],
    }


def build() -> str:
    rows = []
    for case_id in sorted(CASES):
        case = get_case(case_id)
        content = to_content(case, case_id)
        rows.append({
            "slug": SLUG[case_id],
            "specialty": "general_internal_medicine",
            "content": content,
            # Denormalised from content (DATA_MODEL §5.1). They exist because
            # the admin case bank and case selection filter and sort on them,
            # and extracting from JSONB per query cannot be indexed usefully.
            "title": content["title"],
            "anchor_topic": content["anchor_topic"],
            "minimum_questions": content["minimum_questions"],
            "required_topic_count": len(content["required_topics"]),
            "key_investigation_count": sum(
                1 for v in content["investigations"].values()
                if v.get("category") == "key"),
            # sha256 of the canonical content. Canonical = sorted keys, no
            # incidental whitespace, so the same content always hashes the same
            # regardless of how it was serialised.
            "content_hash": hashlib.sha256(
                json.dumps(content, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
        })

    return f'''"""seed_cases

Revision ID: 019
Revises: 018

The five clinical cases, migrated from cases.py into `cases` / `case_versions`
as version 1, status **draft** (DATA_MODEL §9.2).

Draft, not published — including the cases that already ran in the pilot.
§9.2: "Publishing them without review would make the trigger a formality."
The publication gate from migration 007 will refuse to publish them until a
clinician records an approving review (T-023).

GENERATED by scripts/generate_case_migration.py. Do not edit by hand.

This is the step that moves clinical content out of a 2,421-line Python file,
where only a programmer can read it, and into a table a case editor can reach.
"""

from __future__ import annotations

import json

from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None

CASES_SEED = json.loads(r"""{json.dumps(rows, ensure_ascii=False)}""")


def upgrade() -> None:
    bind = op.get_bind()
    for row in CASES_SEED:
        case_id = bind.exec_driver_sql(
            "INSERT INTO cases (slug, specialty, origin) "
            "VALUES (%s, %s, 'hand_authored') RETURNING id",
            (row["slug"], row["specialty"]),
        ).scalar()

        bind.exec_driver_sql(
            """
            INSERT INTO case_versions
                (case_id, version, status, content, title, anchor_topic,
                 minimum_questions, required_topic_count,
                 key_investigation_count, content_hash)
            VALUES (%s, 1, 'draft', %s::jsonb, %s, %s, %s, %s, %s, %s)
            """,
            (case_id, json.dumps(row["content"]), row["title"],
             row["anchor_topic"], row["minimum_questions"],
             row["required_topic_count"], row["key_investigation_count"],
             row["content_hash"]),
        )


def downgrade() -> None:
    bind = op.get_bind()
    # `= ANY(%s)` with a list, not `IN %s` with a tuple: psycopg 3 does not
    # expand tuples into an IN list the way psycopg 2 did.
    slugs = [r["slug"] for r in CASES_SEED]
    # case_versions cascades from cases.
    bind.exec_driver_sql("DELETE FROM cases WHERE slug = ANY(%s)", (slugs,))
'''


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"Wrote {OUT.name} — {len(CASES)} cases as v1 draft")
