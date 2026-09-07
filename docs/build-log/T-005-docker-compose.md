# T-005 · Docker and docker-compose

| | |
|---|---|
| **Task** | T-005, BUILD_PLAN Phase 0 |
| **Status** | ✅ **Complete — stack built and run, 6 September 2026.** See §3a |
| **Branch** | `refactor/t-001-package-structure` |
| **Estimated** | 1 day |
| **Specification** | `TECH_SPEC` §9.1 · `ADR-0008` |
| **Behaviour change** | None to the application. One Dockerfile defect from T-004 fixed |

---

## 1 · Summary

`docker-compose.yml` brings up the application and Postgres 16 with pgvector.
The Dockerfile from T-004 was rewritten — it had a real defect.

**Read §3 before treating this as done.** Docker is not installed on this
machine, so the two criteria that matter — *compose brings up app + Postgres*
and *`docker compose up` gives a working app on a clean machine* — **could not
be executed**. They are runtime criteria and nothing was run.

What was verified is a strong proxy: the package installs from a clean tree with
templates bundled, and **serves every route from `site-packages` with no source
tree present** — which is exactly the situation inside the runtime stage.

---

## 2 · Definition of done

```
T-005 · Docker + docker-compose

Phase    0            Depends  T-001          Est  1 d      Owner  V
Files    Dockerfile, docker-compose.yml, .dockerignore
Spec     TECH_SPEC §9.1
Accept   1. Multi-stage build; non-root user; healthcheck
         2. compose brings up app + Postgres 16 with pgvector
         3. `docker compose up` gives a working app on a clean machine
```

| # | Criterion | Status |
|---|---|---|
| 1 | multi-stage, non-root, healthcheck | ✅ **built** — 15 stages, first attempt, no edits |
| 2 | compose brings up app + Postgres 16 with pgvector | ✅ **PostgreSQL 16.15, vector 0.8.6, pgcrypto 1.3, pg_trgm 1.6** |
| 3 | `docker compose up` works on a clean machine | ✅ all routes 200; `/readyz` reports every check true |

## 3a · Verified on 6 September 2026

Docker Desktop was installed and the stack run. Everything in §3 below was
written before that and is kept as the record of what was and was not known at
the time.

**The build succeeded on the first attempt**, with no edits to the Dockerfile:

```
✔ Image pgvector/pgvector:pg16        Pulled
✔ Image a-bias-aware-vp-simulator-app Built     (15/15 stages)
Container vpsim-db Healthy
```

**The init SQL ran** — the file §5 says could not be validated locally:

```
/docker-entrypoint-initdb.d/01-extensions.sql
CREATE EXTENSION
CREATE EXTENSION
CREATE EXTENSION
```

Queried from the host afterwards:

```
pg_trgm 1.6 · pgcrypto 1.3 · plpgsql 1.0 · vector 0.8.6
PostgreSQL 16.15 (Debian) on aarch64
```

**The application served:**

```
/healthz          -> 200  {"release":"vpsim@0.2.0","status":"ok"}
/readyz           -> 200  {"checks":{"cases_loaded":true,"config":true,
                            "llm_configured":true},"status":"ready"}
/                 -> 200  4666 bytes
/pre_case/case_1  -> 200  4493 bytes
```

### One failure, and it was not ours

```
Error response from daemon: ports are not available: exposing port TCP
0.0.0.0:5432 -> bind: address already in use
```

Homebrew `postgresql@15` already held 5432 on the development machine — the same
instance §5 mentions abandoning a test against. Fixed with `POSTGRES_PORT=5433`
in `.env`, which is the override the compose file already provided and
`.env.example` already documented. No file changed.

Worth knowing: **the host port is now 5433** on that machine. Inside the compose
network the database is still `db:5432`, so nothing in the application depends
on it, and `.env` is git-ignored so it does not affect anyone else.

### One real defect, visible only in the container

Gunicorn's access log is plain text, so every request was logged **twice** —
once as JSON with correlation ids, once as a gunicorn access line — and the
`/healthz` probe reappeared every 30 seconds despite the app-level filter added
in T-007 to remove it.

Invisible locally: `python -m vpsim` runs Werkzeug, whose logger T-007 had
already silenced. It took a real container to surface.

Fixed by dropping `--access-logfile` from the Dockerfile `CMD`.
`--error-logfile` is kept: gunicorn's own failures — worker crash, bind refused
— happen outside Flask and would otherwise be invisible. Rebuilt and confirmed:

```
{"ts": "...", "level": "INFO", "logger": "vpsim.app", "msg": "request",
 "request_id": "6bfa06be76f244fd", "method": "GET", "path": "/",
 "status": 200, "duration_ms": 6.1}
```

---

## 3 · Why this is not signed off

There is no container runtime on this machine — no Docker Desktop, no podman,
no colima, no daemon. Criteria 2 and 3 are statements about a stack starting up.
Nothing started.

I could have written "complete" on the basis that the files look right. They do
look right, and several specific things were checked (§5). But *"docker compose
up gives a working app"* is a claim about behaviour, and the honest status of an
unexecuted behaviour is unknown.

**What is needed:** install Docker Desktop, then

```bash
docker compose up --build
```

Expected: `db` reaches healthy, `app` starts after it, `http://localhost:8000`
lists the five cases. The CI job added in T-004 also builds the image, so the
first pull request will exercise the build half independently.

Likely first failures, in order of probability: a `pip install` resolution
difference on `linux/amd64`; the healthcheck's start period being too short on a
cold image; `pgvector/pgvector:pg16` needing a different tag.

---

## 4 · The Dockerfile defect from T-004

T-004 needed a Dockerfile for its "image builds" criterion and produced one that
was wrong in a way that would have passed a build and failed at runtime.

```dockerfile
# BEFORE — broken
COPY pyproject.toml README.md* ./
COPY vpsim/__init__.py vpsim/__init__.py
RUN pip install --prefix=/install ".[prod]"
```

The intent was to install dependencies against minimal metadata for layer
caching. The effect is that `pip install .` builds a distribution from a tree
containing **one file**, so `/install` receives a `vpsim` package that is empty
apart from `__init__.py`. The runtime stage then copied the real source to
`/app`, leaving **two importable `vpsim` packages** — a hollow one in
`site-packages` and a complete one in the working directory. Which wins depends
on `sys.path` ordering, which depends on how gunicorn is invoked.

```dockerfile
# AFTER — the whole package is present before installing
COPY pyproject.toml README.md ./
COPY vpsim/ ./vpsim/
RUN pip install --no-cache-dir --prefix=/install ".[prod]"
```

and the runtime stage no longer copies source at all — only `/install`. One
importable copy.

**The cost, stated in the file:** any source change now reinstalls dependencies.
The better-caching alternative (dependencies from `requirements.txt`, then
`pip install --no-deps .`) makes `requirements.txt` load-bearing for the image
when it can already drift from `pyproject.toml`. Correctness won.

### The comment worth keeping

```dockerfile
# --workers 1 is NOT a performance choice. Session state is a dict in process
# memory (infra/session_store.py, blocker B1), so a second worker would serve
# requests that cannot see the session.
#
# TECH_SPEC §9.1 specifies 2 workers x 4 threads. That describes the system
# AFTER T-013 moves session state into an event log — the spec says so itself:
# "multiple workers are only safe because session state left process memory".
# Raise this in T-013, not before.
```

`TECH_SPEC` §9.1 and this file appear to contradict each other. They do not —
the spec describes the post-T-013 system. Without the comment, the first person
tuning throughput raises the worker count and produces an intermittent session
bug that is very hard to trace.

---

## 5 · What *was* verified, and how

Docker could not run. These are the checks that could.

**The package installs from a clean tree with its templates.** Copied
`pyproject.toml`, `README.md` and `vpsim/` into an empty directory and ran the
exact command the builder stage runs:

```
/tmp/vpsim_install/lib/python3.11/site-packages/vpsim/app.py
/tmp/vpsim_install/lib/python3.11/site-packages/vpsim/web/templates/index.html
...
```

Templates are bundled via the `package-data` entry — worth confirming, because a
missing template is a 500 on every page and would not show up until the image ran.

**The installed package serves with no source tree.** This is the closest
available proxy for the runtime stage:

```
vpsim imported from: /tmp/vpsim_install/lib/python3.11/site-packages/vpsim
  GET /                      -> 200, 4666 bytes
  GET /pre_case/case_1       -> 200, 4493 bytes
  GET /start/case_2          -> 200, 24144 bytes
```

An assertion checks `"site-packages" in vpsim.__file__`, so the test fails if it
accidentally resolves the repository instead.

**`.dockerignore` does not exclude what the build needs.** Checked explicitly for
`pyproject.toml`, `README.md`, `vpsim/` — a `.dockerignore` that hides a needed
file produces a confusing `COPY failed`.

**`docker-compose.yml` is valid YAML** with the expected services, healthcheck
and dependency edge.

### One thing attempted and abandoned

A local Postgres 15 is running on this machine, so the init SQL could in
principle have been executed. `createdb` needed a password and sat in a prompt
loop until the command timed out.

Not pursued: it is not our database, and poking at someone's running instance to
validate three `CREATE EXTENSION` statements is a bad trade. Instead the SQL was
**simplified** — a `DO $$ ... RAISE NOTICE` block was removed. It logged a
cosmetic line and was the only part with non-trivial syntax. When you cannot
verify, prefer the version with less to get wrong.

---

## 6 · The compose file

Four decisions worth knowing.

**`pgvector/pgvector:pg16`, not `postgres:16`.** The extension comes compiled and
version-matched. Building it manually is a step that breaks on Postgres upgrades.

**`condition: service_healthy`, not `service_started`.** Started means the
container exists. Postgres accepts connections *during* initialisation and then
restarts, so anything less than a healthcheck races the database.

**`pg_isready`, not a TCP port check**, for the same reason.

**Everything defaults.** `${POSTGRES_USER:-vpsim}` and friends mean compose works
with no `.env` at all — criterion 3 says *clean machine*. `.env.example` is
deliberately **not** created here; that is T-006 criterion 3, and doing it now
would leave two files claiming to document the same variables.

`GROQ_API_KEY` passes through with an empty default. The app boots without it —
the gateway builds its client lazily (T-001) — and case browsing works. The
patient will not reply.

### The database is not connected to anything yet

Criterion 2 says compose brings up app **and** Postgres. It does. It is worth
being explicit that **the application does not talk to the database**: there is
no `psycopg`, no `DATABASE_URL` consumer, no schema. That arrives with T-010 and
T-012.

Postgres is here now so the schema work has somewhere to land and so
`docker compose up` is the only command a new machine needs from here on.
`DATABASE_URL` is already set in the app service so compose does not change when
T-012 starts reading it.

---

## 7 · Verification

```bash
venv/bin/python -m pytest -q             # 231 passed · coverage 99.63%
venv/bin/ruff check .                    # All checks passed!
venv/bin/python validate_detectors.py    # PASS: 94.4% meets the required 94%
```

Validation **51/54 = 94%**, unchanged across all five Phase 0 tasks.

**No Docker verification of any kind.**

---

## 8 · What this changes for you

```bash
docker compose up --build     # app on :8000, Postgres on :5432
docker compose down           # stop
docker compose down -v        # stop AND delete the database volume
```

`down -v` matters more than it looks: the init scripts in
`docker/postgres-init/` run **once**, against an empty data directory. Editing
them later has no effect until the volume is removed. A developer who adds an
extension there and cannot understand why it is missing has hit this.

`python -m vpsim` still works and is still faster for day-to-day work. Compose is
for a clean machine, and for when T-010 makes the database necessary.

---

## 9 · Known debt left behind

| Debt | Closed by |
|---|---|
| **The entire stack is unrun.** Criteria 1–3 are unverified behaviour | **you — install Docker and run `docker compose up --build`** |
| **Base image pinned by tag, not digest.** `python:3.11-slim` is a moving target — `SECURITY_SPEC` §5.2 asks for digests | T-045 |
| **No `.env.example`.** Compose defaults cover it; the app's variables are still undocumented in one place | **T-006** |
| **The app does not use the database.** Postgres runs and is idle | T-010, T-012 |
| **One gunicorn worker.** A deliberate constraint, not a tuning choice | T-013 |
| **`requirements.txt` and `pyproject.toml` still both exist.** Carried from T-004; the Dockerfile now uses `pyproject.toml` only, which reduces the risk but does not remove it | unassigned |
| **No `/healthz`.** The healthcheck hits `/`, which renders the case list — heavier than a liveness probe should be | T-007 |

---

## 10 · How to undo it

```bash
rm -rf docker/ docker-compose.yml
git checkout HEAD -- Dockerfile .dockerignore CLAUDE.md
```

Reverting `Dockerfile` restores the T-004 version **with the two-package defect
in §4**. If you revert, revert to no Dockerfile rather than to that one.

---

## 11 · Next

**T-006 · Typed configuration** (1 day, depends T-001). It delivers
`.env.example` — the gap this task deliberately left — plus `pydantic-settings`
with fail-fast validation and a `gitleaks`-clean repository, which is the first
item on the `SECURITY_SPEC` §8 pre-launch checklist.

Then **T-007** (structured logging and Sentry) closes Phase 0.

Still true, and still not an engineering task: `BUILD_PLAN` §11.1 rates
**content authoring** the real critical path. Ten reviewed cases gate launch and
five exist.

---

*Written 5 September 2026 · Vraj Patel (202301408) · Yogesh Bagotia (202301114)*
