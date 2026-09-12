"""
The v1 JSON API (BUILD_PLAN T-014).

The first slice: identity. `openapi.yaml` declares the whole surface and T-030
implements the rest; everything not implemented here still answers 501, which
is what lets the frontend build against the contract (sync point S-1).

These routes are the JSON API the Next.js client will use (`ADR-0006`). The
server-rendered blueprint in `routes.py` is the prototype and is replaced at
T-030 — they coexist deliberately rather than one being half-migrated into the
other.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Blueprint, jsonify, request

from nidan.api.auth import current_actor, error, require_auth
from nidan.infra.db.repositories import repo_scope

bp = Blueprint("v1", __name__)

# Fields a user may set on themselves. The repository has its own allow-list;
# this one exists so the API rejects an unknown field with a 422 naming it,
# rather than a 500 from a layer the client cannot see.
_WRITABLE = frozenset({
    "display_name", "professional_role", "year_of_training", "country",
    "timezone", "consent_research", "consent_version",
})


def _profile_json(row: Mapping[str, Any]) -> dict[str, Any]:
    """
    A profile as the contract describes it (`openapi.yaml` → `Profile`).

    Built explicitly rather than by dumping the row. A `SELECT *` reaching the
    client is how `research_pid` — the pseudonym that keeps analyses
    unlinkable — ends up in a response next to an email, which is exactly what
    `DATA_MODEL` §4.1 says must never happen.

    `sessions_remaining_this_month` is absent until T-017 owns the allowance.
    It is free-tier only and belongs on the dashboard, NEVER in a consultation
    (`PRD` P2).
    """
    return {
        "id": str(row["id"]),
        "display_name": row["display_name"],
        "professional_role": row["professional_role"],
        "year_of_training": row["year_of_training"],
        "country": row["country"],
        "timezone": row["timezone"],
        "subscription_tier": row["subscription_tier"],
        "consent_research": row["consent_research"],
        "onboarded_at": row["onboarded_at"].isoformat() if row["onboarded_at"] else None,
    }


@bp.post("/me")
@require_auth
def create_profile():
    """
    Create the authenticated user's profile. Idempotent (`API_CONTRACT` §3.1).

    The profile row is created here rather than by a database trigger, because
    creation needs `research_pid` generation, timezone capture and — from
    T-015 — trial claiming. Those are application concerns.

    Idempotent because clients retry and Supabase replays webhooks: the
    repository's INSERT is `ON CONFLICT DO NOTHING`, so two concurrent first
    requests both succeed instead of the second hitting a primary-key
    violation.
    """
    body = request.get_json(silent=True) or {}

    unknown = set(body) - _WRITABLE - {"anonymous_id"}
    if unknown:
        return error("validation_failed",
                     f"Unexpected field(s): {', '.join(sorted(unknown))}.", 422)

    fields = {k: v for k, v in body.items() if k in _WRITABLE}

    # Accepted and ignored until T-015, which owns the 30-day claim window and
    # the owner_is_exclusive transition. Accepting it now keeps the request
    # shape stable for the client; silently succeeding while claiming nothing
    # would be worse than refusing, so say so.
    if body.get("anonymous_id"):
        return error("validation_failed",
                     "Claiming a trial session is not available yet (T-015).", 422)

    try:
        with repo_scope(current_actor()) as db:
            existed = db.profiles.get() is not None
            row = db.profiles.ensure(**fields)
    except ValueError as e:
        return error("validation_failed", str(e), 422)

    # 200 on a repeat, 201 on creation. Both are success — the criterion is
    # idempotency, not a fixed status — and the difference tells a client
    # whether onboarding still needs showing.
    return jsonify(_profile_json(row)), (200 if existed else 201)


@bp.get("/me")
@require_auth
def read_profile():
    """The authenticated user's profile."""
    with repo_scope(current_actor()) as db:
        row = db.profiles.get()

    if row is None:
        return error("not_found", "No profile yet. Create one with POST /me.", 404)
    return jsonify(_profile_json(row)), 200
