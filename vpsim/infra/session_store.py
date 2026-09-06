"""
In-memory session store.

Maps an opaque session id to the live consultation state:

    {session_id: {"session_data", "conversation", "pre_case_data", "feedback_data"}}

⚠️  TEMPORARY (BUILD_PLAN T-013). This is the blocker recorded as B1 in
    TECH_SPEC: state held in process memory is lost on restart and cannot be
    shared between workers, so the app is limited to a single process.

    It is replaced by an append-only event log in PostgreSQL (ADR-0003), after
    which session state is reconstructed rather than held. Nothing outside this
    module should assume the store is a dict.
"""

SESSION_STORE: dict = {}
