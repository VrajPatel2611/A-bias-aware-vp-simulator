# Rename plan — VPSim → Nidan

**Status: Phase A and Phase B both executed, 11 September 2026. The rename is complete.**

D-8 was decided on 9 September 2026 (`PRD` §11). This is the plan for making it
real in one deliberate change rather than letting the new name leak in gradually
while the old one persists in half the repository.

---

## 1 · The scope, measured

Not estimated — counted.

| Where | Occurrences | Renaming it breaks something? |
|---|---:|---|
| **Python package `vpsim/`** | 37 files | **Yes** — every import, the console script, the coverage gate, the layering contract |
| `pyproject.toml` | 11 | **Yes** — package name, entry point, `--cov` target, import-linter root |
| `docker-compose.yml` | 10 | **Yes** — container names, Postgres user/db, `DATABASE_URL` |
| `Dockerfile` | 8 | **Yes** — `COPY`, the runtime user, the gunicorn target |
| `.env.example` | 10 | No — documentation of defaults |
| `.github/workflows/ci.yml` | 3 | Minor — image tag |
| `CLAUDE.md` | 4 | No |
| **Markdown docs** | **48 across 15 files** — *corrected; the original 259 was a case-insensitive count that swept in the package identifier* | No |
| **`.docx` files named `VPSim_*`** | 25 | No — regenerated anyway |
| **GitHub repository name** | — | Yes for anyone who has cloned |

---

## 2 · The decision that shapes everything else

**There are two different names here, and they do not have to change together.**

| | |
|---|---|
| **The product** — what users see | `VPSim` → **Nidan** |
| **The Python package** — `import vpsim` | `vpsim` → `nidan`? *Optional* |

The package identifier is internal. No user ever sees it. Renaming it touches
37 files, the Docker user, the database name, the coverage configuration and the
layering contract — and every one of those is a chance to break a build for zero
user-visible benefit.

**Recommendation: rename the product now, rename the package later — or never.**

Precedent is on that side. Facebook's internal codebase kept `thefacebook`
references for years. What matters is that the *product* is consistently Nidan
everywhere a human reads it.

If the package is renamed, do it as its own task, on its own branch, verified by
the full CI suite — never bundled with a documentation change.

---

## 3 · Phase A — the product name — ✅ DONE (11 September 2026)

**Actual effort: under an hour. 36 replacements across 13 files, 26 `.docx`
regenerated.** Smaller than planned, because the 259 figure was wrong (§1).

Domains were deliberately **not** secured first, against the advice in A1. The
name was already public in a pushed commit by then, so delaying the rename no
longer reduced the squatting risk — it only delayed the work. **`nidan.app` is
still unbought.**

Two user-facing strings in the code were changed as well as the documentation,
because a configuration error and a start-up banner are read by humans:

```
 * Nidan running on http://127.0.0.1:8000
Nidan cannot start — configuration is invalid:
```

All six CI checks passed after the change.

### A1 · Secure the domains before anything is public

```
nidan.app        the product
nidan.md         memorable, and reads as "MD"
nidan.health     optional, defensive
```

**Do this first.** The moment the name appears in a public repository, a public
PR title or a conversation outside the team, it is discoverable. Domains are
cheap; a name you cannot use is not.

Also check, in the same sitting:

- **Trademark** — a search in your launch jurisdiction. I cannot do this
- **App Store** — is there an app called Nidan already?
- **Social handles** — `@nidan` or `@nidanapp` on the platforms you would use

### A2 · Documentation and user-facing text

259 occurrences, 22 files. Mechanical, but **not** a blind find-and-replace:

- `VPSim` → `Nidan` — the product name in prose, titles, headers
- `vpsim/` → leave alone — that is the package path
- `vpsim.app:app`, `import vpsim` → leave alone — those are code
- `VPSim_*.docx` → regenerate as `Nidan_*.docx`

The build logs are a special case. **T-001 to T-007 describe work done under the
old name.** Rewriting them would make the record inaccurate — they would claim
to have built "Nidan" before Nidan existed. Add a one-line note at the top of
`docs/build-log/README.md` saying the product was renamed on 9 September 2026
and earlier logs use the working title, then leave their contents alone.

### A3 · Regenerate the 25 `.docx` files

`docs/spec/md2docx.js` takes the title as an argument, so this is a loop, not 25
manual edits.

### A4 · The GitHub repository

`A-bias-aware-vp-simulator` → `nidan`

GitHub redirects the old URL, so existing clones keep working. But anyone with a
clone should still run:

```bash
git remote set-url origin https://github.com/VrajPatel2611/nidan.git
```

Do this **after** the documentation change is merged, so the repository is
already internally consistent when its name changes.

---

## 4 · Phase B — the package — ✅ DONE (11 September 2026)

**Actual effort: under an hour. Risk turned out low**, because the test suite
made it verifiable: 293 tests, the layering contract, mypy strict and the
detector gate all had to agree before it could be called finished.

Done immediately after Phase A rather than "later, or never" as this document
originally recommended. The reason for the change of mind is in §4.1.

Only if you decide it matters. The order is load-bearing:

1. `git mv vpsim nidan` — preserves history, as in T-001
2. Rewrite imports across 37 files
3. `pyproject.toml` — `name`, `[project.scripts]`, `packages.find`,
   `package-data`, `--cov=nidan.domain`, `importlinter.root_package`
4. `tests/test_layering.py` and `tests/test_no_network.py` — both hard-code the
   package path
5. `Dockerfile` — `COPY`, `useradd`, `gunicorn nidan.app:app`
6. `docker-compose.yml` — container names, Postgres user and database
7. `python -m nidan`, `pip install -e ".[dev]"`, full CI green

### 4.1 · Why it was done now rather than never

The Python package rename has **no deadline** — renaming `import nidan` in 2030
would cost exactly what it cost today. But the database name does:

**Changing `POSTGRES_DB` orphans existing local volumes.** Anyone with a running
stack needs `docker compose down -v`, which **deletes their local data**.
Harmless on 11 September, because nothing uses the database yet. After T-010
creates the schema and T-018 imports the pilot sessions, it becomes a
dump-and-restore. After launch it is a production migration with downtime.

So the choice was: do it while it is free, or accept `vpsim` permanently.

**What made it safe:** 293 tests, an import-linter contract, mypy strict on the
domain layer, a Docker build in CI and a detector-accuracy gate. A mechanical
rename against that much verification is a low-risk change. It would not have
been in a codebase without them — which is Phase 0's return on investment,
collected.

### 4.2 · What actually changed

```
git mv vpsim nidan                34 files, renames detected by git
imports rewritten                 37 python files
pyproject.toml                    name, console script, --cov target,
                                  package-data, import-linter root_package
Dockerfile                        COPY, runtime user, gunicorn target
docker-compose.yml                container names, POSTGRES_USER,
                                  POSTGRES_DB, DATABASE_URL, dev password
docs                              TECH_SPEC, TEST_STRATEGY, BUILD_PLAN,
                                  COMMANDS, WINDOWS_SETUP, PROJECT_MAP,
                                  BRANCH_PROTECTION, .gitleaks.toml
```

**Two things that needed a human, not a regex:**

`\bvpsim\b` does not match `vpsim_local_dev_only`, because `_` is a word
character. The dev database password kept the old name until it was caught by
reading the output rather than trusting the count.

Import ordering changed. `nidan` sorts before `tests`, where `vpsim` sorted
after, so `ruff` failed on block ordering until it was re-sorted.

### 4.3 · What anyone with a running stack must do

```bash
docker compose down -v          # the volume points at a database called vpsim
pip install -e ".[dev]"         # the editable install points at the old name
docker compose up --build
```

The `-v` is required. Without it Postgres keeps the old `vpsim` database and the
app connects to a database that does not exist.

---

## 5 · Order of operations

```
1. Secure nidan.app and nidan.md                     ← do this today
2. Trademark and App Store check
3. Phase A — docs, .docx, CLAUDE.md          one PR, low risk
4. Rename the GitHub repository              after (3) merges
5. Phase B — the package                     separate PR, or never
```

Steps 3 and 5 must not share a pull request. One is a documentation change that
cannot break the build; the other touches the import graph, the container and
the database. Reviewing them together means reviewing neither.

---

## 6 · What stays "VPSim" permanently

Worth stating so nobody "fixes" these later:

- **The research paper** (`report/main.tex`) and its results — it was published
  under that name. Changing it retrospectively misrepresents the record
- **The 16 pilot session files** — data collected under the old name
- **Build logs T-001 to T-007** — see A2
- **Git history** — commit messages are immutable and should stay that way

---

## 7 · Not yet decided

- **`nidan.health`** — buy defensively or not?
- **Package rename** — Phase B, yes or no?
- **Tagline.** Nidan means *diagnosis*, which describes the subject rather than
  the product. Something is needed alongside it — *"practise how you think"* is
  the idea, not the wording
- **Wordmark** — lowercase `nidan` sets cleanly: five letters, two syllables,
  no ascender/descender collisions. Worth trying before committing to a logo
