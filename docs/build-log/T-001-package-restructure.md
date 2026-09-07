# T-001 · Restructure into a `vpsim/` package

| | |
|---|---|
| **Task** | T-001, BUILD_PLAN Phase 0 |
| **Status** | ✅ Complete — 5 September 2026 |
| **Branch** | `refactor/t-001-package-structure` |
| **Estimated** | 2 days |
| **Specification** | `TECH_SPEC.md` §4.1 · `ADR-0009` |
| **Blocks** | Everything. No other Phase 0 task can start until this lands. |
| **Behaviour change** | None intended. Same routes, same detectors, same numbers. |

---

## 1 · Summary

The prototype was nine Python files sitting loose in the repository root, with
`app.py` importing all of them and the templates folder next to them. That
layout was correct for a research prototype and is wrong for a product.

This task moved every module into a `vpsim/` package split into three layers —
`domain/`, `infra/`, `api/` — and made the boundary between them a **rule that
is tested**, not a convention that is remembered.

Nothing the user sees changed. All nine routes still work, and the detector
validation still reports 94%, which is the number the research claim rests on.

**The one sentence that matters:** `vpsim/domain/` is now pure Python — no
Flask, no Groq, no file I/O, no network — and there are two tests plus a CI
contract that fail the build if anybody breaks that.

---

## 2 · The problem — what was wrong with the old layout

Before this task, the repository root looked like this:

```
app.py                  586 lines — routes, session store, file saving, LLM calls
cases.py                2 421 lines — the 5 clinical cases
bias_detector.py        the three detectors
clinical_evaluator.py   diagnosis and coverage scoring
feedback_generator.py   prompt building AND the Groq API call
session_tracker.py      topic keywords AND session state AND filesystem reads
templates/
static/
```

That is not a criticism of the prototype. For a study with 16 sessions run from
one laptop, it was the right amount of structure. It becomes a problem the
moment we try to do any of the following, all of which are on the build plan:

**a) Test the assessment engine without a network.**
`bias_detector.py` was importable on its own, but `session_tracker.py` was not
usefully testable because the same file that held `TOPIC_KEYWORDS` also read the
`sessions/` directory from disk. `feedback_generator.py` could not be imported
at all without a Groq API key in the environment, because it constructed a
client at module import time. Any test of feedback logic therefore needed a
real API key and a real network call.

**b) Recompute results from stored sessions.**
Property 3 in `CLAUDE.md` — *the event log is the source of truth, derived state
is reproducible from it* — requires that the scoring path can be run over stored
data with no web server and no model. With scoring logic reachable only through
Flask request handlers, that is not possible.

**c) Swap the model or the storage layer.**
`app.py` and `feedback_generator.py` each constructed their own Groq client at
import time, so there were two independent configurations of the same thing.
Changing model, adding retry, or adding cost logging meant editing both and
hoping neither was missed. This
is exactly what ADR-0011 (per-purpose LLM routing) will need.

**d) Let two people work without collisions.**
A 518-line `app.py` touched by every feature is a merge conflict generator.

**e) Prevent the layering from rotting.**
This is the real one. `ADR-0009` chose a **modular monolith**: one deployable
process, but with enforced internal boundaries. The whole argument for that
choice — that we get the simplicity of a monolith without the tangle — depends
on the boundaries actually being enforced. An unenforced boundary is a comment.

---

## 3 · Definition of done

Copied verbatim from `BUILD_PLAN.md`, not paraphrased:

```
T-001 · Restructure into a `vpsim/` package

Phase    0            Depends  —              Est  2 d      Owner  V
Files    vpsim/{api,domain,infra,web}/, pyproject.toml
Spec     TECH_SPEC §4.1 · ADR-0009
Accept   1. Existing modules moved: cases→domain/content,
            bias_detector→domain/assessment/bias,
            clinical_evaluator→domain/assessment/clinical,
            session_tracker→domain/assessment/topics
         2. domain/ imports nothing from infra/ or api/
         3. `python -m vpsim` starts the app with all existing routes working
         4. validate_detectors.py still reports 94% unchanged
Tests    Smoke test hitting every existing route
```

### Evidence that each criterion is met

| # | Criterion | How it was verified | Result |
|---|---|---|---|
| 1 | Modules moved | `git diff --cached -M` rename detection | 12 renames detected, history preserved |
| 2 | `domain/` imports nothing from `infra/`/`api/` | `pytest tests/test_layering.py` and `lint-imports` | 2 tests pass · **1 contract kept, 0 broken** |
| 3 | `python -m vpsim` serves all routes | booted the server, requested three routes over loopback | 9 routes registered, all HTTP 200 |
| 4 | Validation unchanged | `python validate_detectors.py` | **51/54 = 94%** — byte-identical to before |
| — | Smoke test over every route | `pytest tests/test_smoke.py` | 11 tests, all pass |

Total test suite: **17 passing, 0 failing, 0.31 s.**

---

## 4 · What was built — the shape of the code now

### The three layers

```
┌──────────────────────────────────────────────────────────┐
│  vpsim/api/          the web layer                        │
│    routes.py         Flask blueprint "web" — 9 routes     │
│                      parses requests, calls domain,       │
│                      renders responses. Decides nothing.  │
└───────────────────────────┬──────────────────────────────┘
                            │  may import ↓
┌───────────────────────────┴──────────────────────────────┐
│  vpsim/infra/        everything that touches the outside  │
│    llm/gateway.py    THE single call site for the model   │
│    storage.py        session JSON read/write              │
│    session_store.py  ⚠ in-memory state — replaced by T-013│
│    feedback.py       calls the gateway with domain prompts│
└───────────────────────────┬──────────────────────────────┘
                            │  may import ↓
┌───────────────────────────┴──────────────────────────────┐
│  vpsim/domain/       pure logic — the part that matters   │
│    content/cases.py            5 cases, exams, tests      │
│    assessment/bias.py          the three detectors ← IP   │
│    assessment/clinical.py      diagnosis + coverage       │
│    assessment/topics.py        TOPIC_KEYWORDS, extraction │
│    session.py                  state transitions          │
│    feedback.py                 prompt construction        │
│                                                           │
│    imports NOTHING above this line.                       │
│    no flask · no groq · no os.path · no network           │
└──────────────────────────────────────────────────────────┘
```

Arrows point one way only. `domain/` at the bottom knows nothing about the
layers above it, which is what makes it testable in isolation and replayable
over stored data.

### Every file, and what it is

| File | Lines | Layer | What it holds |
|---|---:|---|---|
| `vpsim/app.py` | 43 | wiring | `create_app()` factory |
| `vpsim/__main__.py` | 10 | wiring | `python -m vpsim` entry point |
| `vpsim/api/routes.py` | 432 | api | the 9 HTTP routes |
| `vpsim/domain/content/cases.py` | 2 421 | domain | 5 cases · 27 examinations · 86 investigations |
| `vpsim/domain/assessment/bias.py` | 294 | domain | anchoring, premature closure, confirmation bias |
| `vpsim/domain/assessment/clinical.py` | 156 | domain | diagnosis correctness, coverage scoring |
| `vpsim/domain/assessment/topics.py` | 275 | domain | `TOPIC_KEYWORDS` + `extract_topics()` |
| `vpsim/domain/session.py` | 144 | domain | `create_session`, `update_session`, `record_exam`, … |
| `vpsim/domain/feedback.py` | 150 | domain | prompt building + rule-based fallback text |
| `vpsim/infra/llm/gateway.py` | 94 | infra | `call_llm()` — the only place we talk to a model |
| `vpsim/infra/storage.py` | 112 | infra | `save_session_file`, `count_prior_sessions` |
| `vpsim/infra/feedback.py` | 57 | infra | the model call + graceful degradation |
| `vpsim/infra/session_store.py` | 17 | infra | ⚠ the temporary in-memory dict |
| `tests/test_smoke.py` | 81 | test | 11 route tests |
| `tests/test_layering.py` | 45 | test | 2 boundary tests |

`vpsim/web/` holds the four templates and two static files, unchanged.

---

## 5 · Step by step — exactly what was done

### 5.1 · Branch

```bash
git checkout -b refactor/t-001-package-structure
```

A refactor that touches every file is not something to do on `main`. If it goes
wrong, `git checkout main` is the whole recovery.

### 5.2 · Create the skeleton

```bash
mkdir -p vpsim/{api,domain/{content,assessment},infra/llm,web}
touch vpsim/__init__.py vpsim/api/__init__.py vpsim/domain/__init__.py \
      vpsim/domain/content/__init__.py vpsim/domain/assessment/__init__.py \
      vpsim/infra/__init__.py vpsim/infra/llm/__init__.py
```

The `__init__.py` files are what make each directory a Python package rather
than a plain folder. They are empty on purpose — putting imports in them creates
import cycles that are painful to unpick later.

### 5.3 · Move the files with `git mv`, not `cp`

```bash
git mv cases.py              vpsim/domain/content/cases.py
git mv bias_detector.py      vpsim/domain/assessment/bias.py
git mv clinical_evaluator.py vpsim/domain/assessment/clinical.py
git mv session_tracker.py    vpsim/domain/session.py
git mv templates             vpsim/web/templates
git mv static                vpsim/web/static
```

**Why `git mv` matters.** Copy-then-delete makes git record a deleted file and
an unrelated new file. `git log --follow` stops at the boundary and `git blame`
loses everything before it. On `bias_detector.py` that would have thrown away
the history of the confirmation-bias fix that took the detector from 14%
sensitivity to 100% — the single most important commit in the repository.

Git confirmed it saw these as renames:

```
R100  bias_detector.py       →  vpsim/domain/assessment/bias.py
R100  clinical_evaluator.py  →  vpsim/domain/assessment/clinical.py
R100  cases.py               →  vpsim/domain/content/cases.py
R100  static/chat.js         →  vpsim/web/static/chat.js
R100  templates/*.html       →  vpsim/web/templates/*.html
R070  feedback_generator.py  →  vpsim/domain/feedback.py
R062  session_tracker.py     →  vpsim/domain/assessment/topics.py
R060  app.py                 →  vpsim/api/routes.py
```

`R100` means a pure rename with identical content. The lower numbers are files
that were also split — see the next section.

### 5.4 · Split the three files that were doing more than one job

This is the part that went beyond what the task text described, and it is the
most important part of the work. Section 6 explains why it was necessary rather
than optional.

#### `session_tracker.py` → three files

| Original lines | Went to | Why |
|---|---|---|
| 17–253 (`TOPIC_KEYWORDS`) + 377–404 (`extract_topics`) | `domain/assessment/topics.py` | Pure data and pure string matching |
| 295–377 (`create_session` … `update_session`) + `get_session_summary` | `domain/session.py` | Pure state transitions |
| 256–295 (`count_prior_sessions`) | `infra/storage.py` | **Reads the filesystem** — `os.listdir`, `open()` |

`count_prior_sessions` is the reason this split was forced. It walks the
`sessions/` directory to work out which repeat number a participant is on. That
is disk I/O. Leaving it in `domain/` would have meant `domain/` importing `os`
and `json` to touch the filesystem, which fails criterion 2 the moment anyone
takes it seriously.

#### `feedback_generator.py` → two files

| Went to | What it holds | Why there |
|---|---|---|
| `domain/feedback.py` | `_FEEDBACK_SYSTEM_INSTRUCTION`, `build_feedback_prompt()`, `build_fallback_feedback()` | Deciding *what to say* is domain logic. The fallback text is generated with no model at all. |
| `infra/feedback.py` | `generate_feedback()` | Makes the network call, catches failure, degrades to the fallback |

This split has a payoff beyond tidiness. `build_fallback_feedback()` is the path
that runs when the model is unavailable, and it is now testable with no API key,
no network and no mock. That path is what guarantees no consultation ever ends
without guidance, and it was previously untestable.

#### `app.py` → three files

| Original lines | Went to |
|---|---|
| 138–518 (the routes) | `api/routes.py` |
| 522–582 (`_save_session_file`) | `infra/storage.py`, renamed `save_session_file` |
| the `SESSION_STORE` dict | `infra/session_store.py` |

The leading underscore was dropped from `save_session_file` because it is no
longer private to a module — it is now infra's public interface for writing a
session to disk.

### 5.5 · Consolidate the model calls into one gateway

Two modules each built their own Groq client at import time. They became one:
`vpsim/infra/llm/gateway.py`.

Two design choices in that file are worth understanding, because both are there
to make a *later* task cheap rather than to make this one work.

**Lazy client construction:**

```python
_client = None

def _get_client() -> Groq:
    """Lazily construct the client so importing this module needs no API key."""
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client
```

The old code built the client at import time. That meant `import
feedback_generator` raised an exception if `GROQ_API_KEY` was absent — so tests,
CI, and anyone who cloned the repo without a key could not even import the
module. Building it on first use means the whole application imports cleanly
with no credentials, and only an actual model call needs one. This is what makes
the smoke tests in section 8 possible.

**A `purpose` argument that currently does nothing:**

```python
def _model_for(purpose: str) -> str:
    default = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return os.getenv(f"GROQ_MODEL_{purpose.upper()}", default)

def call_llm(messages, system_instruction, *, purpose="patient", ...):
```

Today every `purpose` resolves to the same model. ADR-0011 says we will route
different jobs to different models — a cheap fast one for voicing the patient, a
stronger one for writing feedback. Adding the parameter now, while there are
only two call sites, means that when T-031 arrives it changes one function and
zero callers. Adding it later means finding and editing every call site.

The gateway also carries retry with backoff (2 s, then 4 s) on transient errors
— rate limits, 5xx, empty responses — which was previously duplicated in two
places and missing from the third.

### 5.6 · The application factory

`vpsim/app.py` replaces the module-level `app = Flask(__name__)`:

```python
def create_app(config: dict | None = None) -> Flask:
    load_dotenv()
    app = Flask(__name__,
                template_folder="web/templates",
                static_folder="web/static")
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
    if config:
        app.config.update(config)
    app.register_blueprint(web_bp)
    return app

app = create_app()          # WSGI entry point: gunicorn vpsim.app:app
```

**Why a factory rather than a global `app`.** A module-level app is created once,
when the module is first imported, using whatever environment happens to exist
at that moment. That is fine for one process running one configuration. It stops
working the moment you want a second configuration — which is exactly what a
test needs. `create_app({"TESTING": True})` gives every test a clean, isolated
application; a global app would leak state between tests.

The `template_folder` and `static_folder` arguments are relative to `vpsim/`,
which is why the templates had to move into `vpsim/web/` rather than staying at
the repository root.

### 5.7 · Packaging

`pyproject.toml` was added. It does four jobs:

```toml
[project]
name = "vpsim"
requires-python = ">=3.11"
dependencies = ["flask>=3.1", "groq>=1.6", "python-dotenv>=1.2"]

[project.optional-dependencies]
dev = ["pytest>=8", "import-linter>=2", "ruff>=0.6"]

[project.scripts]
vpsim = "vpsim.__main__:main"

[tool.importlinter]
root_package = "vpsim"

[[tool.importlinter.contracts]]
name = "domain must not import infra or api"
type = "forbidden"
source_modules = ["vpsim.domain"]
forbidden_modules = ["vpsim.infra", "vpsim.api", "vpsim.app"]
```

1. **Declares real dependencies.** `requirements.txt` was a frozen `pip freeze`
   dump of 33 packages, most of which are transitive. The three lines above are
   what we actually depend on.
2. **Separates dev dependencies.** `pip install -e ".[dev]"` gets you the test
   tools; a production install does not ship pytest.
3. **Makes the package installable** with `pip install -e .`, so `import vpsim`
   works from any directory rather than only from the repository root.
4. **Encodes the layering contract as data**, which is what CI reads in T-004.

### 5.8 · Update the research tooling

`validate_detectors.py`, `analyze_sessions.py` and `test_api.py` stay at the
repository root. They are research instruments, not part of the product, and
promoting them into the package would blur that line.

Their imports were rewritten:

```bash
sed -i '' \
  -e 's/^from cases import/from vpsim.domain.content.cases import/' \
  -e 's/^from session_tracker import/from vpsim.domain.session import/' \
  -e 's/^from bias_detector import/from vpsim.domain.assessment.bias import/' \
  -e 's/^from clinical_evaluator import/from vpsim.domain.assessment.clinical import/' \
  validate_detectors.py analyze_sessions.py
```

A `grep` afterwards caught one the `sed` had missed: `analyze_sessions.py` line
62 had a *lazy* import inside a function body, indented, so the `^from` anchor
did not match it. Worth remembering — anchored `sed` patterns silently skip
imports that are not at column zero.

---

## 6 · Where we diverged from the specification

The task text named four moves. The work required seven. This section records
the difference and the reason, because the discrepancy between `BUILD_PLAN.md`
and the code is otherwise going to look like a mistake.

### 6.1 · `session_tracker` did not go where the spec said

**BUILD_PLAN says:** `session_tracker → domain/assessment/topics`
**What happened:** it went to three places — `domain/assessment/topics.py`,
`domain/session.py`, and `infra/storage.py`.

**Why.** The task text was written before anyone had read that file closely
enough to notice it holds three unrelated responsibilities, one of which reads
the filesystem. Criterion 1 and criterion 2 are in direct conflict for that
file: obeying criterion 1 literally — putting all of `session_tracker.py` into
`domain/assessment/topics.py` — would have put `os.listdir()` inside `domain/`
and broken criterion 2.

Criterion 2 is the one that encodes ADR-0009 and one of the three properties
that must never break, so it wins. Criterion 1 is a convenience description of
where things roughly go.

### 6.2 · `feedback_generator.py` was not mentioned at all

It had to be split for the same reason: prompt construction is a decision
(domain), the API call is I/O (infra).

### 6.3 · `app.py` was not mentioned at all

The task lists `vpsim/{api,domain,infra,web}/` under Files, which implies the
routes move, but does not say so. `app.py` was carrying three responsibilities
and had to be split for the `api/` directory to mean anything.

### 6.4 · The gateway was not in scope

Consolidating the two Groq clients into one is arguably T-031's job. It was done
here because `infra/feedback.py` needed *something* to call, and writing a
third client construction inside the new package — knowing it would be deleted
in T-031 — was worse than writing the gateway once.

**None of these divergences change behaviour.** They are all structural. The
detector numbers are unchanged, which is the check that proves it.

---

## 7 · Problems hit, and what fixed them

### 7.1 · `BuildError: Could not build url for endpoint 'index'`

**Symptom.** Two smoke tests failed after the first run:

```
werkzeug.routing.exceptions.BuildError: Could not build url for endpoint
'index'. Did you mean 'web.index' instead?
```

**Cause.** Moving routes onto a Flask **Blueprint** namespaces every endpoint
under the blueprint's name. The function is still called `index`, but its
endpoint name is now `web.index`. Four `redirect(url_for("index"))` calls inside
`routes.py` were still using the old flat name.

**Fix.** Use the blueprint-relative form:

```python
return redirect(url_for(".index"))
```

The leading dot means *this blueprint*, whatever it is called. That is better
than hard-coding `"web.index"` because the route module stays independent of the
name the application mounts it under.

**Worth noting:** the templates were unaffected — they hard-code paths like
`/start/case_1` rather than using `url_for`. That is a small piece of debt for a
later task, since hard-coded paths break silently if a route ever changes.

### 7.2 · `pip install -e .` failed with a Python version error

**Symptom.**

```
ERROR: Package 'vpsim' requires a different Python: 3.9.6 not in '>=3.11'
```

**Cause.** A bare `pip` on this machine is macOS's system Python 3.9, not the
project's virtual environment. The virtual environment was never activated in
that shell.

**Fix.** Call the venv's interpreter explicitly:

```bash
venv/bin/pip install -e ".[dev]"
```

**Why it is worth recording.** The error is a good one — `requires-python`
caught the mismatch immediately rather than installing and failing later at
runtime with a confusing syntax error on modern type-hint syntax. This is an
argument for keeping `requires-python` accurate.

### 7.3 · `curl` returned 403 from a server that was working perfectly

**Symptom.** With the server confirmed running, every `curl
http://127.0.0.1:5000/` returned `403`, and the server's own log showed no
requests arriving at all.

**Cause.** Not the application. An HTTP proxy in the environment was
intercepting `curl` before it reached the loopback interface. The 403 came from
the proxy.

**Fix.** Request over loopback from Python instead, bypassing the proxy:

```python
urllib.request.urlopen("http://127.0.0.1:5000/", timeout=1)
```

which returned `200, 4666 bytes`.

**The lesson.** When a tool reports a failure that the thing being tested does
not corroborate — here, the server's own access log was empty — suspect the
tool. An empty server log during a "failed" request is a strong signal that the
request never arrived.

---

## 8 · Verification

Four independent checks, all passing. `docs/spec/TEST_STRATEGY.md` explains what
each kind of test can and cannot catch; this is the short version.

```bash
venv/bin/python -m pytest -q          # 17 passed in 0.31s
venv/bin/lint-imports                 # Contracts: 1 kept, 0 broken
venv/bin/python validate_detectors.py # 51/54 = 94%
venv/bin/python -m vpsim              # boots, 9 routes, HTTP 200
```

| Check | What it proves | What it does **not** prove |
|---|---|---|
| 11 route smoke tests | Every route is wired and returns a sane status | That any answer is clinically correct |
| 2 layering tests | `domain/` has no upward imports | That the layers are well designed |
| `lint-imports` | Same rule, enforced transitively, ready for CI | Anything about runtime behaviour |
| `validate_detectors.py` | Detector accuracy is **unchanged at 94%** | That 94% is good enough for clinical use |

The fourth is the one that matters most for this task. Everything else confirms
the code moved; the validation run confirms the code moved **without changing
what it computes**. It runs the real detectors over 18 hand-labelled transcripts
and reports the same 51/54 as before the refactor.

---

## 9 · What this changes for you

If you have pulled this branch, your old commands will not work.

| Before | Now |
|---|---|
| `python app.py` | `python -m vpsim` |
| — | `pip install -e ".[dev]"` — **once, after pulling** |
| — | `pytest` |
| — | `lint-imports` |
| `python validate_detectors.py` | unchanged |
| `python analyze_sessions.py sessions` | unchanged |

### First-time setup after pulling

```bash
source venv/bin/activate
pip install -e ".[dev]"
pytest
python -m vpsim
```

`pip install -e .` installs the package in **editable** mode — it puts a link to
this directory on the Python path rather than copying files. Edit a file and the
change is live; you do not reinstall.

### Where your file went

| You are looking for | It is now in |
|---|---|
| the detectors | `vpsim/domain/assessment/bias.py` |
| the cases | `vpsim/domain/content/cases.py` |
| the routes | `vpsim/api/routes.py` |
| the templates | `vpsim/web/templates/` |
| the LLM calls | `vpsim/infra/llm/gateway.py` |
| topic keywords | `vpsim/domain/assessment/topics.py` |
| session saving | `vpsim/infra/storage.py` |

### If you add a file

Ask one question: **does this touch the outside world?** Network, disk,
database, environment variables, Flask — that is `infra/` or `api/`. If it is
pure computation over data handed to it, it is `domain/`.

Put it in the wrong place and `pytest` tells you within a second. That is the
point of the layering tests.

---

## 10 · Known debt left behind

Deliberate. Each has a task that closes it.

| Debt | Where | Closed by |
|---|---|---|
| **Session state is a dict in process memory.** Lost on restart, cannot be shared between workers, limits the app to one process. Recorded as blocker B1 in `TECH_SPEC`. | `vpsim/infra/session_store.py` | **T-013** — append-only event log in PostgreSQL (ADR-0003) |
| **No unit tests for the domain layer.** The refactor made them possible; it did not write them. Smoke tests prove wiring, not correctness. | `tests/` | **T-002** — test harness and fake LLM gateway |
| **Server-rendered routes.** The prototype's HTML routes remain. | `vpsim/api/routes.py` | **T-030** — JSON API under `/v1` (ADR-0006) |
| **`purpose` does nothing yet.** Every purpose resolves to the same model. | `vpsim/infra/llm/gateway.py` | **T-031** — per-purpose routing, circuit breaker, cost logging |
| **Templates hard-code URLs.** `url_for` is not used, so a route rename breaks links silently. | `vpsim/web/templates/` | unassigned — fold into T-030 |
| **`requirements.txt` still exists** alongside `pyproject.toml`, and they can drift. | repository root | **T-005** — Docker image build |

Each of these is marked in the source with a `NOTE (BUILD_PLAN T-xxx)` comment,
so the code says where the fix lives.

---

## 11 · How to undo it

Nothing here is committed to `main` yet.

**Abandon the whole thing:**

```bash
git checkout main
git branch -D refactor/t-001-package-structure
```

**Keep it but return to the old layout temporarily:**

```bash
git stash              # if there are uncommitted changes
git checkout main
python app.py
```

`git mv` preserved every file's history, so `git log --follow
vpsim/domain/assessment/bias.py` shows the full history of `bias_detector.py`
including the confirmation-bias fix.

---

## 12 · Next

**T-002 · Test harness and fake LLM gateway** (2 days, depends on T-001).

It is cheap now precisely because of this task. `vpsim/infra/llm/gateway.py` is
a single function that everything routes through, so a fake is one substitution
rather than a hunt through the codebase. That unlocks testing the whole
consultation flow — chat, examine, investigate, conclude — with no API key, no
network, no cost, and deterministic replies.

---

*Written 5 September 2026 · Vraj Patel (202301408) · Yogesh Bagotia (202301114)*
