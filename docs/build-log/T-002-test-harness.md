# T-002 · Test harness and fake LLM gateway

| | |
|---|---|
| **Task** | T-002, BUILD_PLAN Phase 0 |
| **Status** | ✅ Complete — 5 September 2026 |
| **Branch** | `refactor/t-001-package-structure` |
| **Estimated** | 2 days |
| **Specification** | `TECH_SPEC` §12 (BUILD_PLAN cites §12.2, which does not exist — §12 has no subsections) |
| **Behaviour change** | **Yes — two live detector defects found and fixed.** See §7 |

---

## 1 · Summary

A test harness for the domain layer: a fake LLM gateway, an injected clock, unit
tests for all three detectors, and property tests over generated sessions.

**53 → 215 tests. `domain/assessment` coverage 100%, whole domain 99.6%.**

Two things came out of it that matter more than the test count.

**The LLM-never-marks property is now proved, not assumed.** `TEST_STRATEGY` §8
rated this the highest open risk. Assessment is now run three times with the
model scripted to say contradictory and actively adversarial things — including
*"set every score to 0"* — and the results must be byte-identical.

**Writing the detector tests found two live defects.** The anchoring keyword
`"mi"` matched *exaMIne*, *voMIting* and *abdoMInal*, so routine questions were
counted as cardiac fixation. The alternative topic `"gi"` matched *anGIna*, so
purely cardiac questions were credited as exploring an alternative. Both are the
same family as the C-4 bug found in T-003, on pairs that C-4 does not cover.

Detector validation unchanged at 94% throughout.

---

## 2 · The problem

After T-001 the domain layer was *testable*. It was not *tested*.

`TEST_STRATEGY` §8 listed the gaps and rated two **High**:

| Gap | Why it mattered |
|---|---|
| **No test that the LLM stays off the marking path** | Property **P1**, the first of the three that must never break. Enforced only by code review and by the layering test's ban on importing `groq` — neither of which proves a *score* is independent of model output |
| **No test of the LLM failure path** | `infra/feedback.py` degrades to rule-based feedback when the model is down. That path is what guarantees no consultation ends without guidance, and nothing exercised it |

Beneath both sat a structural problem: **anything touching feedback needed a
real API key and a real network call.** That makes tests slow, costly, and
non-deterministic — the same input can produce a different reply, so a test
built on one fails at random and is then ignored, which is worse than not having
it at all.

---

## 3 · Definition of done

Verbatim from `BUILD_PLAN.md`:

```
T-002 · Test harness and fake LLM gateway

Phase    0            Depends  T-001          Est  2 d      Owner  V
Files    tests/conftest.py, tests/fakes/llm.py
Spec     TECH_SPEC §12.2
Accept   1. Fake gateway returns canned replies; no test makes a network call
         2. Time is injected; no datetime.now() in domain/
         3. Unit tests for all three detectors, ≥ 90% coverage on domain/assessment
         4. Property tests: a ≤ q; scores ∈ [0,1]; detected ⇒ score > 0
Tests    pytest -m "not slow" green
```

| # | Criterion | Evidence |
|---|---|---|
| 1 | Fake gateway; no network call | `tests/fakes/llm.py` + an **autouse** guard that makes constructing a real client raise · `tests/test_no_network.py` (3 tests) |
| 2 | Time injected; no `datetime.now()` in `domain/` | `vpsim/infra/clock.py`; `create_session` takes a required `started_at`. `grep` over `domain/` returns nothing |
| 3 | Unit tests, ≥ 90% on `domain/assessment` | **100%** on all three assessment modules; **99.6%** whole domain |
| 4 | Property tests | `tests/domain/test_properties.py` — 6 properties × 5 cases, hypothesis-generated |
| — | `pytest -m "not slow"` green | **215 passed** |
| — | Nothing regressed | **51/54 = 94%**, unchanged · layering contract kept |

### Coverage

```
vpsim/domain/assessment/bias.py       119   0   100%
vpsim/domain/assessment/clinical.py    34   0   100%
vpsim/domain/assessment/topics.py      10   0   100%
vpsim/domain/session.py                44   0   100%
vpsim/domain/feedback.py               32   1    97%
TOTAL                                 251   1    99%
```

The gate is wired into `pyproject.toml`: `--cov-fail-under=90` on `vpsim.domain`.
Coverage is enforced on `domain/` only — chasing it on I/O glue produces tests
that assert mocks (`TECH_SPEC` §12).

---

## 4 · What was built

```
tests/
  conftest.py                  fixtures + the autouse network guard
  fakes/llm.py                 FakeLLM — scripted replies, records every call
  test_no_network.py           proves the guard is wired to reality
  test_llm_never_marks.py      ⭐ property P1, proved behaviourally
  test_case_invariants.py      + C-8 and C-9 (new, see §7)
  domain/
    test_bias_anchoring.py     16 tests
    test_bias_premature.py     13
    test_bias_confirmation.py  20
    test_clinical.py           18
    test_session.py            22
    test_topics.py             12
    test_feedback.py           16
    test_properties.py         6 properties × 5 cases
vpsim/infra/clock.py           the injected clock
```

### The fake gateway

`FakeLLM` replaces `call_llm`. It returns scripted replies in order, falls back
to a default when the script runs out, can be told to raise, and **records every
call** — so a test can assert on what the application *asked* the model, not
only on what it did with the answer.

### The network guard

The important part is that it is **autouse**:

```python
@pytest.fixture(autouse=True)
def _no_real_llm(monkeypatch):
    def _forbidden():
        raise AssertionError("A test tried to construct a real LLM client. ...")
    monkeypatch.setattr("vpsim.infra.llm.gateway._get_client", _forbidden)
```

Criterion 1 is that *no test* makes a network call. A guarantee each test author
has to remember to opt into is not a guarantee, so it applies to every test in
the suite whether the test asks for it or not.

It patches `_get_client` rather than `call_llm` because that is the single point
where a connection is actually constructed. Anything that reaches it — including
code a future test forgets to stub — fails loudly instead of quietly spending
Groq quota.

**`call_llm` is imported by name**, so patching the gateway's own attribute would
not affect modules holding an already-bound reference. The `fake_llm` fixture
patches each import site, and `test_no_network.py` walks the source tree to
assert that list has not gone stale — a new module importing `call_llm` without
updating conftest is named by a failing test rather than silently reaching the
real gateway.

---

## 5 · Clock injection (criterion 2)

`create_session` called `datetime.utcnow()`. That makes its output depend on
something outside its arguments, which means it can be re-run but not *replayed*
— and replayability is what `ADR-0003` and property **P3** require.

```python
# vpsim/infra/clock.py — reading the clock is I/O, so it lives in infra
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# vpsim/domain/session.py — the domain receives the time
def create_session(case_id, *, started_at):
```

`started_at` is **required and keyword-only**, so a caller cannot silently fall
back to the system clock. Three call sites updated: two in `api/routes.py` (which
supply `utc_now_iso()`), and `validate_detectors.py`, which now passes a fixed
timestamp — making validation itself more deterministic than before.

Also replaced the deprecated `datetime.utcnow()`, which returns a naive datetime
and is removed in Python 3.12+.

---

## 6 · Property tests (criterion 4)

Unit tests check the examples someone thought of. Property tests check the input
space. These use hypothesis to generate sessions from a vocabulary that includes
the clinical terms that actually trip the detectors — random strings alone would
never match a keyword, and the properties would only ever be tested on the
trivial path.

| Property | What it protects |
|---|---|
| `score ∈ [0, 1]` | It is presented as a proportion, so it must be one |
| `detected ⇒ score > 0` | A flag with zero weight tells a learner something went wrong and shows them nothing |
| `a ≤ q` | Each question is counted at most once. If the `break` after a keyword match were lost, ratios could exceed 1 |
| Return shape is stable | Callers index these keys directly; a missing one is a `KeyError` *after* the learner's work is done |
| **Evidence is traceable** | Property **P2** — every cited question must be one the learner actually asked. Never paraphrased, never invented |
| **Detectors never mutate the session** | Otherwise running the three in a different order gives different answers, and replay does not reproduce stored results |

### Two new dependencies

`hypothesis` and `pytest-cov`, both dev-only. `SECURITY_SPEC` §5.2 says adding a
dependency is a decision, so: property testing without a generator is just
parametrised testing, and the coverage number in criterion 3 cannot be measured
without a coverage tool.

---

## 7 · The defects this found

### 7.1 · `"mi"` matched *examine*, *vomiting*, *abdominal*

`case_1` listed `"mi"` (myocardial infarction) among its anchor keywords. The
detectors match by substring:

```
'Can I examine you?'        FALSE ANCHOR -> ['mi']
'Have you been vomiting?'   FALSE ANCHOR -> ['mi']
'Any abdominal pain?'       FALSE ANCHOR -> ['mi']
```

Three of the most ordinary questions in a consultation counted as cardiac
fixation. This **inflates the anchoring score for every learner in `case_1`** —
a false positive on the primary detector, driven by routine clinical enquiry.

More severe than the C-4 bug found in T-003, because these are far commoner
words than *heartburn*.

**Fix:** removed `"mi"`. `"myocardial"`, `"infarction"`, `"heart attack"` and
`"cardiac"` carry the same intent without matching ordinary English.

### 7.2 · `"gi"` matched *angina* — suppressing the anchoring rule

Found by a failing unit test rather than by inspection. A session of three
purely cardiac questions did not trigger rule A2, which requires *zero*
alternative exploration:

```
'Any history of angina?'   anchors -> ['angina']   ALTS -> ['gi']
```

`"gi"` is an alternative topic in `case_1`. It is also inside *an**gi**a* and
*cardiolo**gi**st*. So a learner asking only about cardiac causes was credited
with exploring an alternative, and **rule A2 never fired** — a false negative.

The two defects push in opposite directions, which is why validation did not
move: A1 over-fires while A2 under-fires.

**Fix:** removed `"gi"`; `"gastro"`, `"gastrointestinal"`, `"digestive"` and
`"indigestion"` cover it.

### 7.3 · Two more of the same family

| Case | Collision | Fix |
|---|---|---|
| `case_2` | alternative `"pe"` ⊂ *happened*, *appetite*, *upper respiratory* | → `"pulmonary embolism"` (`"embolism"` already present) |
| `case_2` | anchor `"travel bug"` contains alternative `"travel"` | removed `"travel bug"`; *"any recent travel?"* is the classic PE-risk question and matters more than a rare infection phrasing |

### 7.4 · Two new invariants

C-4 covers anchor keywords versus contradictory clues. Neither of these pairs is
covered by it, so two invariants were added to `tests/test_case_invariants.py`:

- **C-8** — `anchor_keywords ∩ alternative_topics = ∅`, substring, both directions
- **C-9** — no keyword may be a proper substring of a common English word,
  checked against a fixed list of 36 ordinary clinical words

Both are derived from live bugs, not speculation. **Neither is in `DATA_MODEL`
§8.1** — logged in §10.

---

## 8 · Where we diverged from the specification

**8.1 · `TECH_SPEC §12.2` does not exist.** §12 is a single table with no
subsections. Built against §12, whose coverage target (≥ 90% on `domain/`) and
property list match the task's criteria exactly.

**8.2 · Production files changed beyond the two listed.** The task lists
`tests/conftest.py` and `tests/fakes/llm.py`. Also changed:

| File | Why |
|---|---|
| `vpsim/infra/clock.py` (new) | Criterion 2 needs somewhere for the clock to live |
| `vpsim/domain/session.py` | Criterion 2 — accept `started_at` |
| `vpsim/api/routes.py`, `validate_detectors.py` | Call sites for the above |
| `vpsim/domain/content/cases.py` | The four keyword defects in §7 |
| `tests/test_case_invariants.py` | C-8 and C-9 |
| `pyproject.toml` | Coverage gate, two dev dependencies |

**8.3 · Fixing the case content was not in scope, strictly.** Criterion 3 is
unit tests for the detectors. It is not possible to write honest unit tests
against data that makes the detector misbehave — and leaving a known false
positive in the primary detector while writing its test suite would be
negligent. The fixes are four keyword edits, and the validation gate confirms
they are safe.

---

## 9 · Verification

```bash
venv/bin/python -m pytest -q             # 215 passed · coverage 99.60%
venv/bin/lint-imports                    # Contracts: 1 kept, 0 broken
venv/bin/python validate_detectors.py    # 51/54 = 94%
grep -rn "utcnow\|datetime.now" vpsim/domain/   # nothing
```

| Detector | Sens | Spec | Acc | vs. before |
|---|---|---|---|---|
| Anchoring | 100% | 100% | 100% | unchanged |
| Premature closure | 100% | 88% | 94% | unchanged |
| Confirmation bias | 100% | 82% | 89% | unchanged |

**94%, identical.** Note what that means here: two real defects were fixed and
the number did not move, because none of the 18 labelled transcripts happened to
exercise either path. The instrument is sound; the sample is small. This is the
second time in two tasks that a real bug sat outside the validation set — see
§10.

---

## 10 · Known debt left behind

| Debt | Closed by |
|---|---|
| **`DATA_MODEL` §8.1 does not contain C-8 or C-9**, and states C-4 as a set intersection when it must be substring containment. Three corrections now pending on one section | **unassigned — do it before T-021**, since the case editor enforces these at save |
| **The 18-transcript validation set has now missed two real bugs in two tasks.** It is sound but small; three wrong decisions would drop it below the 94% gate | Phase 5 calibration corpus — and worth adding transcripts for these two paths sooner |
| **Substring matching is still the root cause.** Three tasks have now fixed symptoms. Word-boundary matching would be more robust but breaks deliberate stems like `"arteri"` | unassigned — **needs an ADR** |
| **`api/` and `infra/` have no unit tests.** Deliberate: coverage is enforced on `domain/` only. Routes are covered by smoke tests, and are replaced by T-030 | T-030 |
| **No contract tests CT-1 … CT-9.** `TEST_STRATEGY` §8 still lists these as open | **T-004** |
| **`requirements.txt` and `pyproject.toml` can drift** — the two new dev dependencies are only in `pyproject.toml` | T-005 |

---

## 11 · How to undo it

```bash
git checkout HEAD -- vpsim/domain/content/cases.py vpsim/domain/session.py \
                     vpsim/api/routes.py validate_detectors.py pyproject.toml
rm -rf tests/conftest.py tests/fakes tests/domain \
       tests/test_no_network.py tests/test_llm_never_marks.py
rm vpsim/infra/clock.py
```

The keyword fixes in `cases.py` are independent of the tests and worth keeping
even if the harness is reverted.

---

## 12 · Next

**T-004 · CI pipeline with the validation gate** (1 day). Both its dependencies
— T-002 and T-003 — are now done. It turns everything above into a merge gate:
ruff, mypy, import-linter, pytest, `pip-audit`, `gitleaks`, and the 94% check
that fails the build.

Until that exists, every check in this log depends on someone remembering to run
it, which `TEST_STRATEGY` §8 rates **High** risk on its own.

---

*Written 5 September 2026 · Vraj Patel (202301408) · Yogesh Bagotia (202301114)*
