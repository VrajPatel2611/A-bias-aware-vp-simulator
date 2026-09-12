"""
A local signing authority, so auth can be tested without Supabase (T-014).

Verification is pure computation over a token and a public key. Nothing about
it needs a real project — which matters, because it means T-014 is not blocked
on provisioning one, and because a test that reached a live key server would be
slow, flaky, and a network call the suite forbids.

This mints tokens with a throwaway RSA key and serves the matching public half
the way a JWKS endpoint would.
"""

from __future__ import annotations

import time
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER_URL = "https://test-project.supabase.co"
AUDIENCE = "authenticated"


class SigningAuthority:
    """One key pair, and the tokens it can sign."""

    def __init__(self, kid: str = "test-key-1") -> None:
        self.kid = kid
        # 2048 rather than 4096: the tests generate keys repeatedly and this is
        # the difference between a fast suite and a slow one. It is a test key.
        self._private = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    @property
    def public_key(self) -> Any:
        return self._private.public_key()

    def token(self, *, sub: str = "3f7c1b6e-2a4d-4c8f-9b1e-5d6a7c8e9f01",
              expires_in: int = 3600, audience: str | None = AUDIENCE,
              issuer: str | None = f"{ISSUER_URL}/auth/v1",
              kid: str | None = None, algorithm: str = "RS256",
              **extra_claims: Any) -> str:
        """A signed token. Every claim is overridable, because every one is tested."""
        now = int(time.time())
        claims: dict[str, Any] = {"sub": sub, "iat": now, "exp": now + expires_in}
        if audience is not None:
            claims["aud"] = audience
        if issuer is not None:
            claims["iss"] = issuer
        claims.update(extra_claims)

        return jwt.encode(claims, self._private, algorithm=algorithm,
                          headers={"kid": kid or self.kid})

    def token_without_kid(self) -> str:
        """
        A well-formed token whose header names no `kid`.

        Passing `headers={"kid": None}` does not do this — PyJWT rejects it.
        The header has to simply omit the field.
        """
        return jwt.encode({"sub": "x"}, self._private, algorithm="RS256",
                          headers={})
