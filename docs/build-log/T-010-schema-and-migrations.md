# T-010 · Schema and migrations

| | |
|---|---|
| **Task** | T-010, BUILD_PLAN Phase 1 ⭐ |
| **Status** | ✅ Complete — 11 September 2026 |
| **Branch** | `docs/decide-d4-d7` (stacked on the decisions) |
| **Estimated** | 3 days · **actual: under a day** |
| **Specification** | `DATA_MODEL` §4–7, §9.1 |
| **Behaviour change** | None to the app — it does not read the database yet (T-012) |

---

## 1 · Summary

16 Alembic migrations creating **21 tables, 6 enum types, 11 triggers and 5 RLS
policies**, with a full `downgrade base` → `upgrade head` round-trip verified
against a real PostgreSQL 16 container.

**293 → 330 tests.** 37 of them are database tests, and every one asserts the
database *refuses* something rather than that a constraint merely exists in
`pg_constraint`.

The two that matter most:

- **Append-only is enforced by the database.** `UPDATE` or `DELETE` on
  `session_events` raises. That is what makes property P3 true — *the event log
  is the source of truth* (`ADR-0003`) — rather than a promise about
  application code.
- **Publishing without an approving clinical review is refused.** Not by the
  admin console (T-023), by a trigger.

---

## 2 · Definition of done

```
T-010 · Schema and migrations

Phase    1            Depends  T-005          Est  3 d      Owner  V
Files    nidan/infra/db/models.py, migrations/versions/001..018
Spec     DATA_MODEL §4–7, §9.1
Accept   1. All 19 v1 tables created by migrations 001–018 in order
         2. All constraints present incl. owner_is_exclusive,
            one_published_version_per_case, one_active_sub_per_user
         3. Append-only triggers on session_events and audit_log raise on UPDATE/DELETE
         4. require_clinical_approval trigger blocks publishing without an approving review
         5. `alembic downgrade base` then `upgrade head` succeeds on an empty database
Tests    testcontainers Postgres; one test per constraint asserting it actually rejects
```

| # | Criterion | Evidence |
|---|---|---|
| 1 | tables created in order | **21 tables** via 001–016 · `test_migrations.py` compares against the spec list both ways |
| 2 | named constraints present **and rejecting** | 15 tests. `owner_is_exclusive` CHECK; the other two are **partial unique indexes**, not constraints |
| 3 | append-only triggers raise | 7 tests — append allowed, `UPDATE` and `DELETE` refused, on both tables |
| 4 | publication gate blocks | 4 tests, including that a **rejecting** review does not permit publication |
| 5 | downgrade → upgrade round-trip | verified; asserts no tables survive the teardown |
| — | RLS actually denies | 7 tests, run **as a non-superuser** — see §5 |

---

## 3 · Where we diverged

**3.1 · Migrations 017–018 are not here.** They are seed data — 27 examinations,
86 investigations, 40 topics, 523 phrases, and engine version 1.0.0 — which is
**T-011's acceptance criteria verbatim**. T-010 creates the tables; T-011 fills
them. Criterion 1 names 001–018 because that is the full sequence in
`DATA_MODEL` §9.1, but rows are not tables.

**3.2 · The spec defines 21 tables, not 19.** Criterion 1 says "19 v1 tables".
Counting `DATA_MODEL` §4–7 gives 21. All 21 are created, and
`test_every_specified_table_exists` asserts the set matches **in both
directions** — a table created but not specified fails too.

**3.3 · `models.py` deliberately contains no table definitions.** It holds the
`MetaData` that `migrations/env.py` imports, and says why it is empty: defining
21 tables that nothing reads yet is 21 opportunities to disagree with the
migrations. T-012 adds what the repository layer actually queries, and a drift
test earns its place then.

---

## 4 · Two things Supabase provides that a container does not

`DATA_MODEL` is written against Supabase. Two of its assumptions do not exist in
plain PostgreSQL, and without them **the schema cannot be migrated or tested
locally at all**.

### 4.1 · `auth.users`

`profiles.id` references it. Migration 001 creates a minimal stub with
`CREATE TABLE IF NOT EXISTS`, so it is a no-op on real Supabase where the table
already exists and is far richer. It carries only what the foreign key needs.

### 4.2 · `auth.uid()` — the more important one

Every RLS policy in migration 016 is written against it. Without it, migration
016 fails outright.

It is created **only if absent**, via a `DO` block — deliberately *not*
`CREATE OR REPLACE`, which on real Supabase would overwrite their
implementation with ours. That would be a security incident, not a convenience.

The body matches Supabase's, reading `request.jwt.claim.sub`. **That is what
makes §5 possible**: RLS can be exercised locally by setting the claim. Without
it, the policies protecting every user's data would first be tested in
production.

---

## 5 · The RLS tests run as a non-superuser

Worth stating because it is the easiest way to write an RLS test that proves
nothing.

**PostgreSQL exempts superusers and table owners from RLS.** The migration user
owns every table, so tests run on that connection would see all rows, pass
happily, and demonstrate nothing.

`tests/db/test_rls.py` therefore creates a separate unprivileged role, grants
it table access, and connects as that role. Only then does "another user's rows
are invisible" mean anything.

It also tests the case that is easiest to get wrong: `session_events` has no
`user_id` of its own, and its policy reaches through the parent session.

---

## 6 · Problems hit

### 6.1 · `op.execute` reads `:0.2` in a comment as a bind parameter

```
InvalidRequestError: A value is required for bind parameter '0'
```

The spec's DDL documents a JSONB shape in a comment — `{"last10":0.2}` — and
SQLAlchemy's `op.execute` treats `:0` as a named parameter.

Fixed by using `op.get_bind().exec_driver_sql()`, which passes raw SQL to the
driver uninterpreted. That is the right primitive for hand-written DDL anyway.

### 6.2 · …which then broke on `%`

```
psycopg.ProgrammingError: incomplete placeholder: '%'; if you want to use '%'
as an operator you can double it up, i.e. use '%%'
```

`exec_driver_sql` avoids `:`, and psycopg then reads `%` as *its* placeholder.
Two occurrences, both `RAISE EXCEPTION` format specifiers. Doubled to `%%`,
which the driver unescapes, so the stored function bodies are unchanged.

**The pair is worth remembering:** `op.execute` chokes on `:`,
`exec_driver_sql` chokes on `%`, and hand-written DDL contains both.

### 6.3 · Test fixtures guessed column names

`column "correct_diagnosis" of relation "case_versions" does not exist`. Fixed
by querying `information_schema` for the NOT NULL columns without defaults and
building the fixture from that, rather than from memory of the spec.

### 6.4 · The RLS tests silently leaked rows into every later test

The subtlest one. RLS tests must `commit()` so a second connection can see
their rows — which ends the transaction the fixture was relying on to roll
everything back.

It surfaced only as `SAWarning: transaction already deassociated`. The tests
passed. But every row an RLS test created stayed in the database for the rest
of the session, and the eventual failure would have appeared in an unrelated
test.

The fixture now truncates when the transaction is gone and rolls back when it
is not. The check is `conn.in_transaction()`, not `txn.is_active` — after a
commit the transaction object is deassociated but still reports itself active.

---

## 7 · Verification

```
ruff                PASS      mypy (domain strict)   PASS
import-linter       PASS      gitleaks               PASS
pytest              330 passed (was 293)
validation          51/54 = 94%, unchanged
```

```
tables   (21): audit_log, case_versions, cases, clinical_reviews, engine_versions,
               examinations, feature_flags, feedback_texts, idempotency_keys,
               investigations, leakage_flags, llm_calls, profiles, session_events,
               session_results, sessions, subscriptions, topic_lexicon,
               topic_phrases, user_case_history, user_progress
triggers (11): 2 append-only, 8 set_updated_at, 1 publication gate
policies ( 5): own_profile, own_sessions, own_session_events,
               own_session_results, read_published_cases
```

A new CI job, **Database schema**, runs these on every pull request.

---

## 8 · What this changes for you

The app does not use the database yet — T-012 builds the repository layer. But
the schema is now real and you can look at it:

```bash
docker compose up -d db
DATABASE_URL=postgresql://nidan:nidan_local_dev_only@localhost:5433/nidan \
  alembic upgrade head
docker compose exec db psql -U nidan -d nidan
```

`\dt` lists the tables, `\d sessions` describes one, `\q` quits.

**Port 5433 on Vraj's machine**, 5432 elsewhere — see `.env`.

Two commands worth knowing:

```bash
alembic upgrade head      # apply everything
alembic downgrade base    # tear it all down
```

---

## 9 · Known debt left behind

| Debt | Closed by |
|---|---|
| **`models.py` has no table definitions.** Deliberate — see §3.3 | **T-012** |
| **No seed content.** The master lists and engine version are empty | **T-011** |
| **`set_updated_at` triggers were not in the spec's DDL.** §2.7 states the rule; the per-table wiring was added here. `DATA_MODEL` should show it | unassigned, small |
| **The `auth` stubs are untested against real Supabase.** `IF NOT EXISTS` and the `DO` guard are correct by inspection, not by observation | first Supabase deploy |
| **No index-usage verification.** 29 indexes are created; nothing confirms a query plan uses them | Phase 5, or first slow query |
| **`test_downgrade_to_base_then_upgrade_again` is marked `slow`** but not excluded anywhere, so it runs every time. It is 2s; revisit if the suite slows | — |

---

## 10 · How to undo it

```bash
rm -rf migrations alembic.ini tests/db nidan/infra/db
git checkout HEAD -- pyproject.toml requirements.txt .github/workflows/ci.yml \
                     docker-compose.yml
```

Nothing else depends on it yet.

---

## 11 · Next

**T-011 · Seed content and `openapi.yaml` skeleton** (2 days) — migrations 017
and 018, seeding 27 examinations, 86 investigations, 40 topics and 523 phrases
**from `cases.py`**, plus engine version 1.0.0.

`BUILD_PLAN` marks it **sync point S-1**: it unblocks the frontend track, and
the note says *"do not let this slip."*

---

*Written 11 September 2026 · Vraj Patel (202301408) · Yogesh Bagotia (202301114)*
