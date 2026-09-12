"""
Token verification (BUILD_PLAN T-014, `ADR-0002`).

No database and no Supabase: verification is computation over a token and a
public key, and these tests mint their own with a throwaway RSA key
(`tests/fakes/auth.py`). That is deliberate — it means the security-critical
half of T-014 is checked on every run, including the runs where Docker is
unavailable and `tests/db` skips entirely.
"""

from __future__ import annotations

import time

import pytest

from nidan.config import settings
from nidan.infra.auth import jwks
from nidan.infra.auth.tokens import (
    ALLOWED_ALGORITHMS,
    JWKSUnavailable,
    TokenExpired,
    TokenInvalid,
    TokenMissing,
    verify,
)
from tests.fakes.auth import SigningAuthority

# ── the happy path ───────────────────────────────────────────────────

def test_a_valid_token_yields_its_subject(authority):
    token = authority.token(sub="3f7c1b6e-2a4d-4c8f-9b1e-5d6a7c8e9f01",
                            email="learner@example.org")
    verified = verify(token)
    assert str(verified.user_id) == "3f7c1b6e-2a4d-4c8f-9b1e-5d6a7c8e9f01"
    assert verified.email == "learner@example.org"


def test_the_backend_never_sees_a_password(authority):
    """
    Criterion 5, as far as a unit test can state it: everything the backend
    learns about a user comes from a signed token it did not issue.
    """
    verified = verify(authority.token())
    assert "password" not in verified.claims
    assert not any("password" in k.lower() for k in verified.claims)


# ── expiry is its own answer ─────────────────────────────────────────

def test_an_expired_token_raises_token_expired(authority):
    """
    Criterion 3. Its own exception, mapped to its own code, because
    `API_CONTRACT` §3.3 makes it the signal to refresh and retry once. Reported
    as a generic failure it would log the learner out mid-consultation instead.
    """
    with pytest.raises(TokenExpired):
        verify(authority.token(expires_in=-60))


def test_a_token_just_inside_the_leeway_still_verifies(authority):
    """Small clock differences between Supabase and this host are not a logout."""
    assert verify(authority.token(expires_in=-5))


# ── the claim checks that are easy to omit ───────────────────────────

def test_a_token_from_another_project_is_refused(authority):
    """
    The vulnerability this check exists for.

    A token from anyone else's Supabase project — a free account takes a
    minute to create — carries a valid signature from *a* Supabase. Without the
    audience and issuer checks it would authenticate here as whatever `sub` it
    names. PyJWT only checks them if you pass `audience=` and `issuer=`, so the
    hole is one missing keyword argument and leaves no trace.
    """
    with pytest.raises(TokenInvalid, match="audience"):
        verify(authority.token(audience="some-other-project"))

    with pytest.raises(TokenInvalid, match="different project"):
        verify(authority.token(issuer="https://attacker.supabase.co/auth/v1"))


def test_a_token_missing_a_required_claim_is_refused(authority):
    """
    `require` in the decode options: a token that simply omits `aud` or `iss`
    must fail as surely as one that carries the wrong value. Otherwise the
    checks above are bypassed by leaving the claim out.
    """
    with pytest.raises(TokenInvalid):
        verify(authority.token(audience=None))
    with pytest.raises(TokenInvalid):
        verify(authority.token(issuer=None))


def test_a_token_signed_by_a_different_key_is_refused(authority):
    """A valid-looking token signed by someone who is not Supabase."""
    impostor = SigningAuthority(kid=authority.kid)   # same kid, different key
    with pytest.raises(TokenInvalid):
        verify(impostor.token())


def test_a_subject_that_is_not_a_uuid_is_refused(authority):
    """
    Supabase issues UUID subjects. Accepting anything else would mean querying
    with an attacker-chosen string where a user id belongs.
    """
    with pytest.raises(TokenInvalid, match="sub is not a UUID"):
        verify(authority.token(sub="'; DROP TABLE sessions; --"))


def test_only_asymmetric_algorithms_are_accepted():
    """
    The algorithm-confusion attack: an attacker signs a token with HS256 using
    the *public* key as the HMAC secret, and a library that trusts the token's
    own `alg` header agrees. The token never decides how it is checked.
    """
    assert "HS256" not in ALLOWED_ALGORITHMS
    assert all(a.startswith(("RS", "ES")) for a in ALLOWED_ALGORITHMS)


def test_a_token_with_no_kid_is_refused(authority):
    with pytest.raises(TokenInvalid, match="no kid"):
        verify(authority.token_without_kid())


def test_garbage_is_refused_without_a_stack_trace(authority):
    for rubbish in ("not.a.token", "abc", "..", "Bearer something"):
        with pytest.raises(TokenInvalid):
            verify(rubbish)


def test_nothing_presented_is_distinct_from_something_invalid(authority):
    """
    "No credentials" and "bad credentials" are different situations: one is a
    signed-out visitor, the other may be an attack. They share a response code
    but not a code path.
    """
    for empty in ("", "   ", None):
        with pytest.raises(TokenMissing):
            verify(empty)


# ── the cache, and the rotation trap ─────────────────────────────────

def test_the_keys_are_fetched_once_and_then_cached(authority):
    for _ in range(5):
        verify(authority.token())
    assert authority.fetches == 1, "the key set was refetched on a cached key"


def test_a_rotated_key_is_fetched_immediately_not_after_the_ttl(authority):
    """
    The trap in a 10-minute TTL.

    Supabase rotates keys. A cache that refreshes only on expiry answers
    "unknown key, 401" to every request until the TTL runs out — logging out
    every user at once, then fixing itself before anyone can investigate. An
    unseen `kid` must force a refetch.
    """
    verify(authority.token())
    assert authority.fetches == 1

    rotated = SigningAuthority(kid="test-key-2")
    authority.keys = {"test-key-2": rotated.public_key}

    assert verify(rotated.token(kid="test-key-2"))
    assert authority.fetches == 2, "a rotated key did not trigger a refetch"


def test_unknown_kids_cannot_be_used_to_hammer_the_key_server(authority):
    """
    The opposite failure. If every unknown `kid` forced a fetch, a burst of
    junk tokens would become a burst of requests to Supabase — a denial of
    service anybody can trigger from outside, against a dependency we do not
    control.
    """
    for i in range(25):
        with pytest.raises((JWKSUnavailable, TokenInvalid)):
            verify(authority.token(kid=f"nonexistent-{i}"))

    assert authority.fetches <= 2, (
        f"{authority.fetches} fetches from 25 bad tokens — the refetch floor "
        f"is not holding")


def test_a_stale_cache_is_refreshed(authority, monkeypatch):
    """After the TTL, the next verification fetches again."""
    verify(authority.token())
    assert authority.fetches == 1

    real_monotonic = time.monotonic
    monkeypatch.setattr(jwks.time, "monotonic",
                        lambda: real_monotonic() + jwks.CACHE_TTL_S + 60)

    verify(authority.token())
    assert authority.fetches == 2


def test_an_unreachable_key_server_is_not_reported_as_a_bad_token(monkeypatch):
    """
    `JWKSUnavailable`, not `TokenInvalid`. The credentials may be perfectly
    good — we cannot check them. The API turns this into a 503, because a 401
    would send every client into a refresh loop against an outage.

    The token here is well-formed on purpose: `"a.b.c"` would fail at header
    parsing and never reach the key server, so the test would pass without
    exercising anything it claims to.
    """
    good_token = SigningAuthority().token()
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    jwks.cache.clear()
    with pytest.raises(JWKSUnavailable):
        verify(good_token)
