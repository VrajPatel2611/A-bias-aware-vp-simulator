# Rename plan — VPSim → Nidan

**Status: planned, not executed.** Nothing below has been done yet.

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
| **Markdown docs** | **259 across 22 files** | No |
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

## 3 · Phase A — the product name (do this first)

**Effort: about half a day. Risk: low. Nothing executable changes.**

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

## 4 · Phase B — the package (optional, later)

**Effort: one day. Risk: medium. Do not bundle with anything else.**

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

**The database name is the trap.** Changing `POSTGRES_DB` means existing local
volumes point at a database that no longer exists. Anyone with a running stack
needs `docker compose down -v`, which **deletes their local data**. Harmless
today — the app does not use the database yet. **After T-010 it would not be.**

That alone is an argument for doing Phase B now if it is going to be done at
all, or accepting `vpsim` as a permanent internal name.

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
