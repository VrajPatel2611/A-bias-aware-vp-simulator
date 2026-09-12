# T-012 · Repository layer and tenant scoping

| | |
|---|---|
| **Task** | T-012, BUILD_PLAN Phase 1 |
| **Status** | ✅ Complete — 12 September 2026 |
| **Branch** | `feat/repository-layer` |
| **Estimated** | 2 days |
| **Specification** | `DATA_MODEL` §10.1 · `SECURITY_SPEC` L3 · new `ADR-0016` |
| **Behaviour change** | None visible. The application can now reach the database; no route uses it yet |

---

## 1 · Summary

The first code that queries the database, and the boundary that makes a
tenant-isolation bug structurally impossible rather than merely absent.

```
migration 020         two roles: nidan_app (RLS applies), nidan_service (bypasses)
infra/db/actor.py     three actor types — who is asking
infra/db/engine.py    the only connection pool, private to infra/db
infra/db/repositories/  the only place SQL is written
  base.py               repo_scope(actor): SET LOCAL ROLE + set_config
  anonymous.py          the one path where RLS is off — four methods
```

Every transaction now opens with two statements:

```sql
SET LOCAL ROLE nidan_app;
SELECT set_config('request.jwt.claim.sub', :user_id, true);
```

**40 new tests.** 396 pass, 99.6 % coverage on the domain.

---

## 2 · Definition of done

| # | Acceptance criterion | Met by |
|---|---|---|
| 1 | Repository base requires an actor context; no query bypasses it | `tests/test_db_access.py` — four AST checks over the whole package |
| 2 | RLS policies applied and tested — a second user's rows are invisible | `tests/db/test_repository_scope.py` — 18 tests through the real pool |
| 3 | Anonymous-session path isolated and separately tested | `nidan/infra/db/repositories/anonymous.py` + `tests/db/test_anonymous_scope.py` |

---

## 3 · What was built

### 3.1 The problem this task actually solves

Migration 016 enabled Row-Level Security and wrote six policies. T-010 proved
they were written correctly, using a purpose-built non-superuser role called
`rls_tester`, with this comment:

> Postgres exempts superusers and table owners from RLS, so running these
> assertions as the migration user would pass while proving nothing at all.

That was right, and it left a hole the schema alone cannot close. **The
application also has to not be a superuser or the table owner** — and the
direct connection string Supabase issues authenticates as `postgres`, a
superuser, which is the obvious thing to paste into `DATABASE_URL`.

Had T-012 simply reused that connection, every policy would have been silently
inert. `pg_policies` would still list all six. Every T-010 test would still
pass. The first sign of trouble would have been one learner seeing another's
consultation.

### 3.2 Two roles, assumed per transaction (`ADR-0016`)

Migration 020 creates two `NOLOGIN` roles:

| Role | RLS | Used for |
|---|---|---|
| `nidan_app` | **applies** | every authenticated request |
| `nidan_service` | bypassed | the anonymous-trial path, jobs, the case editor |

They are assumed per *transaction*, not per connection. That choice does three
things at once:

- one connection pool serves both roles;
- a superuser connection is **demoted for the duration of the statement**, so
  the policies apply even when the credentials would otherwise be exempt;
- no password is added to a migration, because a `NOLOGIN` role has none.

Grants are enumerated, not wholesale. The application gets `SELECT` on clinical
content and nothing more — a bug in a request handler cannot rewrite a reviewed
case even if it gets as far as issuing the `UPDATE`. There is a test for that.

### 3.3 `SET LOCAL`, and why the word matters

```python
# WRONG — persists for the life of the connection, which is pooled
conn.execute(text(f"SET request.jwt.claim.sub = '{user_id}'"))

# RIGHT — transaction-scoped, and parameterised
conn.execute(
    text("SELECT set_config('request.jwt.claim.sub', :uid, true)"),
    {"uid": str(actor.user_id)})
```

Two separate failures are avoided there.

**Plain `SET` outlives the transaction.** It is transactional — a rollback
reverts it — but a *commit* makes it stick for the life of the connection, and
SQLAlchemy's pool reset is a `ROLLBACK`, which does not undo it. The connection
then carries the previous user's role and identity to whoever borrows it next.

**An f-string there is SQL injection through the authentication path.** That
value comes from a JWT: the one input an attacker most directly influences.
`SET ROLE` genuinely cannot take a bind parameter, so the role name is
interpolated — guarded by a frozenset of exactly two literals in `actor.py`,
which is why `assume()` refuses an unrecognised role rather than trusting the
caller.

### 3.4 Three actor types, not one with an optional field

```python
AuthenticatedUser(user_id: UUID)   → nidan_app,     auth.uid() = user_id
AnonymousVisitor(anonymous_id: str) → nidan_service, auth.uid() = NULL
ServiceActor(reason: str)           → nidan_service, auth.uid() = NULL
```

An optional `user_id` invites `if actor.user_id:` at the call site and a
forgotten `else`. Three types make the anonymous path unreachable by accident,
because it does not type-check.

`ServiceActor` requires a written reason of at least eight characters. The
database never reads it. It exists so that every place the safety net is
switched off is greppable and explains itself, and so that the constructor is
not one anybody reaches for casually.

### 3.5 The anonymous path — `DATA_MODEL` §10.1's exception

A trial visitor has no `auth.uid()`, so `own_sessions` (`user_id = auth.uid()`)
evaluates NULL and denies the visitor their own session. The spec accepts that
and names the compensating control:

> served through a service-role connection with an explicit `anonymous_id`
> filter in the query, and that code path is short, isolated, and separately
> tested.

All three words are implemented rather than asserted:

- **short** — four methods, none of which writes its own `WHERE`. The filter
  lives in `_scoped()`, so omitting it means writing a query that does not
  compile. A test additionally asserts that every SQL literal in the file
  mentions `anonymous_id`.
- **isolated** — `anonymous_scope` yields sessions and read-only cases and
  nothing else. `repo_scope` *refuses* an `AnonymousVisitor`, because if the
  general repositories were reachable from the trial path, the correctness of
  that filter would become a property of every query anyone writes from now on
  rather than of one file.
- **separately tested** — `tests/db/test_anonymous_scope.py`, nine tests.

### 3.6 Criterion 1 made structural

"No query bypasses it" is not "queries should use the repository". A convention
is something you can follow, which means it is something you can forget. So it
is checked the way `test_layering.py` checks ADR-0009 — by reading the source:

1. `create_engine` appears in exactly one module.
2. Nothing outside `nidan.infra.db` imports it (also an import-linter contract,
   so CI enforces it too).
3. SQL literals appear only in `repositories/`.
4. Every SQL literal in `anonymous.py` filters `anonymous_id`.

---

## 4 · Where we diverged from the specification

**`BUILD_PLAN` cites `TECH_SPEC` §4.1, which is the assessment engine's
`assess()` interface — not data access.** There is no written data-access spec;
§4.1 is about `EngineVersion` and thresholds. The design decisions were
therefore new, and are recorded in `ADR-0016` rather than left implicit in the
code.

**No SQLAlchemy `Table` objects were added to `models.py`.** That module
reserved the right for T-012 to add them and diff them against a migrated
database. The repositories turned out to use textual SQL, which settles it the
other way: those objects would be read by nothing and would exist only to be
compared — a second copy of the schema, the exact outcome `models.py` was
written to avoid.

The drift check still exists, in the form the code actually takes.
`test_every_repository_query_still_matches_the_schema` executes every public
repository method against a real migrated database, so a renamed or dropped
column fails the build rather than the first request that touches it. That
tests the SQL that ships, which a metadata diff would not have.
`models.py` now records the reversal and why.

---

## 5 · The test that passed for the wrong reason

The most important test in this task was written backwards first, and finding
out took a deliberate attempt to break it.

The original read: *user A creates a session, the pool hands the same physical
connection to user B, assert B cannot see it.* It passed. Then it was run
against a deliberately broken `assume()` using plain `SET` and
`set_config(..., false)` — the exact bug it existed to catch.

**It still passed.**

The reason is real and worth keeping: `assume()` runs at the *start of every
scope*, so it overwrites the stale role and claim before any query sees them.
The leak is genuinely there — the connection sits in the pool carrying the last
user's identity — but nothing inside a scope can observe it.

That is far too thin a thread to hang tenant isolation on. It holds only while
no code ever touches a pooled connection outside a scope, and it fails
silently, in production, under load, the first time one does.

So the test was rewritten to assert the durable property instead: **a
connection returns to the pool carrying no identity.**

```python
with repo_scope(AuthenticatedUser(alice)) as db:
    raw_in_scope = id(db.conn.connection.dbapi_connection)
    db.sessions.create(cv)

with get_engine().connect() as conn:          # same physical connection
    role  = conn.execute(sa.text("SELECT current_user")).scalar()
    claim = conn.execute(sa.text(
        "SELECT current_setting('request.jwt.claim.sub', true)")).scalar()

assert raw_in_scope == id(conn.connection.dbapi_connection)
assert role != "nidan_app"
assert not claim
```

Re-run against the broken version, this one fails, naming the problem:

```
AssertionError: SET ROLE outlived the transaction: the next borrower of
this connection inherits the previous request's role
```

The weaker end-to-end version was kept alongside it, labelled as weaker, because
it is the sentence the acceptance criterion is written in and it is worth being
able to point at.

**The general lesson, which is the same one T-011 recorded in a different
costume:** a test that cannot fail is indistinguishable from a test that passes.
Every guard in this task was therefore probed by breaking the thing it guards:

| Guard broken | Tests that caught it |
|---|---|
| `SET LOCAL ROLE` removed entirely | 8 |
| `SET LOCAL` → `SET` | 1 (after the rewrite; **0 before**) |
| `anonymous_id` filter removed | 3 |
| A module opening its own connection | 3 |

---

## 6 · Other problems hit

**The fixture teardown truncated too few tables.** `TRUNCATE ... sessions`
failed with *"cannot truncate a table referenced in a foreign key constraint —
`llm_calls` references `sessions`"*. All 13 assertions had passed; only the
cleanup broke. Fixed by reusing the existing `_DATA_TABLES` list rather than
maintaining a second one — a second list is how the T-010 bug happened, and it
would have drifted the same way.

Deliberately still without `CASCADE`, for the reason T-011 recorded: cascade
propagates *outward*, to every table holding a foreign key *into* the listed
ones, and `cases.created_by` references `profiles`.

**`consent_recorded_together`.** Writing a profile with `consent_research=True`
violated a CHECK constraint requiring `consent_version` *and* `consent_at`. The
fix was not to add `consent_at` to the caller's allow-list but to stamp it in
the repository: it records when the user actually agreed, and a caller that can
choose it can backdate it. `ensure()` now also refuses consent without a
version — consent to an unnamed document is not consent.

**`professional_role: "student"` is not a valid enum label.** It is
`medical_student`. Caught by the drift test on its first run, which is exactly
the job that test exists to do.

**Two `assert` statements in shipping code.** `python -O` strips them, and both
carried real guarantees — one was the type guard keeping a non-visitor actor
away from queries whose only tenant filter is the value it returns. Replaced
with explicit raises.

---

## 7 · Verification

```
pytest                          396 passed        (was 356)
pytest tests/db -q --no-cov      81 passed        (was 54)
ruff check .                    All checks passed
mypy nidan/domain --strict      Success: no issues found in 10 source files
lint-imports                    2 contracts kept, 0 broken
coverage (domain)               99.63%
```

New tests, by what they defend:

| File | Tests | Defends |
|---|---|---|
| `tests/db/test_repository_scope.py` | 18 | criterion 2 — the policies deny the application |
| `tests/db/test_anonymous_scope.py` | 9 | criterion 3 — the path RLS cannot protect |
| `tests/test_db_access.py` | 4 | criterion 1 — structurally, over the whole package |
| `tests/test_db_actor.py` | 9 | the actor guards, with no Docker needed |

That last file exists because `tests/db/` **skips** when Docker is unavailable —
a normal state on a laptop and a possible one in CI. Without it, the actor
guards would be untested on exactly the runs where nobody noticed.

---

## 8 · What this changes for you

Nothing about running the app changes; no route uses the database yet.

What changes is how database code must now be written:

```python
from nidan.infra.db.repositories import repo_scope, AuthenticatedUser

with repo_scope(AuthenticatedUser(user_id)) as db:
    case    = db.cases.by_slug("chest-pain-gerd")
    session = db.sessions.create(case["id"], confidence_pre=3)
```

Three rules follow, and all three are enforced rather than requested:

1. **Never open a connection outside `infra/db`.** `tests/test_db_access.py`
   and an import-linter contract both fail the build.
2. **Never write SQL outside `repositories/`.** Same test.
3. **Do not add a `WHERE user_id = ...` to a scoped query.** The policy does it.
   Adding it by hand makes the test that checks the policy fires vacuous — it
   would pass whether or not RLS was working.

`docs/process/COMMANDS.md` §6a is new and covers the database commands,
including why a `psql` prompt is useless for checking isolation.

---

## 9 · Known debt left behind

**Session creation has a benign race.** `sequence_index` is `max + 1`, so two
genuinely concurrent starts collide. The partial unique index turns that into a
failed `INSERT` rather than two sessions numbered 4 — correct, but not graceful.
T-013 owns the retry, along with the identical problem on `session_events.seq`.

**Migration 020 grants role membership to `CURRENT_USER`,** so a local
`docker compose` stack works unconfigured. A production deployment should grant
it to the application's own login user instead. Noted in the ADR's consequences.

**The anonymous path is protected by application code alone.** `ADR-0016`
records the rejected alternative — extending RLS to cover anonymous sessions via
a second session variable — as worth revisiting at T-015, when a trial's shape
is actually defined.

**Repository reads return row mappings, not domain objects.** Deliberate: T-013
makes the session an event-sourced aggregate and owns that type. Inventing one
here would mean building it twice.

---

## 10 · How to undo it

```bash
alembic downgrade 019          # drops both roles
git revert <commit>
```

The migration's `downgrade` uses `DROP OWNED BY` before `DROP ROLE`, because
`DROP ROLE` refuses while any privilege anywhere still references it and the
error names the database rather than the grant.

---

## 11 · Next

**T-013 · Event-sourced session state** ⭐ (3 days) — deletes `SESSION_STORE`
entirely, appends an event before every response, and makes killing the process
mid-consultation lose nothing. It depends on this task and is the one that makes
`ADR-0003` real.

T-014 (Supabase Auth) and T-015 (anonymous trials) also unblock from here. T-015
is where the `anonymous_id` filter written in this task first carries real
traffic.
