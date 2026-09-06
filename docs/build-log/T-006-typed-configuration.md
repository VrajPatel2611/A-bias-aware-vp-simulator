# T-006 · Typed configuration

| | |
|---|---|
| **Task** | T-006, BUILD_PLAN Phase 0 |
| **Status** | ✅ Complete — 5 September 2026 |
| **Branch** | `refactor/t-001-package-structure` |
| **Estimated** | 1 day |
| **Specification** | none — BUILD_PLAN cites `TECH_SPEC` §9.4, which is *CI/CD* (§6.1) |
| **Behaviour change** | The app now refuses to start on invalid configuration |

---

## 1 · Summary

One module, `vpsim/config.py`, declaring every setting the application reads,
validated once at start-up. `.env.example` documents all of them, and a test
fails if a new field is added without documenting it.

Configuration errors that used to surface partway through a consultation now
stop the process at boot with a message naming the variable and exit code 78
(`EX_CONFIG`).

**Criterion 2 — no secret anywhere in the repository — was already true**, and
now demonstrably so: every blob ever committed was scanned, not just the working
tree. Zero key-shaped strings; `.env` has never been tracked.

231 → **255 tests.**

---

## 2 · The problem

Configuration was three scattered `os.getenv` calls. Two failure modes, both
quiet.

**Late failure.** `GROQ_API_KEY` was read when the gateway first built its
client — that is, on the learner's first question. A missing key produced a
failed consultation a third of the way in, not a container that refused to
start.

**Silent failure.** `os.getenv("DEBUG")` returns the *string* `"false"`, which
is truthy. Written as `if os.getenv("DEBUG")`, debug mode is **on** in
production — and the Flask debugger offers remote code execution
(`SECURITY_SPEC` §3, T5). A misspelt variable name is worse still: `getenv`
returns `None` and the code proceeds with a default nobody chose, with no error
at any point.

Both become a start-up failure with a typed schema.

---

## 3 · Definition of done

```
T-006 · Typed configuration

Phase    0            Depends  T-001          Est  1 d      Owner  V
Files    vpsim/config.py, .env.example
Spec     TECH_SPEC §9.4
Accept   1. pydantic-settings; app fails fast on boot with a clear message if config is invalid
         2. No secret literal anywhere in the repo (gitleaks green)
         3. .env.example documents every variable
```

| # | Criterion | Evidence |
|---|---|---|
| 1 | fails fast with a clear message | **exit 78 verified**, message names the variable · 24 tests |
| 2 | no secret literal in the repo | **every blob in history scanned — 0 hits** · `.env` never tracked |
| 3 | `.env.example` documents every variable | all 6 fields, plus 7 compose/optional variables · **enforced by a test** |

```
invalid config  -> exit 78  (EX_CONFIG)
valid config    -> exit 0
```

```
VPSim cannot start — configuration is invalid:

  GROQ_API_KEY: Value error, GROQ_API_KEY is still the placeholder from
  .env.example. Put a real key in .env, or leave it empty to run without a
  patient.

See .env.example for every variable and what it does.
```

---

## 4 · What was built

### 4.1 · `vpsim/config.py`

Six fields, each carrying a `description` that says what breaks if it is wrong.
It lives in the package root, not `infra/`, because `api/` and `infra/` both
read it and `domain/` reads nothing (ADR-0009).

Two validators, each aimed at a specific mistake someone will make.

**The unfilled placeholder:**

```python
placeholders = {"your-groq-api-key-here", "changeme", "replace-me", ...}
if v.strip().lower() in placeholders:
    raise ValueError("GROQ_API_KEY is still the placeholder from .env.example.")
```

Copying `.env.example` and forgetting to paste a key is the single most likely
first-run error. Without this it appears as a 401 from Groq during a
consultation, which looks like a Groq problem.

**The compose development secret:**

```python
if v.strip() == "local-development-only-not-a-secret":
    raise ValueError("FLASK_SECRET_KEY is the docker-compose development default...")
```

`docker-compose.yml` sets a fixed secret so browser sessions survive a restart
locally. Deployed, it lets anyone forge a session cookie. Because the value is
written down in a committed file, it is exactly the kind of thing that reaches
production by being copied. The error message includes the command to generate a
real one.

### 4.2 · `SystemExit`, not a raised exception

```python
except ValidationError as e:
    print("\nVPSim cannot start — configuration is invalid:\n", file=sys.stderr)
    for err in e.errors():
        print(f"  {'.'.join(str(p) for p in err['loc'])}: {err['msg']}", file=sys.stderr)
    raise SystemExit(78) from e   # EX_CONFIG, sysexits.h
```

Criterion 1 says *a clear message*. Pydantic's default traceback buries the one
useful line under a stack, and in a container that stack is what lands in the
logs. Exit 78 is the conventional "configuration error" code, so an orchestrator
can tell a bad config from a crash.

### 4.3 · Wiring — the part that makes it real

A config module nothing reads is decoration. All three call sites moved:

| Was | Now |
|---|---|
| `app.py`: `os.environ.get("FLASK_SECRET_KEY", os.urandom(24))` | `settings.FLASK_SECRET_KEY or os.urandom(24)` |
| `gateway.py`: `Groq(api_key=os.getenv("GROQ_API_KEY"))` | `Groq(api_key=settings.GROQ_API_KEY)` |
| `__main__.py`: hard-coded `port=5000`, `debug=True` | `settings.PORT`, `settings.DEBUG` |

`load_dotenv()` was removed from `app.py` — pydantic-settings reads `.env`
itself, and two things loading it independently is how they come to disagree.

**One `os.getenv` remains, deliberately:**

```python
# The per-purpose override stays an os.getenv: the variable name is built from
# `purpose` at call time, so it cannot be a declared Settings field.
return os.getenv(f"GROQ_MODEL_{purpose.upper()}", settings.GROQ_MODEL)
```

The variable name is computed, so it cannot be declared. The *default* comes
from validated configuration.

### 4.4 · A test that keeps the documentation honest

```python
def test_every_declared_field_appears_in_env_example(self):
    documented = set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", text, re.M))
    missing = sorted(set(Settings.model_fields) - documented)
    assert not missing, f".env.example does not document: {missing}"
```

Criterion 3 is true today. This is what keeps it true. Documentation that is
merely correct at the moment it is written decays; documentation with a test
does not.

There is also a test asserting `.env.example` contains nothing key-shaped —
`gitleaks` catches that in CI, but this fails locally, before the push.

---

## 5 · Criterion 2 — the secret scan

`gitleaks` is not installed on this machine and runs as a GitHub Action in CI
(T-004). Rather than assume, the check was done directly — and against **history,
not just the working tree**, because a deleted secret is still a leaked secret.

```
working tree, key patterns          0 hits
every blob ever committed           0 hits   (all objects, not a sample)
.env ever tracked                   never
files named *.pem / *.key / secret  none
```

Patterns: `gsk_…` (Groq), `AIza…` (Google — the project used Gemini before),
`sk-…`, `AKIA…` (AWS), and PEM private-key headers.

The Gemini-era check mattered: `google-auth` survived the migration as a dead
dependency until T-004 removed it, so a stale credential was plausible. There
was none.

---

## 6 · Where we diverged from the specification

**6.1 · The cited spec section is about something else.** `TECH_SPEC` §9.4 is
CI/CD. Configuration is not specified anywhere in `TECH_SPEC`.

**This is the fourth dangling `Spec` reference in five tasks** — T-002 cited
§12.2 (does not exist), T-004 cited §9.3 (*Environments*), T-005 cited §9.1
(correct), T-006 cites §9.4 (*CI/CD*). The references were written before
`TECH_SPEC` was finalised and never re-checked. Logged in §8; it is a
five-minute fix and it is now misleading four times over.

**6.2 · Files changed beyond the two listed.** `vpsim/app.py`,
`vpsim/__main__.py`, `vpsim/infra/llm/gateway.py` (the wiring — without it the
module does nothing), `pyproject.toml` and `requirements.txt`
(`pydantic-settings`), `tests/test_config.py`.

**6.3 · `settings` is a module-level singleton.** Loaded once at import, so
`monkeypatch.setenv` in a test does not change it. That is the intended
behaviour — configuration is a boot-time fact — and the module says so. Tests
that need different values construct `Settings(_env_file=None, ...)` directly,
which is what `tests/test_config.py` does throughout.

---

## 7 · Verification

```
ruff                          PASS
mypy (domain strict)          PASS
import-linter                 PASS
pytest                        PASS   255 tests, coverage 99.63%
pip-audit                     PASS   no known vulnerabilities
validation 94%                PASS   51/54
```

Validation **51/54 = 94%**, unchanged across all six Phase 0 tasks.

---

## 8 · Known debt left behind

| Debt | Closed by |
|---|---|
| **Four dangling `Spec` references in BUILD_PLAN** (§6.1). Each sends the next person to the wrong section | **unassigned — worth doing now, five minutes** |
| **`TECH_SPEC` does not specify configuration at all.** This module was designed from the criteria alone | fold into a `TECH_SPEC` revision |
| **`gitleaks` never actually run.** History was scanned by hand with five patterns; gitleaks knows hundreds | first CI run |
| **`DATABASE_URL` is declared but unread** | T-012 |
| **No settings for logging or Sentry** | **T-007**, next |
| **`requirements.txt` and `pyproject.toml` both list dependencies.** Now three places if you count the Dockerfile — though the Dockerfile reads `pyproject.toml` only | unassigned |

---

## 9 · How to undo it

```bash
rm vpsim/config.py .env.example tests/test_config.py
git checkout HEAD -- vpsim/app.py vpsim/__main__.py vpsim/infra/llm/gateway.py \
                     pyproject.toml requirements.txt
```

---

## 10 · Next

**T-007 · Structured logging and Sentry** (0.5 d, depends T-006) — the last
task in Phase 0. JSON logs with `request_id` and `session_id`, no raw question
text at INFO, no emails, no keys; Sentry with `send_default_pii=False`.

It also closes the `/healthz` gap left by T-005, whose container healthcheck
currently hits `/` and renders the whole case list.

---

*Written 5 September 2026 · Vraj Patel (202301408) · Yogesh Bagotia (202301114)*
