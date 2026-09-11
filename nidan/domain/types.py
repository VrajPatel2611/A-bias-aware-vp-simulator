"""
Shared type aliases for the domain layer.

These name the dictionary shapes the domain passes around. They are aliases,
not validation — `Session` is a plain dict at runtime. Their value is that a
signature reading `(session: Session, case: Case) -> DetectorResult` says what a
function does, where `(dict, dict) -> dict` says nothing.

NOTE (BUILD_PLAN T-013): `Session` becomes a reconstruction from an append-only
event log. Naming the shape here means that change has one place to start.
"""

from typing import Any, TypedDict

# A clinical case definition from nidan.domain.content.cases.
Case = dict[str, Any]

# The short {id, title, intro} form used for case listings.
CaseSummary = dict[str, str]

# Live consultation state: questions asked, topics covered, exams, diagnosis.
Session = dict[str, Any]


class DetectorResult(TypedDict):
    """
    What every bias detector returns.

    `evidence` carries the learner's own questions (or the topics they missed).
    It is not optional: property P2 requires that a flag can always be traced
    back to what the learner actually did (ADR-0004).
    """

    detected: bool
    score: float
    reason: str
    evidence: list[str]


# {"anchoring": DetectorResult, "premature_closure": ..., "confirmation_bias": ...}
BiasResults = dict[str, DetectorResult]

# Output of nidan.domain.assessment.clinical.evaluate_clinical.
ClinicalEval = dict[str, Any]
