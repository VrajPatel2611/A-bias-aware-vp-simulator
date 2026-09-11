"""enums

Revision ID: 003
Revises: 002
"""

from __future__ import annotations

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

# All six enum types, created together so later migrations can assume them.
# Values are verbatim from DATA_MODEL — an enum is part of the contract, and a
# value added here without updating §4–7 is a silent divergence.
ENUMS: list[tuple[str, tuple[str, ...]]] = [
    # §4.1
    ("professional_role", ("medical_student", "intern", "resident",
                           "physician", "other")),
    ("subscription_tier", ("free", "pro")),
    # §5.1
    ("case_status", ("draft", "in_review", "published", "retired")),
    ("case_origin", ("hand_authored", "generated")),
    # §6.1
    ("session_status", ("active", "completed", "abandoned", "expired")),
    # §6.2
    ("event_type", ("question", "patient_reply", "examination", "investigation",
                    "early_diagnosis", "diagnosis", "feedback_viewed",
                    "input_blocked")),
]


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in ENUMS:
        labels = ", ".join(f"'{v}'" for v in values)
        bind.exec_driver_sql(f"CREATE TYPE {name} AS ENUM ({labels})")


def downgrade() -> None:
    bind = op.get_bind()
    for name, _ in reversed(ENUMS):
        bind.exec_driver_sql(f"DROP TYPE IF EXISTS {name}")
