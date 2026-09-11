# Command reference

Every command for this project, grouped by what you are trying to do.

Run everything from the project directory unless a command says otherwise:

```
cd ~/Desktop/A-bias-aware-vp-simulator
```

Getting the directory wrong is the single most common cause of a confusing
error. `docker compose up` from your home folder fails with *"no configuration
file found"*, not *"you are in the wrong place"*.

---

## 1 · First time on a new machine

```
git clone https://github.com/VrajPatel2611/A-bias-aware-vp-simulator.git
cd A-bias-aware-vp-simulator
```

**Create the virtual environment.** Python 3.11 or newer — the package refuses
to install on older versions, deliberately, because the code uses syntax they
cannot parse.

```
python3.11 -m venv venv
source venv/bin/activate
```

*Windows:* `py -3.11 -m venv venv` then `venv\Scripts\activate`

**Install the package and the development tools.**

```
pip install -e ".[dev]"
```

`-e` is *editable*: it puts a link to this folder on the Python path rather than
copying files, so an edit is live with no reinstall. `[dev]` adds pytest, ruff,
mypy and the rest — a production install does not ship them.

**Create your configuration.**

```
cp .env.example .env
```

Then open `.env` and paste your Groq key into `GROQ_API_KEY`. Free key from
https://console.groq.com

You can skip the key. The app starts, the case list works and the whole test
suite passes without one — only the patient's replies need it.

**Check it worked.**

```
pytest
```

293 tests, about 8 seconds. If they pass, the install is good.

---

## 2 · Running the app

**Day to day** — fastest, auto-reloads when you edit a file:

```
python -m nidan
```

Then open http://localhost:8000

**The full stack** — app plus PostgreSQL 16 with pgvector. Slower to start, and
what you want when the database work begins in T-010:

```
docker compose up --build
```

Same URL. Postgres is on `localhost:5433` on Vraj's machine, `localhost:5432`
elsewhere — see §7.

**Stop it:** `Ctrl+C`, or from another terminal:

```
docker compose down
```

**Stop it and wipe the database:**

```
docker compose down -v
```

The `-v` matters more than it looks. The scripts in `docker/postgres-init/` run
**once**, against an empty data directory. Edit them and nothing happens until
the volume is removed.

---

## 3 · Tests and quality

These are the six checks CI runs. Run them before you push and you will not be
surprised.

| Command | What it checks | Time |
|---|---|---|
| `pytest` | all 293 tests, plus the ≥90% coverage gate on `domain/` | ~8 s |
| `ruff check .` | style and common mistakes | <1 s |
| `ruff check . --fix` | the same, fixing what it can | <1 s |
| `mypy nidan/domain --strict` | types, on the domain layer only | ~5 s |
| `lint-imports` | the ADR-0009 layering contract | ~1 s |
| `pip-audit --skip-editable` | known vulnerabilities in dependencies | ~10 s |
| `python validate_detectors.py` | **detector accuracy — must stay ≥ 94%** | ~2 s |

### Running part of the suite

```
pytest -v
```
One line per test, with names.

```
pytest tests/domain/test_bias_anchoring.py
```
One file.

```
pytest -k anchoring
```
Every test whose name contains "anchoring".

```
pytest -x
```
Stop at the first failure.

```
pytest --lf
```
Re-run only what failed last time. Useful while fixing.

```
pytest tests/test_case_invariants.py -v --no-cov
```
The nine case invariants. `--no-cov` because running one file trips the coverage
gate, which is measured across the whole suite.

### The one that matters most

```
python validate_detectors.py
```

18 hand-labelled transcripts through the real detectors. It **exits non-zero
below 94%**, so CI fails the build.

If it fails, **do not lower the threshold.** The published paper reports 94%.
Find out what changed. The failure message says the same thing.

---

## 4 · Research tooling

```
python analyze_sessions.py sessions
```
Paired statistics — McNemar and Wilcoxon — over the session JSON files.

```
python test_api.py
```
Check the Groq key works. The quickest way to tell a key problem from a code
problem.

---

## 5 · Git

**Start a piece of work.** Never commit to `main` directly.

```
git checkout main && git pull && git checkout -b feature/short-description
```

**See what you have changed.**

```
git status
```

```
git diff
```

**Commit.**

```
git add -A && git commit -m "short description of what changed"
```

**Push and open a pull request.**

```
git push -u origin HEAD
```

Then open the PR on GitHub. CI runs automatically; all six jobs must pass.

**Undo, in increasing order of violence:**

```
git checkout -- path/to/file
```
Throw away changes to one file.

```
git stash
```
Set all changes aside. `git stash pop` brings them back.

```
git reset --hard
```
**Throws away every uncommitted change with no way back.** Be sure.

---

## 6 · Docker, in more detail

```
docker compose up --build
```
Build and start everything, logs in the terminal.

```
docker compose up -d --build
```
The same, in the background.

```
docker compose logs -f app
```
Follow the app's logs.

```
docker compose ps
```
What is running, and whether it is healthy.

```
docker compose exec db psql -U nidan -d nidan
```
A SQL prompt inside the database container. `\dx` lists extensions, `\q` quits.

```
docker compose build --no-cache
```
Rebuild from scratch. For when you suspect a stale layer.

---

## 7 · Things that go wrong, and the fix

### `zsh: command not found: docker`

Docker is not installed.

```
brew install --cask docker
```

Then **launch it** — installing gives you the command, not the running engine:

```
open -a Docker
```

Wait for the whale icon to stop animating, then check:

```
docker info
```

### `Cannot connect to the Docker daemon`

Docker Desktop is not running. `open -a Docker` and wait.

### `ports are not available: ... 5432: bind: address already in use`

Something else already uses PostgreSQL's port — on Vraj's Mac, Homebrew
`postgresql@15`. Fixed by adding this to `.env`:

```
POSTGRES_PORT=5433
```

The container then publishes on 5433. Nothing in the app changes: inside the
compose network the database is still `db:5432`.

To see what is holding a port:

```
lsof -nP -iTCP:5432 -sTCP:LISTEN
```

### `no configuration file found`

You are not in the project directory. `cd ~/Desktop/A-bias-aware-vp-simulator`

### `ERROR: Package 'nidan' requires a different Python: 3.9.6 not in '>=3.11'`

You are using the system Python instead of the virtual environment.

```
source venv/bin/activate
```

Or call the venv's interpreter directly: `venv/bin/python`, `venv/bin/pip`.

### `ModuleNotFoundError: No module named 'nidan'`

The package is not installed in the active environment.

```
pip install -e ".[dev]"
```

### Tests pass, then fail, with nothing changed

Stale compiled bytecode — usually after restoring a file with `cp`, which can
leave the source older than its cached `.pyc`.

```
find . -name __pycache__ -not -path "./venv/*" -exec rm -rf {} +
```

Restore files with `git checkout` rather than `cp` and this does not happen.

### `FAIL: detector accuracy 92.6% is below the required 94%`

A change degraded the detectors. **Do not lower the threshold.** Look at what
you changed in `nidan/domain/assessment/` or `nidan/domain/content/cases.py`.
`docs/detector_validation.md` shows which transcripts now fail.

### A case invariant fails (C-1 … C-9)

You edited a case and broke a rule. The message names the offending terms. The
fix is almost always to make the **anchor keyword more specific**, not to weaken
the clue — the clue vocabulary is what a learner naturally says when reasoning
correctly.

---

## 8 · The short version

Pin these five up somewhere:

```
source venv/bin/activate
python -m nidan
pytest
python validate_detectors.py
docker compose up --build
```

---

*Last updated 6 September 2026, after Phase 0.*
