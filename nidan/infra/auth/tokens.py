"""
Verifying a Supabase JWT (BUILD_PLAN T-014, `ADR-0002`).

The backend never sees a password. It receives a token Supabase issued, checks
that the signature is one of Supabase's, checks that the claims are ours, and
reads `sub` as the user id. That is the whole of authentication here, and the
second check is the one that is easy to leave out.

**Verifying the signature is not verifying the token.** A signature says "some
Supabase project issued this". Without `aud` and `iss`, a valid token from
*anyone else's* project — a free account anybody can create in a minute —
authenticates against our API as whatever `sub` it names. PyJWT only checks
`aud` if you pass `audience=`, and only checks `iss` if you pass `issuer=`, so
the vulnerability is one missing keyword argument and leaves no trace.

Expiry is separated from every other failure on purpose. `API_CONTRACT` §3.3
gives `token_expired` its own code so the client refreshes and retries once; a
generic `unauthenticated` logs the user out instead, mid-consultation.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import jwt

from nidan.config import settings
from nidan.infra.auth.jwks import JWKSUnavailable, cache

# Asymmetric only. Listing the algorithms is not a formality: PyJWT will
# happily verify an HS256 token using the "key" it is given, so a caller that
# accepts whatever `alg` the token names invites the classic confusion attack —
# an attacker signs with HMAC using the public key as the secret and the
# library agrees. The token decides nothing about how it is checked.
ALLOWED_ALGORITHMS = ("RS256", "ES256", "RS512", "ES512")

# Tolerance for clock difference between Supabase and this host. Small: a
# generous leeway is a token that stays valid after it should not.
LEEWAY_S = 10


class AuthError(Exception):
    """Base for every authentication failure."""


class TokenMissing(AuthError):
    """No credentials were presented."""


class TokenExpired(AuthError):
    """Valid, but past its expiry. The client should refresh and retry once."""


class TokenInvalid(AuthError):
    """Present but unusable: bad signature, wrong audience, wrong issuer."""


@dataclass(frozen=True)
class VerifiedToken:
    """What a verified token tells us. Nothing more is trusted."""

    user_id: UUID
    email: str | None
    claims: dict


def verify(token: str) -> VerifiedToken:
    """
    Verify a Supabase JWT and return its subject.

    Raises `TokenMissing`, `TokenExpired`, `TokenInvalid`, or `JWKSUnavailable`.
    """
    if not token or not token.strip():
        raise TokenMissing("no token presented")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        raise TokenInvalid(f"unreadable token header: {e}") from e

    kid = header.get("kid")
    if not kid:
        raise TokenInvalid("token header carries no kid, so no key can be selected")

    # Raises JWKSUnavailable, which callers must NOT report as a bad token:
    # it means we cannot verify, not that the credentials are wrong.
    key = cache.key_for(kid)

    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=list(ALLOWED_ALGORITHMS),
            audience=settings.SUPABASE_JWT_AUDIENCE,
            issuer=settings.jwt_issuer,
            leeway=LEEWAY_S,
            options={
                # Spelled out rather than left to defaults. A default that
                # changes between PyJWT versions would silently stop checking
                # something, and nothing would fail.
                "require": ["exp", "sub", "aud", "iss"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except jwt.ExpiredSignatureError as e:
        raise TokenExpired("the access token has expired") from e
    except jwt.InvalidAudienceError as e:
        # Worth its own branch for the message alone: this is what a token from
        # another Supabase project looks like, and it should be recognisable.
        raise TokenInvalid(
            f"token audience is not {settings.SUPABASE_JWT_AUDIENCE!r}") from e
    except jwt.InvalidIssuerError as e:
        raise TokenInvalid("token was issued by a different project") from e
    except jwt.PyJWTError as e:
        raise TokenInvalid(f"token could not be verified: {e}") from e

    subject = claims.get("sub")
    try:
        user_id = UUID(str(subject))
    except (TypeError, ValueError) as e:
        # Supabase issues UUID subjects. Anything else is a token we do not
        # understand, and guessing would mean querying with an attacker's
        # string in place of a user id.
        raise TokenInvalid(f"sub is not a UUID: {subject!r}") from e

    return VerifiedToken(user_id=user_id, email=claims.get("email"), claims=claims)


__all__ = [
    "AuthError", "TokenMissing", "TokenExpired", "TokenInvalid",
    "JWKSUnavailable", "VerifiedToken", "verify",
    "ALLOWED_ALGORITHMS", "LEEWAY_S",
]
