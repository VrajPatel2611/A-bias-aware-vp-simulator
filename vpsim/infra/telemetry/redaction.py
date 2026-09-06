"""
Redaction — the last line of defence (BUILD_PLAN T-007, TECH_SPEC §10).

The rule is *never log raw question text at INFO, never emails or keys*. The
primary enforcement is not logging those things in the first place; this module
is what catches the case where someone does anyway, months from now, while
debugging.

Two reasons a scrubber matters more here than in most products:

  · A learner's questions are the raw material of the assessment. A consultation
    transcript in a log file is the same data the database protects with RLS
    (asset A2, SECURITY_SPEC §2).
  · Learners are asked never to enter real patient data, and mostly will not.
    "Mostly" is the problem: T-035 adds a guard, and until then anything a
    learner types could contain something that must not be retained.

Redaction is deliberately aggressive. A log line with a mangled key is a small
inconvenience; a log line with a working one is an incident.
"""

from __future__ import annotations

import re

REDACTED = "[redacted]"

# Ordered: the more specific patterns run first so a key inside an email-shaped
# string is not merely partly masked.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Groq uses gsk_; OpenAI sk-; Stripe sk_live_/pk_test_/rk_live_ (T-041).
    # The body allows underscores and hyphens so Stripe's prefixed keys match
    # in full rather than up to the first separator.
    ("api_key", re.compile(r"\b(?:gsk|sk|pk|rk)[_\-][A-Za-z0-9_\-]{8,}")),
    ("google_key", re.compile(r"\bAIza[A-Za-z0-9_\-]{10,}\b")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{10,}", re.I)),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\b")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
]

# Field names whose VALUE is never safe to log, whatever it looks like.
SENSITIVE_FIELDS = frozenset({
    "question", "question_text", "text", "message", "user_message",
    "diagnosis", "answer", "transcript", "content", "prompt", "reply",
    "password", "token", "api_key", "groq_api_key", "secret",
    "flask_secret_key", "authorization", "email", "dsn",
})


def scrub(value: str) -> str:
    """Mask anything key-shaped or address-shaped in a string."""
    for _, pattern in _PATTERNS:
        value = pattern.sub(REDACTED, value)
    return value


def safe_extra(fields: dict[str, object]) -> dict[str, object]:
    """
    Prepare structured log fields.

    A key in SENSITIVE_FIELDS has its value replaced outright — free text is not
    worth pattern-matching, because the risk is the text itself, not a token
    inside it. Everything else is scrubbed for key and email shapes.
    """
    out: dict[str, object] = {}
    for key, value in fields.items():
        if key.lower() in SENSITIVE_FIELDS:
            out[key] = REDACTED
        elif isinstance(value, str):
            out[key] = scrub(value)
        else:
            out[key] = value
    return out


def question_fingerprint(text: str) -> dict[str, object]:
    """
    What may be logged about a learner's question instead of the question.

    Length and word count are enough to investigate "the app hung on a long
    input" without retaining what was asked. The text itself lives in the
    session record, which is access-controlled; a log file is not.
    """
    stripped = (text or "").strip()
    return {"question_chars": len(stripped), "question_words": len(stripped.split())}
