# Branch protection — the manual half of T-004

The workflow in `workflows/ci.yml` makes the checks *run*. It cannot make them
*required*. Requiring them is a repository setting, and until it is switched on
a red build can still be merged — which makes every gate in this repository
advisory.

**This is the last step of T-004 and it has to be done by hand, once, by the
repository owner.**

---

## Steps

GitHub → the repository → **Settings** → **Branches** → **Add branch ruleset**
(or *Add rule* on older UI).

1. **Branch name pattern:** `main`
2. Tick **Require a pull request before merging**
   - Required approvals: **1**
   - (With two of you, this means neither merges their own work unreviewed.)
3. Tick **Require status checks to pass before merging**
   - Tick **Require branches to be up to date before merging**
   - Add every check below.
4. Tick **Do not allow bypassing the above settings**
   - Without this, an admin merges past a red build without noticing.

### The required checks

Names must match the workflow's `name:` fields exactly. They appear in the
picker only after the workflow has run at least once — **open a pull request
first**, let CI run, then come back.

| Check | Guards |
|---|---|
| `Lint and types` | style, `mypy --strict` on `domain/`, the ADR-0009 layering contract |
| `Tests` | 231 tests, ≥90% coverage on `domain/` |
| `Detector validation (research claim)` | **the 94% figure. The important one** |
| `Case content invariants` | C-1 … C-9, including the C-4 disjointness rule |
| `Security` | `pip-audit`, `gitleaks` |
| `Docker image builds` | the image still builds |

---

## Why this is worth ten minutes

`TEST_STRATEGY` §8 rates "no CI" as **High** risk, and the reason is not that
the checks are missing — they all exist and pass locally. It is that a check
which depends on somebody remembering to run it is not a gate.

The detector-validation check is the one that matters most. The published paper
reports 94% accuracy. Once that check is required, **no change can merge that
degrades the instrument the research claim rests on** — including a change
neither of you noticed was degrading it. That has now happened three times in
three tasks (T-002, T-003, T-004), each time found by a test rather than by
review.

---

## Verifying it worked

Open a pull request with a deliberately broken detector:

```bash
git checkout -b test/verify-ci-gate
sed -i '' 's/if concentration > 0.60:/if concentration > 0.99:/' \
  vpsim/domain/assessment/bias.py
git commit -am "TEST: deliberately degrade anchoring — do not merge"
git push -u origin test/verify-ci-gate
```

Expected: `Detector validation (research claim)` fails, and the merge button is
disabled. Then delete the branch.

A gate you have never seen block anything is not known to work — the same
reasoning as `tests/test_validation_gate.py`, which proves the script's exit
code in both directions.
