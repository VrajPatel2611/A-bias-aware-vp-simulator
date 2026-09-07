# T-007 · Structured logging and Sentry

| | |
|---|---|
| **Task** | T-007, BUILD_PLAN Phase 0 — **last task in the phase** |
| **Status** | ✅ Complete — 5 September 2026 |
| **Branch** | `refactor/t-001-package-structure` |
| **Estimated** | 0.5 days |
| **Specification** | `TECH_SPEC` §10 (BUILD_PLAN cites §10.1–10.2; §10.2 does not exist) |
| **Behaviour change** | JSON logs to stdout · `/healthz` and `/readyz` added |

---

## 1 · Summary

`vpsim/infra/telemetry/` — JSON logs to stdout carrying `request_id` and
`session_id`, redaction as a last line of defence, Sentry with PII off, and the
two health endpoints `TECH_SPEC` §10 asks for.

A question now logs like this:

```json
{"ts": "2026-09-06T15:31:28+00:00", "level": "INFO", "logger": "vpsim.api.routes",
 "msg": "question_asked", "request_id": "26c8053d93f440e0",
 "session_id": "21dc04ef-5866-45a3-aac0-8fe5e51d2f1d",
 "case_id": "case_1", "question_chars": 41, "question_words": 9}
```

The shape of the question, never the question.

255 → **293 tests**. Phase 0 is complete.

---

## 2 · Definition of done

```
T-007 · Structured logging and Sentry

Phase    0            Depends  T-006          Est  0.5 d    Owner  V
Files    vpsim/infra/telemetry/
Spec     TECH_SPEC §10.1–10.2
Accept   1. JSON logs to stdout with request_id, session_id, user_id
         2. Raw question text never logged at INFO; no emails, no keys
         3. Sentry wired, send_default_pii=False, release tagged
```

| # | Criterion | Evidence |
|---|---|---|
| 1 | JSON to stdout with correlation ids | `JsonFormatter` + `contextvars` · 8 tests |
| 2 | no question text, emails or keys | **end-to-end test drives a real consultation and greps the output** · 17 tests |
| 3 | Sentry, `send_default_pii=False`, release tagged | `errors.py` + a `before_send` scrubber · 4 tests |

---

## 3 · Criterion 2 — the one that needed proving

Criterion 2 is a claim about what is *absent*, and absence is easy to assert and
hard to demonstrate. So the test drives a real consultation and searches the
captured output for the learner's own words:

```python
secret_question = "ZZQUESTIONMARKERZZ does the pain radiate to your jaw"
client.post("/chat", json={"message": secret_question})
client.post("/conclude", json={"diagnosis": "ZZDIAGNOSISMARKERZZ reflux"})

output = capsys.readouterr().out + capsys.readouterr().err
assert "ZZQUESTIONMARKERZZ" not in output
```

**The first draft of this test was broken in an instructive way.** It built
`secret_question` and never posted it — `ruff` caught it as `F841 assigned but
never used`. It passed, and would have kept passing with logging wide open. A
test that asserts something is absent, on input that was never present, proves
nothing.

Verified by breaking it deliberately. Adding `"debug_q": user_message` to the
log call — the exact thing someone does while debugging — turns the test red:

```
FAILED TestNothingSensitiveReaches::test_a_learners_question_never_appears_in_the_log
```

Restored, it passes. Same principle as the validation gate in T-004: a guard
never observed failing is not known to work.

---

## 4 · What was built

```
vpsim/infra/telemetry/
  context.py     request_id / session_id / user_id via contextvars
  logging.py     JsonFormatter, configure_logging
  redaction.py   scrub(), safe_extra(), question_fingerprint()
  errors.py      Sentry init and before_send scrubber
  __init__.py    setup_telemetry()
```

### 4.1 · Correlation without threading it through

`contextvars`, not thread locals — the mechanism asyncio propagates correctly,
so this survives any part of the app becoming async. Bound once per request;
every record emitted while handling it picks them up:

```python
payload.update(context.current())
```

No call site passes `request_id`. Unset ids are **omitted rather than sent as
null**, so a log line does not carry three empty fields before a session exists.

The id comes from an inbound `X-Request-ID` when present, so a trace survives a
proxy, and is echoed on the response — a user reporting a problem can quote
something findable.

### 4.2 · Redaction, and why it is aggressive

The primary control is not logging sensitive things. `redaction.py` is what
catches the case where someone does anyway, months from now, mid-debug.

Two mechanisms:

- **`SENSITIVE_FIELDS`** — field names whose *value* is never safe whatever it
  looks like: `question`, `diagnosis`, `transcript`, `prompt`, `token`. Replaced
  outright. Free text is not worth pattern-matching, because the risk is the
  text itself, not a token inside it.
- **Patterns** — key and email shapes, applied to every remaining string,
  including the rendered message and the formatted traceback. A traceback can
  contain argument values, and an argument can be an API key.

`question_fingerprint()` is the sanctioned alternative: length and word count,
enough to investigate *"it hung on a long input"* without retaining what was
asked.

**Why this matters more here than in most products.** A learner's questions are
the raw material of the assessment — a transcript in a log file is the same data
the database protects with RLS (asset A2). And learners are asked never to enter
real patient data, and mostly will not; *mostly* is the problem, and the guard
for that is T-035.

### 4.3 · `/healthz` and `/readyz`

Separate endpoints because they answer different questions. Liveness: is the
process alive — restart me if not. Readiness: can I serve — hold traffic back.
Conflating them means a temporary dependency outage triggers a restart loop,
which makes the outage worse.

`/healthz` touches nothing. `/readyz` reports individual checks:

```json
{"status": "ready",
 "checks": {"config": true, "cases_loaded": true, "llm_configured": true}}
```

`TECH_SPEC` §10 specifies database, migrations and model-loaded checks. **None
exist yet** — there is no database code until T-010 — so `/readyz` reports what
is true today rather than a check that always passes because it tests nothing.
Each is added as its dependency arrives.

`llm_configured` is **reported but not required**: the app serves the case list
and the feedback fallback without a key, so a missing key should not remove the
instance from service.

**This closes the T-005 gap.** The container healthcheck previously probed `/`,
rendering the entire case list every 30 seconds. It now hits `/healthz`.

### 4.4 · Sentry

```python
sentry_sdk.init(
    dsn=dsn, environment=environment, release=release,
    send_default_pii=False,
    before_send=_before_send,
)
```

`send_default_pii=False` is the setting the criterion names. With PII on, Sentry
attaches request bodies, headers and cookies — for this app, the learner's
questions and their session cookie (assets A2 and A3).

`before_send` covers what that flag does not: a key interpolated into an
exception message, and the query string, which is dropped entirely. It is
wrapped so that **reporting can never raise** — an error reporter that throws
becomes the error being reported.

No DSN means no reporting, which is the normal state locally and in tests, and
must not be an error.

---

## 5 · Where we diverged

**5.1 · `TECH_SPEC §10.2` does not exist.** §10 has an intro table and §10.1
(*Metrics that matter*). The intro table carries the actual requirements and was
used.

**This is the fifth dangling `Spec` reference in six tasks** — §12.2, §9.3,
§9.4, §10.2 wrong; §9.1 correct. Now logged for the fourth time; see §7.

**5.2 · Files changed beyond `vpsim/infra/telemetry/`.** `config.py` (four
settings), `app.py` (middleware, health endpoints), `api/routes.py` (bind the
session id, log the fingerprint), `Dockerfile` (healthcheck), `.env.example`,
`pyproject.toml`, `requirements.txt`.

**5.3 · `question_fingerprint` is used, not just provided.** The first pass
imported it into `app.py` without calling it — `ruff` flagged it as unused. An
API nothing calls is a suggestion; wiring it into the chat route makes the
intended pattern the actual one.

---

## 6 · What T-006's test caught

Adding four settings broke `test_every_declared_field_appears_in_env_example`
immediately — the test written *one task earlier* to prevent exactly this.

```
FAILED tests/test_config.py::TestEnvExampleStaysHonest::
       test_every_declared_field_appears_in_env_example
```

`.env.example` now documents `LOG_LEVEL`, `ENVIRONMENT`, `SENTRY_DSN` and
`RELEASE`. Without that test the file would have been silently four variables
out of date, which is how configuration documentation normally dies.

`LOG_LEVEL` also gets a validator, because a misspelt level is accepted by the
logging library and **silently produces no output at all** — the worst possible
failure mode for a logger.

---

## 7 · Verification

```
ruff                          PASS
mypy (domain strict)          PASS
import-linter                 PASS
pytest                        PASS   293 tests, coverage 99.63%
case invariants               PASS   C-1 … C-9
pip-audit                     PASS   no known vulnerabilities
validation 94%                PASS   51/54
```

Validation **51/54 = 94%**, unchanged across all seven Phase 0 tasks.

---

## 8 · Known debt left behind

| Debt | Closed by |
|---|---|
| **`user_id` is never bound.** The plumbing carries it; nothing sets it, because there are no accounts | **T-014** |
| **`/readyz` checks nothing external.** Database, migrations, model-loaded are specified but do not exist | T-010, Phase 5 |
| **No metrics.** `TECH_SPEC` §10.1 lists six with alert thresholds — p95 latency, cost per session, leakage rate. None are emitted | T-031, T-043 |
| **Sentry never actually connected.** No DSN available here; the disabled path is tested, the enabled path is not | first deploy |
| **`traces_sample_rate=0.0`** — no performance monitoring. Cost, not privacy | when latency needs investigating |
| **Five dangling `Spec` references in BUILD_PLAN** (§5.1). Raised in T-004 and T-006 and still open | **unassigned — worth doing before Phase 1** |

---

## 9 · How to undo it

```bash
rm -rf vpsim/infra/telemetry tests/test_telemetry.py
git checkout HEAD -- vpsim/app.py vpsim/api/routes.py vpsim/config.py \
                     Dockerfile .env.example pyproject.toml requirements.txt
```

---

## 10 · Phase 0 is complete

| Task | | Verified |
|---|---|---|
| T-001 | package restructure | ✅ |
| T-002 | test harness, fake LLM gateway | ✅ |
| T-003 | lexicon disjointness | ✅ |
| T-004 | CI with the validation gate | ✅ except branch protection |
| T-005 | Docker + compose | ⚠️ **unrun** |
| T-006 | typed configuration | ✅ |
| T-007 | telemetry | ✅ |

**53 → 293 tests. Five real defects, each found by a test rather than review:**

| Task | Defect |
|---|---|
| T-002 | `"mi"` matched *examine*/*vomiting* — inflated anchoring for every `case_1` learner |
| T-002 | `"gi"` matched *angina* — suppressed anchoring rule A2 |
| T-003 | `"heart"` matched *heartburn* — flagged learners who reasoned **correctly** |
| T-004 | session saving broken and silent for three tasks |
| T-007 | the redaction test proved nothing until `ruff` caught the unsent question |

Two things are outstanding and neither is code: **branch protection** and
**running the container stack**.

And `BUILD_PLAN` §11.1 still applies: **content authoring is the critical
path.** Ten reviewed cases gate launch, five exist, and nothing in Phase 0
produced one.

---

*Written 5 September 2026 · Vraj Patel (202301408) · Yogesh Bagotia (202301114)*
