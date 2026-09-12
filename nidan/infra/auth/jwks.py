"""
Supabase's signing keys, cached (BUILD_PLAN T-014, `ADR-0002`).

`API_CONTRACT` §2.2 and `SECURITY_SPEC` L1 specify the same thing: verify the
JWT against Supabase's JWKS, cached with a 10-minute TTL. Fetching the keys on
every request would put an external HTTP call in front of every authenticated
route — including the patient's reply, which is already the slowest thing we do.

**The TTL hides a trap, and it is why this module is not ten lines.** A cache
that refreshes only on expiry means a key rotation breaks every request until
the TTL runs out. Supabase rotates keys; when it does, tokens arrive signed by a
`kid` this cache has never seen. Answering "unknown key, 401" for up to ten
minutes would log out every user at once and then fix itself before anyone could
investigate.

So an unknown `kid` forces an immediate refetch. That opens the opposite
failure: a burst of tokens carrying a bogus `kid` becomes a burst of requests to
Supabase, which is a denial of service anyone can trigger from outside. Hence
`_MIN_REFETCH_INTERVAL_S` — an unknown key may force a refetch, but not more
often than once every few seconds.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from nidan.config import settings

CACHE_TTL_S = 600.0            # 10 minutes, per API_CONTRACT §2.2
_MIN_REFETCH_INTERVAL_S = 5.0  # floor on rotation-triggered refetches
_HTTP_TIMEOUT_S = 5.0


class JWKSUnavailable(RuntimeError):
    """
    The signing key could not be obtained.

    Deliberately distinct from an invalid or expired token. This means *we*
    cannot verify, not that the caller's credentials are bad, and the two must
    not produce the same response: telling a client its token expired when the
    key server is unreachable sends it into a refresh loop against an outage.
    """


class KeyCache:
    """
    Process-local cache of the project's public keys.

    Locked, because gunicorn runs threads: without it a rotation makes every
    in-flight request fetch the keys at the same moment.
    """

    def __init__(self) -> None:
        self._keys: dict[str, Any] = {}
        self._fetched_at: float | None = None
        # The last refetch that did NOT yield the key being asked for. Only
        # failures throttle; see _may_refetch.
        self._last_failure: float | None = None
        self._lock = threading.Lock()

    # ── public ───────────────────────────────────────────────────────

    def key_for(self, kid: str) -> Any:
        """
        The signing key for this `kid`, fetching or refreshing as needed.

        Raises `JWKSUnavailable` if the key is still unknown after a refetch.
        """
        key = self._fresh_key(kid)
        if key is not None:
            return key

        # Either the cache is cold or stale, or this `kid` is new to us. The
        # second case is a rotation, and waiting out the TTL would be an outage.
        if self._may_refetch():
            self._refresh()
            with self._lock:
                key = self._keys.get(kid)
            if key is not None:
                return key
            # The refetch did not produce it, so this `kid` is junk rather than
            # rotated. Start the floor NOW — see _may_refetch.
            with self._lock:
                self._last_failure = time.monotonic()
        else:
            # Throttled. A stale key still verifies a token signed with it, so
            # serve one rather than refuse: the floor exists to protect the key
            # server, not to invalidate sessions.
            with self._lock:
                key = self._keys.get(kid)
            if key is not None:
                return key

        raise JWKSUnavailable(
            f"no signing key with kid={kid!r}; the token was not issued by "
            f"{settings.SUPABASE_URL or 'the configured project'}")

    def clear(self) -> None:
        """Drop everything. For tests, and for a clean restart."""
        with self._lock:
            self._keys = {}
            self._fetched_at = None
            self._last_failure = None

    def age_s(self) -> float:
        """Seconds since the last successful fetch; infinite if never."""
        with self._lock:
            if self._fetched_at is None:
                return float("inf")
            return time.monotonic() - self._fetched_at

    # ── internals ────────────────────────────────────────────────────

    def _may_refetch(self) -> bool:
        """
        Whether an unknown `kid` may trigger a fetch right now.

        The floor is keyed on the last **unproductive** refetch, not on the
        last fetch of any kind, and the difference is the whole point. Stamping
        every fetch — which is what this did first — meant a genuine key
        rotation arriving within seconds of a normal fetch was refused, so the
        floor defeated the rotation handling it was written to coexist with.
        A test caught it.

        Throttling only failures gives both properties: a rotated key is
        fetched immediately, every time, and a burst of junk `kid`s costs one
        fetch and then nothing.
        """
        with self._lock:
            if self._last_failure is None:
                return True
            return time.monotonic() - self._last_failure >= _MIN_REFETCH_INTERVAL_S

    def _fresh_key(self, kid: str) -> Any | None:
        """A cached key, but only while the cache is within its TTL."""
        with self._lock:
            if self._fetched_at is None:
                return None
            if time.monotonic() - self._fetched_at > CACHE_TTL_S:
                return None
            return self._keys.get(kid)

    def _refresh(self) -> None:
        """Fetch the key set and replace the cache."""
        keys = self._fetch()
        with self._lock:
            self._keys = keys
            self._fetched_at = time.monotonic()

    def _fetch(self) -> dict[str, Any]:
        """One HTTP GET, parsed into {kid: key}."""
        from jwt import PyJWK

        if not settings.auth_configured:
            raise JWKSUnavailable(
                "SUPABASE_URL is not set, so no token can be verified. "
                "See .env.example.")

        url = settings.jwks_url
        try:
            request = urllib.request.Request(
                url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_S) as response:
                document = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise JWKSUnavailable(f"could not fetch {url}: {e}") from e

        keys: dict[str, Any] = {}
        for entry in document.get("keys", []):
            kid = entry.get("kid")
            if not kid:
                # A key we cannot address is a key we can never select.
                continue
            try:
                keys[kid] = PyJWK(entry).key
            except Exception:                       # noqa: BLE001
                # One unsupported algorithm must not discard the whole set.
                continue

        if not keys:
            raise JWKSUnavailable(
                f"{url} returned no usable keys; the project may be configured "
                f"for symmetric (HS256) tokens, which this path does not verify")
        return keys


# One cache per process. Module-level, like the engine: a per-request cache
# would fetch the keys on every request, which is the thing being avoided.
cache = KeyCache()
