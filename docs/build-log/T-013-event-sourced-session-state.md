# T-013 · Event-sourced session state

| | |
|---|---|
| **Task** | T-013, BUILD_PLAN Phase 1 ⭐ |
| **Status** | ✅ Complete — 12 September 2026 |
| **Branch** | `feat/event-sourced-sessions` |
| **Estimated** | 3 days |
| **Specification** | `ADR-0003` · `DATA_MODEL` §6.2, §8.2 |
| **Behaviour change** | The app now requires PostgreSQL, runs on 2 workers, and survives a restart mid-consultation |

---

## 1 · Summary

`SESSION_STORE` is gone. Every consultation is an append-only log in
`session_events`, and session state is replayed from it on every request.

```
domain/events.py            the 8 event types, payload validated on write
domain/session.py           replay(events) — a pure fold
domain/feedback_view.py     the feedback screen, recomputed rather than stored
infra/db/repositories/
  events.py                 append with a savepoint retry
  feedback.py               the prose — the only thing stored
api/routes.py               rewritten: replay, act, append, return
migration 021               the four RLS policies DATA_MODEL §10.1 left out
Dockerfile                  --workers 1 → 2
```

**37 new tests.** 433 pass, 98.9 % coverage on the domain.

The line this task existed to change, in the Dockerfile, had been waiting for it:

> `--workers 1` is NOT a performance choice. […] **Raise this in T-013, not before.**

---

## 2 · Definition of done

| # | Acceptance criterion | Met by |
|---|---|---|
| 1 | SESSION_STORE deleted entirely | `infra/session_store.py` removed; no references remain |
| 2 | Every action appends an event before the response is returned | `test_a_consultation_records_every_action_as_an_event` — reads the table after each response |
| 3 | `UNIQUE(session_id, seq)` collision retried cleanly, never interleaved | `tests/db/test_event_concurrency.py` — 10 real threads |
| 4 | Killing the process mid-consultation loses nothing; resume works | `test_a_consultation_survives_losing_the_process` |
| 5 | App runs with 2 gunicorn workers with no session bleed | Verified against the running container — see §7 |

---

## 3 · What was built

### 3.1 The shape of a request now

```
replay the log  →  act  →  append what happened  →  return
```

Nothing is held between requests. The browser cookie carries three values — a
visitor id, the current session id, the current case id — and every one of them
is an identifier, not state.

### 3.2 `replay` is a fold, and re-derives nothing

```python
def replay(events, *, case_id, started_at) -> Session
```

It returns exactly the shape `create_session` produces, so the detectors, the
feedback builder and the templates did not change. That was the promise
`session.py` made in T-001 when it said the signatures were kept stable so this
change would be contained.

The important discipline is what replay does *not* do. Topics come from
`patient_reply.matched_topics`, not from re-running `extract_topics` over the
questions. An early diagnosis comes from its own event, not from re-scanning
the text. `DATA_MODEL` §8.2 is explicit about why:

> **`matched_topics` on `patient_reply` rather than on `question`** — deliberate.
> It records what the *system understood*, evaluated at the time, under the
> engine version then current. Recomputation compares against this to detect
> drift.

Recomputing during replay would make every replay agree with today's code by
construction, and destroy the signal that recomputation exists to find.

### 3.3 The retry, and the trap underneath it

`UNIQUE (session_id, seq)` is the concurrency control. The trap is what a
collision does to the surrounding transaction: in PostgreSQL a unique violation
aborts **the whole transaction**, so every later statement fails with *"current
transaction is aborted"*. A `try / except / retry` written the obvious way turns
one collision into a dead scope — and looks perfectly correct in every
single-threaded test.

So the INSERT runs inside a `SAVEPOINT`. `test_the_retry_needs_its_savepoint`
is the single-threaded proof that the poisoning is real.

`pg_advisory_xact_lock` would remove the race entirely and was rejected:
BUILD_PLAN specifies the retry, and a lock adds a failure mode — one stuck
transaction blocking every append for that session — that a retry does not have.

### 3.4 What is stored, and what is not

Only the prose. Every number on the feedback page — flags, scores, verdicts,
both scorecards, the coverage grid — is recomputed from the log when the page is
rendered.

A stored score is a cache of a conclusion, and a cache can disagree with the log
it came from, silently, in the direction nobody checks. The model's words are
the one thing that genuinely cannot be recomputed, because replaying the same
events would produce different sentences. That split is `ADR-0005` — *the model
writes prose and never marks* — turned into a storage decision.

`test_the_feedback_page_stores_prose_and_recomputes_everything_else` asserts
both halves, including that `session_results` is still empty.

### 3.5 Ownership, before accounts exist

T-013 lands before T-014 (auth), so there are no accounts to own a session. Every
consultation is created through the **anonymous trial path** that T-012 built —
which is not a workaround: `PRD` FR-2 makes the first case a trial anyone can
take without an account, and T-015 adds the step that claims it at signup.

The alternative — running the whole application as a `ServiceActor` with RLS
bypassed — would have built exactly the habit T-012 was written to prevent.

---

## 4 · Where we diverged from the specification

**A backoff was added to the retry.** BUILD_PLAN says "retried cleanly" and
nothing about waiting. Five immediate retries were not enough — see §5.

**`CASE_SLUGS` moved into `domain/content/cases.py`.** It lived in
`scripts/generate_case_migration.py`, and the application needed it at runtime
to resolve a consultation to its `case_versions` row. Moving rather than copying
was the point; the generator now imports it, migration 019 regenerates
byte-identical, and a test asserts the map matches the seeded rows.

**`prototype_version_id` is a deliberate, temporary bypass.** Migration 019
seeded all five cases as drafts, on purpose (`DATA_MODEL` §9.2: publishing them
without review would make the gate a formality). A `sessions` row needs a real
`case_version_id`, so one method may resolve an unpublished case — it returns an
id and nothing else, and requires a `ServiceActor` with a written reason. It is
deleted at T-023.

**Five smoke tests became integration tests.** They drove routes that now need a
database. Rather than put the whole smoke file behind a container, they moved to
`tests/db/test_routes.py` and got stronger; `tests/test_smoke.py` keeps the
routes that read no session state, and still runs in under a second with nothing
installed.

**`FLASK_SECRET_KEY` became mandatory in production.** Not in the task
description; it is a direct consequence of raising the worker count. See §6.

**`pid` was added to the JSON log.** Criterion 5 is about which worker served
what, and the log could not answer that question. It is a standard field for a
multi-worker deployment, and it is what made §7 verifiable rather than assumed.

---

## 5 · The RLS defect this task found

Writing the first `feedback_texts` row meant checking its policy. Four tables
had **RLS enabled with zero policies**:

```
feedback_texts      subscriptions      user_progress      user_case_history
```

In PostgreSQL that does not mean "unrestricted". It means **deny everything** to
any role that is not the owner or a superuser. Those four tables were not weakly
protected — they were entirely unreadable and unwritable by the application.

`DATA_MODEL` §10.1 enables RLS on eight tables and writes policies for four.

**Why three tasks passed over it.** T-010 tested the policies that exist. T-012
exercised sessions and profiles. The anonymous-trial path runs as a bypassing
role and would have worked regardless. T-013 is the first task to write one of
those tables — and had it not been checked here, the first *authenticated* write
would have been T-014's problem, surfacing one table at a time, each as a fresh
mystery, with no error message explaining any of them.

Fixed by migration 021, following §10.1's own two patterns. Guarded by a
property of the schema rather than a list of tables:

```
AssertionError: RLS is enabled with no policy on: user_progress
— these tables deny every query from the application, silently
```

Verified by dropping a policy and watching it fire.

---

## 6 · Three tests that passed for the wrong reason

Both were found by deliberately breaking what they guard — the same practice
T-012 adopted, and the second time it has paid.

**The concurrency test starved a thread.** Ten parallel appends, nine landed,
one exhausted its five attempts. The retry was not broken; it was *lockstep*.
Every loser of a collision recomputes `max(seq) + 1` and retries immediately, so
the contenders stay synchronised and keep colliding as a group — the unluckiest
thread loses repeatedly through no growing improbability of its own.

Fixed with randomised backoff (randomised, not fixed: a fixed delay reschedules
every loser at the same instant and reproduces the lockstep) and a higher
ceiling. Then run eight times in a row to confirm it is not flaky, because a
concurrency test that passes once has told you almost nothing.

**The savepoint test passed without running any SQL.** It asserted
`pytest.raises(Exception)` around a deliberately colliding INSERT. It passed —
but the statement never executed: SQLAlchemy rejected the text before sending
it, so the transaction stayed healthy and the *real* assertion that followed
found nothing wrong.

`pytest.raises(Exception)` cannot tell "the thing I meant happened" from
"something else did". Now `pytest.raises(IntegrityError)`.

**The restart test passed off a developer's `.env`, and CI caught it** — the
third instance, and the only one I did not find myself:

```
FAILED tests/db/test_routes.py::test_a_consultation_survives_losing_the_process
assert 400 == 200
```

The test builds a second application and hands it the first one's cookie. It set
`FLASK_SECRET_KEY` with `monkeypatch.setenv` — which does nothing, because
`settings` is a module-level singleton read at import. Locally the key came from
my `.env`, both applications shared it, and the test passed. On a runner with no
`.env`, each `create_app` fell back to `os.urandom(24)` and the second could not
read the first's cookie.

**The test bug was hiding a real one.** `app.py` has always had that fallback,
and gunicorn imports the application separately in each worker — so with the
`--workers 2` this very task introduced, an unset `FLASK_SECRET_KEY` means every
worker signs session cookies with a different secret and rejects the others'.
The learner is thrown out of their consultation on roughly half their requests,
with nothing in the logs to explain it.

At `--workers 1` that setting was merely inconvenient: sessions did not survive
a restart. **Raising the worker count is what turned it into a broken
application**, so the fix belongs to the task that raised it:

* `config.py` now refuses to start a **production** environment without a key,
  with a message that says why. Development and tests keep the random fallback.
* `create_app` accepts `SECRET_KEY` in its config dict, so a test that builds
  two applications can pin it explicitly rather than depend on an environment
  variable it cannot actually set.

This is the third time CI has caught something that passed locally because of
one machine's state — after `setuptools` in T-004 and `pip` in T-011. The
pattern is identical every time: *the developer's environment supplies
something the specification never required.*

---

## 7 · Verification

```
pytest                          433 passed        (was 396)
pytest tests/db -q --no-cov     103 passed        (was 82)
ruff check .                    All checks passed
mypy nidan/domain --strict      Success: no issues found in 12 source files
lint-imports                    2 contracts kept, 0 broken
python validate_detectors.py    PASS: 94.4%
coverage (domain)               98.93%
```

**Criterion 5, against the running container.** Not a unit test — `docker
compose up --build`, 2 gunicorn workers, one consultation driven over HTTP:

```
requests served, by worker pid:
  pid 7: 11 requests   e.g. ['/pre_case/case_2', '/examine', '/examine', '/examine']
  pid 8:  3 requests   e.g. ['/examine', '/investigate', '/investigate']

distinct workers: 2
```

One consultation, two worker processes, and in the database afterwards:

```
8e627fd8  chest-pain-gerd                    completed  events= 8 max_seq= 8
9fb0a136  breathlessness-pulmonary-embolism  completed  events=11 max_seq=11
```

`events == max_seq` on both: dense sequences, no gaps, no duplicates. Blocker B1
is cleared.

New tests, by what they defend:

| File | Tests | Defends |
|---|---|---|
| `tests/db/test_routes.py` | 14 | criteria 2, 4, 5 — the consultation end to end |
| `tests/domain/test_replay.py` | 16 | replay is pure and reproduces the session |
| `tests/db/test_event_concurrency.py` | 6 | criterion 3 — the retry, with real threads |

---

## 8 · What this changes for you

**The app now needs PostgreSQL to run.** `docker compose up --build` gives you
both. `python -m nidan` alone will refuse the first consultation with a message
naming the fix.

**Restarting no longer loses anything.** Stop the app mid-consultation, start it
again, carry on. That is now a test, not a hope.

**Two workers.** `TECH_SPEC` §9.1's deployment shape is real.

**Adding a new kind of action is three steps:** add the type to the enum
(a migration), add its payload shape to `_SHAPES` in `domain/events.py`, and
handle it in `replay`. The second step is what stops a typo'd payload key from
being accepted silently by a JSONB column and found months later by a replay
that cannot see the field it wants.

---

## 9 · Known debt left behind

**`/chat` appends the question and the reply together, after the model
answers.** Appending the question first would be more orthodox, but a failed
model call would then leave a question with no answer — the learner retypes and
the log holds it twice. `question_count` feeds premature closure (P1: `q < q_min`),
so an inflated count *suppresses* a flag the learner should have seen. Losing a
question nobody got an answer to is the cheaper mistake, and it is recorded here
as a decision rather than an accident.

**The container cannot write `sessions/`.** The research JSON export warns and
continues (`Permission denied: 'sessions'`). Pre-existing, not introduced here —
the export needs a writable mount or an object store. It does not affect the
event log, which is the source of truth.

**`prototype_version_id` must be deleted at T-023**, when the cases are
published and there is a real published version to point at.

**`pre_case_data` lives in the signed cookie.** `participant_id` and
`year_of_study` are pilot-research fields with no column, consumed only by the
JSON export. The profile owns `year_of_training` once accounts exist (T-014).

---

## 10 · How to undo it

```bash
alembic downgrade 020          # drops the four RLS policies
git revert <commit>
```

Reverting restores `SESSION_STORE` and with it blocker B1 — single worker, state
lost on restart. The event rows are harmless if left behind.

---

## 11 · Next

**T-014 · Supabase Auth integration** (2 days) — JWT verification against JWKS,
`@require_auth`, and the profile lifecycle. It unblocks **T-015**, where the
`anonymous_id` written by every consultation in this task finally gets claimed
into a real account, and the trial path stops being the only path.

T-016 (assessment from events) also unblocks: the golden-file test over the 16
pilot sessions now has a log to replay.
