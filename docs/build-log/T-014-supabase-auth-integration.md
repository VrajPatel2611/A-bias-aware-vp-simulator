# T-014 · Supabase Auth integration

| | |
|---|---|
| **Task** | T-014, BUILD_PLAN Phase 1 |
| **Status** | ✅ Complete — 13 September 2026 |
| **Branch** | `feat/supabase-auth` |
| **Estimated** | 2 days |
| **Specification** | `ADR-0002` · `API_CONTRACT` §2.2, §3 · `SECURITY_SPEC` L1 |
| **Behaviour change** | The `/v1` JSON API exists, with two working endpoints. The prototype is unaffected |

---

## 1 · Summary

Nidan can now tell who someone is, without ever seeing a password.

```
infra/auth/jwks.py     Supabase's signing keys, cached 10 min, rotation handled
infra/auth/tokens.py   verification — signature AND aud AND iss
api/auth.py            @require_auth · @require_tier('pro')
api/v1.py              POST /v1/me · GET /v1/me
```

**35 new tests.** 468 pass.

This is also the first code that uses what T-012 built: `repo_scope(AuthenticatedUser(...))` existed, fully tested, with no caller. Every authenticated request now opens a transaction as that user, so Row-Level Security decides what comes back in production and not only in tests.

---

## 2 · Definition of done

| # | Acceptance criterion | Met by |
|---|---|---|
| 1 | JWT verified against JWKS, cached 10 min | `infra/auth/jwks.py` · `test_the_keys_are_fetched_once_and_then_cached` |
| 2 | `@require_auth` and `@require_tier('pro')` | `api/auth.py` · 5 tier tests |
| 3 | Expired token → 401 `token_expired` | `test_an_expired_token_says_so_specifically` |
| 4 | Profile created on `POST /me`, idempotent | `test_creating_a_profile_is_idempotent` |
| 5 | Backend never handles a password | No password is read anywhere; `test_the_backend_never_sees_a_password` |

---

## 3 · What was built

### 3.1 Verifying a signature is not verifying a token

The check that matters most is the one easiest to leave out.

A signature proves *some* Supabase project issued the token. Without `aud` and `iss`, a valid token from **anyone else's** project — a free account takes a minute to create — authenticates here as whatever `sub` it names. PyJWT checks `aud` only if you pass `audience=`, and `iss` only if you pass `issuer=`. The vulnerability is one missing keyword argument, and it leaves no trace: every legitimate token still works.

```python
claims = jwt.decode(
    token, key=key,
    algorithms=list(ALLOWED_ALGORITHMS),   # asymmetric only
    audience=settings.SUPABASE_JWT_AUDIENCE,
    issuer=settings.jwt_issuer,
    options={"require": ["exp", "sub", "aud", "iss"], ...},
)
```

`require` matters as much as the values: a token that simply *omits* `aud` must fail as surely as one carrying the wrong value, or the check is bypassed by leaving the claim out.

**`ALLOWED_ALGORITHMS` excludes HS256**, and that is not tidiness. In the algorithm-confusion attack an attacker signs a token with HMAC using the *public* key as the secret, and a library that trusts the token's own `alg` header agrees. The token never decides how it is checked.

The JWKS URL and the expected issuer are both **derived from `SUPABASE_URL`** rather than configured separately. Two settings that must agree are two settings that can disagree, and that failure would be a project verifying tokens against another project's keys.

### 3.2 The 10-minute cache, and the trap inside it

`API_CONTRACT` §2.2 asks for a 10-minute TTL. A cache that refreshes only on expiry means a **key rotation breaks every request until the TTL runs out** — every user logged out at once, then fixed before anyone can investigate.

So an unknown `kid` forces an immediate refetch. That opens the opposite failure: a burst of tokens carrying bogus `kid`s becomes a burst of requests to Supabase — a denial of service anyone can trigger from outside, against a dependency we do not control. Hence a floor on refetches.

**The first version of that floor defeated the rotation handling it was meant to coexist with** — see §5.

### 3.3 The tier comes from the profile, not the token

```python
@require_tier('pro')
```

reads `subscription_tier` from `profiles`, not from a claim. A JWT is issued at sign-in and lives about an hour; a subscription can be cancelled, expire, or be upgraded well inside that window. Trusting the claim gives a cancelled subscriber an hour of paid access, and makes someone who has just paid wait for one — and the second complaint arrives within minutes of taking their money.

The cost is one indexed read, inside a transaction the request opens anyway. `test_a_pro_user_is_allowed` upgrades the subscription in the database **without reissuing the token**, which is exactly the case a claims-based check gets wrong.

### 3.4 Three different failures, three different answers

| Situation | Status | Code |
|---|---|---|
| No token | 401 | `unauthenticated` |
| Expired | 401 | `token_expired` |
| Bad signature, wrong `aud`, wrong `iss` | 401 | `unauthenticated` |
| Authenticated, free tier, pro route | 403 | `pro_required` |
| **Key server unreachable** | **503** | **`service_unavailable`** |

The last row is a new error code, added to `openapi.yaml` in this commit. It matters: a 503 says *we cannot check your credentials*, where a 401 says *your credentials are wrong*. Answering 401 during a key-server outage would send every client into a refresh loop against the outage, turning a blip into a stampede.

The rejection message never says **which** check failed. "Wrong audience" tells someone probing exactly which field to change next.

### 3.5 `POST /v1/me`

Idempotent, because clients retry and Supabase replays webhooks. Most of it already existed: `ProfileRepository.ensure()` was written in T-012 with `ON CONFLICT DO NOTHING`, precisely so two concurrent first requests both succeed instead of the second hitting a primary-key violation.

201 on creation, 200 on a repeat. Both are success — the criterion is idempotency, not a fixed status — and the difference tells a client whether onboarding still needs showing.

The response is built **field by field**, never by dumping the row. A `SELECT *` reaching the client is how `research_pid` — the pseudonym that keeps published analyses unlinkable — ends up in a response beside an email, which `DATA_MODEL` §4.1 says must never happen. There is a test for its absence.

---

## 4 · Where we diverged from the specification

**The Supabase region did not block this.** I had said it would. Reading the spec properly, verification is computation over a token and a public key: none of it needs a project to exist. `tests/fakes/auth.py` mints tokens with a throwaway RSA key and serves the public half as a JWKS endpoint would. What still needs a real project is end-to-end signup — so the region blocks **deployment**, not this task. It should be settled before T-015, where a real account first has to exist.

**`PATCH` and `DELETE /me` are still 501.** Profile editing is routine; account deletion is not — `DATA_MODEL` §10.2 retains session results and the research pseudonym so published analyses stay reproducible, and the deletion screen must say so. That deserves its own task rather than a footnote in this one.

**`anonymous_id` is accepted and refused with a 422.** T-015 owns the 30-day claim window. Silently succeeding while claiming nothing would tell a learner their trial was saved when it was not.

**A new error code, `service_unavailable`.** Reasoned above; added to the frozen enum with a comment explaining why it is not a 401.

**`admin` is not implemented.** `API_CONTRACT` §2.2 lists it, but it needs a role claim and the admin console is Phase 2 (T-021+). Inventing a role scheme now would mean designing it without its first user.

---

## 5 · The rate limit that defeated the rotation fix

Written, and then caught by its own test within the hour.

The cache has two competing requirements. An unknown `kid` must trigger an immediate refetch, or a key rotation is a ten-minute outage. And refetches must be throttled, or junk `kid`s become a denial of service against Supabase.

My first floor stamped a timer on **every** fetch, including successful ones. So:

```
verify(token)              → fetch #1, stamps the floor
… rotation happens …
verify(rotated token)      → unknown kid → throttled → 401
```

`test_a_rotated_key_is_fetched_immediately_not_after_the_ttl` failed on exactly that. The throttle had swallowed the rotation handling it was written to coexist with — a five-second outage rather than ten minutes, but for the same reason and by my own hand.

The fix is to throttle only refetches that **failed to produce the requested key**:

- a rotated `kid` is fetched immediately, every time, because that fetch succeeds;
- twenty-five junk `kid`s cost one fetch and then nothing.

Both are now tested, in both directions. The general shape is worth keeping: **two safety mechanisms can each be correct and still cancel each other**, and only a test that exercises them together will say so.

---

## 6 · Other things the tests caught

**A guard test caught undocumented configuration.** `test_every_declared_field_appears_in_env_example` failed the moment `SUPABASE_URL` and `SUPABASE_JWT_AUDIENCE` were added — a T-006 guard doing precisely its job two tasks later.

**The 501 test had become wrong rather than merely stale.** T-011 asserted *every* operation declares 501, which was true when none worked. It now asserts an equivalence: implemented operations must **not** advertise 501, and stubs must. Implementation is read from the app's own routing table rather than a hand-kept list, so it cannot go stale the same way. Verified in both directions.

**One of my own tests was written confusingly enough to be wrong** — a `{...} if False else {...}` expression that tested one claim twice. Rewritten as two plain assertions.

**Every security guard was probed by breaking it.** Removing `audience=` fails 2 tests; adding HS256 to the allowed algorithms fails 1; both were checked rather than assumed.

---

## 7 · Verification

```
pytest                          468 passed        (was 433)
pytest tests/db -q --no-cov     121 passed        (was 103)
ruff check .                    All checks passed
mypy nidan/domain --strict      Success: no issues found in 12 source files
lint-imports                    2 contracts kept, 0 broken
```

| File | Tests | Defends |
|---|---|---|
| `tests/test_auth.py` | 17 | verification, the cache, rotation — **no Docker, no Supabase** |
| `tests/db/test_auth_routes.py` | 18 | status codes, error codes, tier gating, RLS through a real request |

That first row is deliberate. `tests/db` skips without Docker, so the security-critical half of this task is checked on every run — including the runs where nobody notices the rest was skipped.

---

## 8 · What this changes for you

**Nothing about running the prototype.** Consultations are still anonymous trial sessions (`PRD` FR-2) and need no login. `SUPABASE_URL` may stay unset.

**The `/v1` API now exists** with `POST /me` and `GET /me`. Everything else still answers 501, which is what lets the frontend build against the contract.

**To try it against a real project**, set `SUPABASE_URL` in `.env` — the JWKS URL and issuer are derived from it. Confirm the project issues **asymmetric** (RS256/ES256) tokens with a JWKS endpoint; older Supabase projects sign HS256 with a shared secret, which this path deliberately refuses.

---

## 9 · Known debt left behind

**No refresh-token handling, by design.** `API_CONTRACT` §3.3 puts it client-side in the Supabase SDK; our API only ever validates. `token_expired` is the entire server-side contribution.

**`admin` is unimplemented**, as above.

**The JWKS cache is per process.** Each gunicorn worker keeps its own, so a rotation costs one fetch per worker. With two workers that is not worth shared state.

**`PATCH`/`DELETE /me` and `/me/export` remain 501.**

---

## 10 · How to undo it

```bash
git revert <commit>
```

No migration, no schema change. Unsetting `SUPABASE_URL` disables authentication without removing the code: the `/v1` endpoints answer 503, and the prototype is unaffected.

---

## 11 · Next

**T-015 · Anonymous trial sessions** (1.5 days) — the task that joins the two halves. Every consultation since T-013 writes an `anonymous_id`; T-015 claims it into a real account at signup, within a 30-day window, and enforces one trial per browser. It depends on T-013 and T-014, and it is the point at which **the Supabase region must be settled** (`SECURITY_SPEC` S-4), because a real account has to live somewhere.

`UX_SPEC` already specifies the moment down to the copy: *"Your case result will be saved to your new account."*
