# T-011 · Seed content and `openapi.yaml` skeleton

| | |
|---|---|
| **Task** | T-011, BUILD_PLAN Phase 1 ⭐ — **sync point S-1** |
| **Status** | ✅ Complete — 12 September 2026 |
| **Branch** | `feat/seed-content-and-openapi` |
| **Estimated** | 2 days |
| **Specification** | `DATA_MODEL` §9.2 · `API_CONTRACT` |
| **Behaviour change** | None to the running app. The database now holds content; nothing reads it yet |

---

## 1 · Summary

Three migrations fill the tables T-010 created, and `openapi.yaml` declares the
whole v1 API.

```
017   27 examinations · 86 investigations · 40 topics · 523 phrases
018   engine version 1.0.0 with the current detector thresholds
019   the 5 clinical cases as case_versions v1, status DRAFT
openapi.yaml   18 paths · 22 operations · 14 schemas · 28 error codes
```

**Migration 019 is the one that matters.** Clinical content no longer lives only
inside a 2,421-line Python file that only a programmer can read — which was the
thing blocking the two clinician reviewers. It is the first step of
T-021 → T-023 → ten reviewed cases → launch.

**`openapi.yaml` is why the plan calls this a sync point.** Yogesh can now
generate a typed client and build screens against a mock, instead of idling
through the rest of Phase 1.

330 → **356 tests**. Detector accuracy unchanged at 94%.

---

## 2 · Definition of done

```
T-011 · Seed content and `openapi.yaml` skeleton ⭐ (sync point S-1)

Phase    1            Depends  T-010          Est  2 d      Owner  V
Files    migrations/017,018, openapi.yaml
Spec     DATA_MODEL §9.2 · API_CONTRACT
Accept   1. 27 examinations, 86 investigations, 40 topics, 523 phrases seeded from cases.py
         2. Engine version 1.0.0 seeded with current thresholds, is_current=true
         3. 5 existing cases migrated as case_versions v1, status='draft'
         4. openapi.yaml committed with all v1 paths and schemas (may return 501)
Note     Unblocks the frontend track. Do not let this slip.
```

| # | Criterion | Evidence |
|---|---|---|
| 1 | master lists seeded | all four counts exact · 8 tests compare **contents**, not just counts |
| 2 | engine 1.0.0, `is_current` | seeded · a drift test ties it to `bias.py` |
| 3 | 5 cases as v1 draft | seeded · a test asserts the publication gate still refuses them |
| 4 | `openapi.yaml` with all paths | 18 paths, every operation declaring 501 · 9 contract tests |

**Every count in `DATA_MODEL` §9.2 was checked against `cases.py` rather than
trusted** — 27, 86, 40, 523, 5, all exact. Worth doing: T-010's task text
claimed 19 tables where the spec defined 21.

---

## 3 · What was built

### 3.1 · The seed migrations are generated, not written

`scripts/generate_seed_migration.py` and `generate_case_migration.py` read
`cases.py` and emit migrations 017 and 019.

**Why.** 523 phrases transcribed by hand would contain mistakes nobody would
ever find. A phrase that silently never matches looks exactly like a learner who
never asked about that topic — it would quietly depress coverage scores for
everyone, and there is no test that could distinguish it from real behaviour.

They are also re-runnable. Until T-021 gives clinicians an editor, `cases.py`
remains where content is authored, so this is a bridge rather than a one-off
import.

### 3.2 · Cases enter as draft — including the pilot's

`DATA_MODEL` §9.2 is explicit:

> *"The 5 migrated cases enter as `draft`, not `published`. They must pass
> clinical review before going live (FR-12.5) — including the ones that already
> ran in the pilot. Publishing them without review would make the trigger a
> formality."*

Implemented, and `test_the_publication_gate_still_refuses_these_cases` asserts
the trigger from migration 007 treats them like any other draft.

### 3.3 · The engine-version drift guard

`engine_versions.thresholds` records what a stored score *means*. A score of
0.75 is uninterpretable unless you know the concentration threshold was 0.60 at
the time.

The seeded row carries the values currently hard-coded in `bias.py`, and
`test_thresholds_match_the_constants_the_detectors_actually_use` fails if
`bias.py` changes without a new engine version:

> *"Change 0.60 in bias.py without changing this row and every historical result
> silently becomes uninterpretable — the number is still there, but what it was
> measured against is now a lie."*

Until T-016 makes the engine read these values, that test is the only thing
holding the two together.

### 3.4 · `openapi.yaml` guards two product rules

Three of the nine contract tests check guarantees rather than syntax:

- **No bias vocabulary in field names or enum values.** A field called
  `anchoring_score` would put the word in front of a learner through the
  generated client, without anyone writing it into the UI. Scoped to names and
  values, **not prose** — a `description` explaining the rule is developer
  documentation and the right place for the vocabulary.
- **No assessment state on the session response.** No coverage, no readiness,
  no count against a target (`PRD` P2, CT-1, CT-2).
- **Every documented error code is declared**, cross-checked against
  `API_CONTRACT` §10, so a client branching on `monthly_limit_reached` cannot
  break because the enum forgot it.

---

## 4 · Where we diverged from the specification

**4.1 · A fourth migration.** The task lists `017, 018`. Seeding the cases is
criterion 3 and belongs in its own revision, so it is **019**. Bundling it into
018 would have made the engine version and the clinical content inseparable in a
downgrade.

**4.2 · `patient.name`, `age` and `sex` were transcribed by hand.**
`DATA_MODEL` §8.1 wants a structured `patient` object; `cases.py` has that
information only in prose, and the five intros use five different sentence
shapes:

```
A 48-year-old male accountant named Ramesh Kumar…
Kavya Menon, a 29-year-old marketing executive…
```

Parsing that with a regex would be fragile in a way nobody would notice. With
five cases, the fifteen values were transcribed into an explicit table in the
generator, where they can be checked by reading the intro. **Every value appears
verbatim in the case's own text** — this is transcription, not authorship, and
the case editor (T-021) is where a clinician can correct them.

**4.3 · Slugs were chosen, not derived.** `cases.slug` is UNIQUE and ends up in
URLs and the admin console, so `case_1` would be a poor permanent identifier.
They are `chest-pain-gerd`, `breathlessness-pulmonary-embolism` and so on.

---

## 5 · The T-010 bug this exposed

The most useful thing that happened, and it was mine.

`tests/db/conftest.py` truncated `cases` and `case_versions` whenever a test
committed. That was **correct in T-010**, when those tables held nothing but
fixtures. It became wrong the moment T-011 seeded real content into them: every
seed assertion failed, in whichever test file happened to run after one that
committed.

It took four hypotheses to find, and two of them are worth keeping.

### 5.1 · `TRUNCATE … CASCADE` propagates outward

Removing `cases` from the truncate list did not fix it. `CASCADE` truncates
every table holding a foreign key *into* the listed ones — and
`cases.created_by` references `profiles`. So `TRUNCATE profiles CASCADE` took
the five seeded cases with it.

The `CASCADE` had to go. Listing the tables explicitly means a forgotten foreign
key now fails loudly instead of quietly widening the blast radius.

`TRUNCATE` itself stays, because `session_events` and `audit_log` carry
append-only triggers that refuse a `DELETE` by design. Truncate bypasses row
triggers — which is exactly what a test teardown wants and exactly what
application code must never be able to do.

### 5.2 · Then keying the cleanup on ids broke it again

The next attempt deleted "cases whose id is not one of the seeded ids",
captured once per session. That failed too:
`test_downgrade_to_base_then_upgrade_again` rebuilds the entire schema
mid-session, and migration 019 generates **fresh UUIDs** on the way back up. The
session-scoped list then referred to rows that no longer existed, and the
teardown deleted all five as "not seeded".

Now keyed on **slug**, which is deterministic across a re-seed.

### 5.3 · A stale assertion

`test_the_head_revision_is_016` hard-coded a revision number and went stale the
moment this task added three migrations. It now reads the latest migration
filename, so adding a migration does not require remembering to update a test.

**The general lesson:** a fixture that encodes "these tables hold only test
data" is a statement about the *current* schema, and it silently stops being
true. The comment in T-010 even said master content was "deliberately absent"
from the list — the reasoning was right, the list simply did not anticipate
`cases` joining that category.

---

## 6 · Other problems hit

**Two dependency advisories on `pip` itself** — `PYSEC-2026-196` and
`PYSEC-2026-3721`. **The same shape as the `setuptools` finding in T-004**: a
tool that ships with the virtualenv rather than something we depend on, clean
locally only because one machine had been upgraded by hand. Both are now pinned
in the `dev` extra so a fresh environment is audit-clean without anyone
remembering.

**`gitleaks` flagged `hba1c_glucose`** — a clinical investigation key — as a
generic API key. Allowlisted, with a note that there are 86 such keys and more
arrive with cases 6–10, so the list will grow.

**And the guard was re-verified.** The first probe used `K = "gsk_…"` and was
*not* detected, which briefly looked like the allowlist had blinded the scanner.
It had not: gitleaks' `generic-api-key` rule keys off an identifier containing
`key`/`token`/`secret`, and the variable was called `K`. With a realistic
`GROQ_API_KEY = "gsk_…"` it fires. **A guard that fails to fire on a bad probe
looks identical to a broken guard** — worth knowing before concluding the second.

---

## 7 · Verification

```bash
pytest -q                        # 356 passed
ruff check .                     # PASS
mypy nidan/domain --strict       # PASS
lint-imports                     # PASS
python validate_detectors.py     # PASS: 94.4%
gitleaks dir .                   # no leaks found
pip-audit --skip-editable        # no known vulnerabilities
```

Against a real container, `upgrade head` → `downgrade base` → `upgrade head`
succeeds repeatedly, and the seed counts are exact each time.

---

## 8 · What this changes for you

```bash
docker compose up -d db
alembic upgrade head
docker compose exec db psql -U nidan -d nidan
```

```sql
SELECT slug, status FROM cases JOIN case_versions ON cases.id = case_id;
SELECT topic_key, count(*) FROM topic_lexicon
  JOIN topic_phrases ON topic_lexicon.id = topic_id GROUP BY 1;
```

**For Yogesh:** `openapi.yaml` is at the repository root. Generate a client from
it and start T-032 — every operation returns 501 today, so mock the responses.
The error codes are a stable contract; branch on `code`, never on the message.

---

## 9 · Known debt left behind

| Debt | Closed by |
|---|---|
| **Nothing reads the seeded content.** The app still imports `cases.py` | T-012, T-016 |
| **`cases.py` is still the place content is authored.** Two sources of truth until the editor exists — regenerate 017/019 if it changes | **T-021** |
| **Development seed absent.** §9.2 also asks for 3 test users, an approving review per case, and ~10 synthetic sessions for dashboard work | unassigned — needed before T-033 |
| **Patient demographics are transcribed, not clinician-confirmed** (§4.2) | T-021 |
| **`openapi.yaml` is unverified against an implementation** — nothing serves it yet | T-030 |
| **No `openapi.yaml` linter in CI.** The tests check structure and the two product rules, not full 3.1 conformance | fold into T-030 |
| **`engine_versions` is seeded but unused.** The detectors still read constants | **T-016** |

---

## 10 · How to undo it

```bash
alembic downgrade 016      # removes the seeds, keeps the schema
git revert HEAD
```

The seeds are additive and nothing reads them, so reverting affects nothing that
runs today.

---

## 11 · Next

**T-012 · Repository layer and tenant scoping** (2 days) — the first code that
actually queries the database. Its acceptance criteria are the interesting part:
*no query bypasses the actor context*, and *RLS policies are tested to actually
deny*.

The RLS tests written in T-010 prove the policies are wired correctly at the
schema level. T-012 proves the application cannot route around them.

---

*Written 12 September 2026 · Vraj Patel (202301408) · Yogesh Bagotia (202301114)*
