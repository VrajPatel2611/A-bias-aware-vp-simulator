# T-010 · Schema and migrations

| | |
|---|---|
| **Task** | T-010, BUILD_PLAN Phase 1 ⭐ — **first task of Phase 1** |
| **Status** | ✅ Complete — 11 September 2026 |
| **Branch** | `docs/decide-d4-d7` (stacked; T-010 is commit `96a795c`) |
| **Estimated** | 3 days |
| **Specification** | `DATA_MODEL` §4–7, §9.1 |
| **Behaviour change** | None to the running app. The database exists; nothing reads it yet |

---

## 1 · Summary

21 tables, 6 enum types, 11 triggers and 5 row-level security policies, created
by **16 hand-written Alembic migrations** and verified by **37 tests against a
real PostgreSQL 16 in a container**.

The tests are the point. A constraint that appears in `pg_constraint` but never
fires is decoration, so every one of them asserts the database **refuses**
something: two published versions of a case, a session owned by both a user and
an anonymous trial, an `UPDATE` on an append-only table, publishing without
clinical approval, one user reading another's rows.

293 → **330 tests.** Detector accuracy unchanged at 94%.

**Nothing in the application talks to the database yet.** Repositories are T-012;
the event log replaces the in-memory store at T-013.

---

## 2 · The problem

Session state is a dict in process memory (`infra/session_store.py`), which is
blocker **B1** in `TECH_SPEC`: it is lost on restart, cannot be shared between
workers, and limits the app to a single process. The Dockerfile's
`--workers 1` is a consequence, not a tuning choice.

Everything that fixes that — the event log (T-013), accounts (T-014), the
anonymous trial (T-015), assessment recomputed from events (T-016) — needs
tables to exist first. T-010 is the bottom of that stack.

---

## 3 · Definition of done

Verbatim from `BUILD_PLAN.md`:

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
| 1 | All tables created in order | **21 tables** via 001–016 · `test_every_specified_table_exists` |
| 2 | All three named constraints | 15 constraint tests, each asserting a rejection |
| 3 | Append-only triggers raise | 6 tests — append allowed, `UPDATE` and `DELETE` refused, on both tables |
| 4 | Publication gate blocks | 4 tests incl. a *rejecting* review not permitting publication |
| 5 | `downgrade base` → `upgrade head` | `test_downgrade_to_base_then_upgrade_again` |
| — | One test per constraint | **37 tests**, all asserting refusal rather than existence |

---

## 4 · What was built

```
alembic.ini                     hand-written migrations, not autogenerate
migrations/env.py               URL from DATABASE_URL, not from alembic.ini
migrations/versions/
  001_extensions       pgcrypto, citext, vector, pg_trgm + the auth stubs (§5.3)
  002_functions        set_updated_at, forbid_mutation
  003_enums            all 6 enum types, together
  004_profiles         profiles + updated_at trigger
  005_content_master   examinations, investigations, topic_lexicon, topic_phrases
  006_cases            cases, case_versions, clinical_reviews
  007_case_publish_gate  require_clinical_approval — must follow 006
  008_engine_versions  engine_versions
  009_sessions         sessions + owner_is_exclusive
  010_session_events   session_events + append-only trigger
  011_session_results  session_results
  012_feedback         feedback_texts
  013_commerce         subscriptions + one_active_sub_per_user
  014_progress         user_progress, user_case_history
  015_ops              llm_calls, leakage_flags, idempotency_keys, audit_log,
                       feature_flags
  016_rls              5 policies, RLS on 9 tables
nidan/infra/db/models.py        SQLAlchemy metadata (deliberately thin — §6.4)
tests/db/                       37 tests, real Postgres in a container
```

### 4.1 · The SQL is the specification's, not mine

`DATA_MODEL` §4–7 contains complete DDL. Rather than retype it — which invites
silent transcription drift from the contract — the SQL blocks were **extracted
programmatically** from the document and embedded in the migrations.

Each migration says so:

> *SQL is verbatim from the specification. Where they diverge, the specification
> is the contract and this file is the bug.*

### 4.2 · Why hand-written rather than autogenerate

`DATA_MODEL` §9.1 requires it, and the reason is concrete. Alembic's
autogenerate cannot express partial indexes, `CHECK` constraints, triggers or
RLS policies — and having failed to express them, it would **drop them on the
next revision** without comment. Every guarantee this task exists to create is
in exactly that category.

### 4.3 · Real Postgres, not SQLite

Every property under test is a PostgreSQL feature: partial unique indexes,
`plpgsql` triggers, row-level security, enum types. SQLite has none of them, so
a test there would pass while proving nothing.

The container starts once per session; each test runs in a transaction that is
rolled back. Tests neither wait for 16 migrations nor see each other's rows.

---

## 5 · Where we diverged from the specification

### 5.1 · 16 migrations, not 18

The task says `001..018`. Migrations **017 (seed_content)** and **018
(seed_engine)** insert rows — 27 examinations, 86 investigations, 40 topics, 523
phrases, and engine version 1.0.0. That is **T-011's acceptance criteria 1 and
2**, word for word.

T-010 creates the tables; T-011 fills them. Criterion 1 is about tables, and
tables are complete at 016.

### 5.2 · 21 tables, not 19

The task says "all 19 v1 tables". `DATA_MODEL` §4–7 defines **21**, and 21 were
created. The 19 appears to be a miscount in the task text.

### 5.3 · Two Supabase objects had to be stubbed

`profiles.id REFERENCES auth.users(id)` and every RLS policy calls `auth.uid()`.
Both are **Supabase's**, and neither exists in a plain Postgres container — so
without them there is no schema to migrate locally and no way to test RLS at
all.

Migration 001 creates both, guarded so they are a **no-op on real Supabase**:

```sql
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users (id UUID PRIMARY KEY, ...);
```

`auth.uid()` needed more care, because `CREATE FUNCTION` has no `IF NOT EXISTS`:

```sql
DO $do$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n
                 ON n.oid = p.pronamespace
                 WHERE n.nspname = 'auth' AND p.proname = 'uid') THEN
    CREATE FUNCTION auth.uid() RETURNS uuid AS $fn$
      SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid;
    $fn$ LANGUAGE sql STABLE;
  END IF;
END
$do$;
```

**Deliberately not `CREATE OR REPLACE`.** On real Supabase that would overwrite
their authentication function with this stub — a security incident, not a
convenience.

The body matches Supabase's own, which is what makes RLS testable locally:

```sql
SET LOCAL request.jwt.claim.sub = '<uuid>';
```

Without that, the policies could only ever have been verified in production.

### 5.4 · `set_updated_at` triggers are not in the spec's DDL

§2.7 states the rule — *"applied to every table carrying `updated_at`"* — but no
`CREATE TABLE` block wires it. Eight tables carry the column; eight triggers
were added. The specification states the intent and leaves the wiring to the
implementation, which is reasonable, but it means the DDL blocks are not
complete on their own.

### 5.5 · `models.py` is deliberately thin

The task lists it, and it exists, but it holds only `MetaData` with a naming
convention. **The migrations are the source of truth.** A full set of
SQLAlchemy models would duplicate 21 tables, and duplication drifts.

The models the repository layer needs are **T-012's** work, and the file's
docstring says a drift test should come with them.

---

## 6 · Problems hit

### 6.1 · `op.execute` reads a comment as a bind parameter

```
sqlalchemy.exc.StatementError: A value is required for bind parameter '0'
```

The spec's DDL documents a JSONB shape in a SQL comment:

```sql
-- {"anchoring":{"last10":0.2,"prev10":0.5},...}
```

SQLAlchemy parses `:0` and `:5` as named bind parameters — inside a comment, in
a `CREATE TABLE`. Raw DDL must reach the driver uninterpreted, so every
migration uses `op.get_bind().exec_driver_sql(...)` instead.

### 6.2 · …and then psycopg reads `%` as a placeholder

Switching drivers swapped one escaping problem for another:

```
psycopg.ProgrammingError: incomplete placeholder: '%';
if you want to use '%' as an operator you can double it up, i.e. use '%%'
```

Two occurrences, both `RAISE EXCEPTION` format specifiers:

```sql
RAISE EXCEPTION 'Table % is append-only', TG_TABLE_NAME;
```

Doubled to `%%`; psycopg unescapes before sending, so the stored function body
is unchanged. **The two problems have opposite fixes** — `op.execute` chokes on
`:`, `exec_driver_sql` chokes on `%` — which is worth knowing before adding a
migration containing either character.

### 6.3 · An edit that silently did nothing

Inserting the `auth.uid()` stub into migration 001 appeared to succeed and did
not. The edit matched on `op.execute(`, but 001 had already been converted to
`exec_driver_sql` — so the upgrade half never applied while the downgrade half,
which matched a different pattern, did.

Caught by the next run failing on `auth.uid() does not exist`. **A
string-replacement edit that finds nothing should be an error, not a silent
no-op** — the same class of mistake as the `sed` that missed an indented import
in T-001.

### 6.4 · 37 tests skipped, which looked like a failure

```
sssssssssssssssssssssssssssssssssssss   37 skipped
```

Docker Desktop was closed. The fixture skips rather than fails, which is
correct — a suite should not fail because of a missing local daemon — but a
wall of `s` reads as breakage.

**Worth knowing:** `pytest` without Docker gives 293 passed, 37 skipped. That is
healthy, not broken.

---

## 7 · Verification

```bash
pytest tests/db -q --no-cov      # 37 passed
pytest -q                        # 330 passed, coverage 99.63%
ruff check .                     # PASS
mypy nidan/domain --strict       # PASS
lint-imports                     # PASS
python validate_detectors.py     # PASS: 94.4%
```

Against a real container:

```
tables   (21)  audit_log, case_versions, cases, clinical_reviews,
               engine_versions, examinations, feature_flags, feedback_texts,
               idempotency_keys, investigations, leakage_flags, llm_calls,
               profiles, session_events, session_results, sessions,
               subscriptions, topic_lexicon, topic_phrases,
               user_case_history, user_progress
triggers (11)  2 append-only, 8 set_updated_at, 1 publication gate
policies ( 5)  own_profile, own_sessions, own_session_events,
               own_session_results, read_published_cases
RLS on   ( 9)  and case_versions, which needs it for the read policy
```

`alembic upgrade head` and `downgrade base` both succeed, repeatedly.

---

## 8 · What this changes for you

The schema is code. The tables are what happens when you run it somewhere.

```bash
docker compose up -d db          # the database
alembic upgrade head             # create every table
alembic downgrade base           # remove them again
docker compose exec db psql -U nidan -d nidan
```

Inside `psql`: `\dt` lists tables, `\d sessions` shows one in full. `\d
session_events` shows the append-only trigger — the guarantee, visible.

**Deploying to Supabase later is the same command pointed elsewhere:**

```bash
DATABASE_URL="postgresql://...supabase.co:5432/postgres" alembic upgrade head
```

That is the entire argument for migrations: one definition, applied identically
to a laptop, to CI's throwaway container, and to production.

---

## 9 · Known debt left behind

| Debt | Closed by |
|---|---|
| **Tables are empty.** No examinations, investigations, topics or engine version | **T-011** (migrations 017–018) |
| **`models.py` holds only metadata.** No table objects to query | **T-012**, which should add a drift test against a migrated database |
| **Nothing in the app reads the database** | T-012, T-013 |
| **RLS is tested via the local `auth.uid()` stub.** Behaviour on real Supabase is assumed, not observed | first Supabase deployment |
| **The `auth.users` stub is minimal** — id, email, created_at. Real Supabase has far more | — by design |
| **`docker-compose.yml` has no `name:`**, so the Compose project is still derived from the directory | unassigned, one line |
| **`alembic.ini` is not wired into CI.** Migrations are tested by `tests/db`, but CI never runs `upgrade head` against a fresh database as a deploy would | worth folding into T-012 |

---

## 10 · How to undo it

```bash
alembic downgrade base                      # if applied to a database
git revert 96a795c
```

The migrations are additive and the application does not read the database, so
reverting affects nothing that runs today.

---

## 11 · Next

**T-011 · Seed content and `openapi.yaml` skeleton** (2 days) — migrations
017–018, seeding the master lists from `cases.py`, plus the OpenAPI skeleton.

`BUILD_PLAN` marks it **sync point S-1**: it unblocks the frontend track, and
the plan says *"do not let this slip."*

It also migrates the 5 existing cases into `case_versions` as v1 drafts — the
first time clinical content lives in the database rather than in a 2,421-line
Python file, and the step that makes the case editor (T-021) possible.

---

*Written 12 September 2026 · Vraj Patel (202301408) · Yogesh Bagotia (202301114)*
