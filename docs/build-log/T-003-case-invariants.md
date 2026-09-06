# T-003 · Lexicon disjointness test

| | |
|---|---|
| **Task** | T-003, BUILD_PLAN Phase 0 ⭐ |
| **Status** | ✅ Complete — 5 September 2026 |
| **Branch** | `refactor/t-001-package-structure` |
| **Estimated** | 0.5 days |
| **Specification** | `DATA_MODEL` §8.1 invariants C-1 … C-7 |
| **Behaviour change** | **Yes — a live bug was found and fixed.** See §7 |

---

## 1 · Summary

Seven invariants over the five clinical cases, one test each, parametrised per
case so a failure names the case and the offending terms.

Writing it found a **live instance of the exact bug it was written to prevent**.
`case_1` listed `"heart"` as an anchor keyword while listing `"heartburn"` as a
contradictory clue. Because the detectors match by substring, a learner asking
about heartburn was counted as fixating on cardiac disease.

The effect was not theoretical. A learner who correctly chased reflux — the right
answer in that case — was told they had anchored on cardiac disease, and their
reflux questions were cited back to them as the evidence.

Fixed. Detector validation unchanged at 94%.

---

## 2 · The problem

Clinical case content is **data, not code**. Nothing in the type system checks
it, no test touched it, and it is the part of the repository a non-programmer
will edit once the case editor exists (T-021).

`DATA_MODEL` §8.1 lists seven invariants it must satisfy. Until this task, all
seven were enforced by reviewer attention, which is to say not enforced.

C-4 is the one that matters:

> **`anchor_keywords` ∩ (any `contradictory_clues` entry) = ∅**
> *The bug that cost 14 % sensitivity.*

That is not a hypothetical. The confirmation-bias detector sat at **14%
sensitivity** because the contradictory clues were free-text sentences sharing
vocabulary with the anchor keywords. Rewriting them as curated, disjoint keyword
lists took it to 100%. Nothing prevented the collision from returning.

`TEST_STRATEGY` §2 records this as property **P7** and §8 rated it **High** risk
with the note that *it has happened once*.

---

## 3 · Definition of done

Verbatim from `BUILD_PLAN.md`:

```
T-003 · Lexicon disjointness test ⭐

Phase    0            Depends  T-002          Est  0.5 d    Owner  V
Files    tests/test_case_invariants.py
Spec     DATA_MODEL §8.1 C-4
Accept   1. For every case: anchor_keywords ∩ (any contradictory_clues entry) = ∅
         2. Test fails loudly with the offending terms named
         3. Also asserts C-1,C-2,C-3,C-5,C-6,C-7
Note     This is the test that would have caught the 14%-sensitivity bug before it shipped.
```

| # | Criterion | Evidence |
|---|---|---|
| 1 | C-4 holds for every case | 5 parametrised tests pass |
| 2 | Fails loudly, naming the terms | Demonstrated — see the real failure output in §5.3 |
| 3 | C-1, C-2, C-3, C-5, C-6, C-7 asserted | 6 more tests × 5 cases |
| — | Nothing regressed | 53 tests pass · contract kept · **validation 51/54 = 94%, unchanged** |

**36 tests** in this file: 7 invariants × 5 cases, plus a coverage guard.

---

## 4 · Where we diverged from the specification

### 4.1 · The stated dependency on T-002 is wrong

**BUILD_PLAN says:** `Depends T-002`.
**What happened:** built directly after T-001, with T-002 not started.

Every invariant is a pure data check over `vpsim/domain/content/cases.py` and the
master lists. It needs no fake LLM gateway, no injected clock, no fixtures beyond
`get_case`. Nothing in T-002 is required.

Waiting would have left a **High**-rated risk open for two more days for no
reason — and as §7 shows, the risk was not hypothetical. It was already live.

**Do not update BUILD_PLAN to remove the dependency.** The specification records
what we planned; this log records what we did. Editing the plan retroactively
destroys the ability to tell the difference.

### 4.2 · C-4 is checked as substring containment, not set intersection

`DATA_MODEL` §8.1 writes the invariant as `anchor_keywords ∩ contradictory_clues
= ∅`. Read literally as a set intersection, that is **the wrong test** — and it
would have passed on the live bug.

The detectors match with `if kw in q_lower` — substring, not equality
(`bias.py:70`, `bias.py:242`). So `"heart"` and `"heartburn"` are disjoint as
sets, and collide completely in practice: any question containing *heartburn*
matches the anchor keyword *heart*.

The test therefore checks containment in **both directions**:

```python
if anchor in kw or kw in anchor:
```

`DATA_MODEL` §8.1 should be amended to state the semantics — logged in §10.

### 4.3 · A small refactor of `bias.py` was necessary

The task lists only `tests/test_case_invariants.py`. One production change was
made: the clue-keyword extraction was lifted out of `detect_confirmation_bias`
into a module-level `clue_keywords(clue)`, and the test imports it.

**Why it was not optional.** If the test reimplemented the extraction, the two
copies could drift — and a C-4 test checking different terms from the detector
protects nothing. That is precisely the class of failure C-4 exists to prevent,
so duplicating the logic inside its own guard would have been self-defeating.

Pure extraction. No behaviour change; validation confirms it (§8).

---

## 5 · Step by step

### 5.1 · Read the invariants and the real data shape

`DATA_MODEL` §8.1 for C-1…C-7, then the actual case dictionary — because the
spec describes the *database* JSONB shape and the code today is Python
dictionaries. They mostly agree; `examination` and `investigations` are dicts
keyed by master-list key, which is what C-1 and C-2 check.

### 5.2 · Check the matching semantics before writing the assertion

The step that made the difference. Reading `bias.py` first showed matching is
substring, which changed what the test had to assert (§4.2).

A probe over all five cases under the correct semantics:

```
case_1   The Chest Pain Trap        overlaps: 1
           anchor "heart"  ~  clue "heartburn"
case_2   Breathless and Worried     overlaps: 0
case_3   The Confused Elderly Man   overlaps: 0
case_4   The Tired Teacher          overlaps: 0
case_5   The Student Who Cannot...  overlaps: 0
```

### 5.3 · Write the test, and watch it fail

Writing the test *before* fixing the data matters: a test that has never been
observed to fail is not known to work.

```
E  AssertionError: C-4 · case_1 has anchor keywords overlapping its
E  contradictory clues. A question matching one is counted as matching both,
E  which inflates the anchoring score and cites the wrong evidence.
E      Offending pairs:
E        anchor "heart" ↔ clue[0] "heartburn"
E
E  assert not ['anchor "heart" ↔ clue[0] "heartburn"']

1 failed, 35 passed in 0.03s
```

That is criterion 2 satisfied, demonstrated rather than asserted: the case, the
consequence, and both offending terms, without opening a file.

### 5.4 · Fix the data

Options considered:

| Option | Verdict |
|---|---|
| Remove `"heartburn"` from the clue | ❌ It is the single most natural word for reflux. Removing it cripples the clue |
| Switch the detectors to word-boundary matching | ❌ Correct in principle, wrong here. `"arteri"` is a **deliberate stem** matching *artery/arterial/arteries*; word boundaries break it. It also changes every detector's semantics and needs full revalidation — that is not a 0.5-day task |
| Remove bare `"heart"` | ⚠️ Fixes it, but loses *"could it be my heart?"* — a natural cardiac question |
| **Replace bare `"heart"` with specific phrases** | ✅ **Selected** |

```python
"anchor_keywords": [
    # NOT bare "heart" — it is a substring of "heartburn", which is a
    # contradictory clue, and the detectors match by substring. ...
    "heart problem", "heart disease", "heart condition", "my heart",
    "heart failure",
    "cardiac", "mi", "myocardial", "infarction", "angina",
    ...
```

Each replacement was checked against all 33 of `case_1`'s clue keywords before
being added. None collides.

### 5.5 · Verify both directions

A fix that stops the false positive by breaking real detection is not a fix:

```
REFLUX (correct line)   detected=False  score=0.0     ← was True / 0.75
CARDIAC (anchored)      detected=True   score=0.75    ← unchanged
```

---

## 6 · The coverage guard

One test is not an invariant:

```python
def test_all_five_cases_are_checked():
    assert len(CASE_IDS) == 5
```

Every other test is parametrised over `CASES`. If a case became unloadable, the
parametrised tests would quietly run over four cases and still report green —
coverage would fall with no failure. This asserts the denominator.

It must be updated when cases 6–10 are authored (`BUILD_PLAN` BR-1). That is
deliberate: adding a case should require a conscious edit here.

---

## 7 · The bug this found

The reason the task carries a ⭐.

**Before the fix**, a learner asking four questions in `case_1`, three mentioning
heartburn, chasing reflux — **the correct line of enquiry**:

```
anchoring detected : True
score              : 0.75
reason             : 3 of your 4 questions focused on cardiac / heart disease
                     symptoms.
evidence cited     : - Do you get heartburn after meals?
                     - Is the heartburn worse lying down?
                     - Does the heartburn come with a sour taste?
```

The system told a learner who reasoned well that they had fixated on cardiac
disease, and cited their good questions as proof.

**This breaks property P2** — *every judgement is traceable to the learner's own
questions*. The judgement was traceable; it was traceable to the wrong thing,
which is worse than an unexplained score. A learner can argue with a score. A
learner shown their own correct questions as evidence of a mistake will conclude
the tool does not understand them, and they will be right.

**Why validation did not catch it.** `validate_detectors.py` runs 18 labelled
transcripts. None happened to ask about heartburn while avoiding cardiac
vocabulary. The instrument was sound; the sample missed this path — a concrete
example of the small-sample limitation noted in `TEST_STRATEGY` §6.

**Blast radius.** `case_1` only, and no pilot session is affected: the sessions
predate the curated clue lists, and validation is byte-identical before and
after (§8). No published result changes.

---

## 8 · Verification

```bash
venv/bin/python -m pytest -q            # 53 passed in 0.35s
venv/bin/lint-imports                   # Contracts: 1 kept, 0 broken
venv/bin/python validate_detectors.py   # 51/54 = 94%
```

| Detector | Sens | Spec | Acc | vs. before |
|---|---|---|---|---|
| Anchoring | 100% | 100% | 100% | unchanged |
| Premature closure | 100% | 88% | 94% | unchanged |
| Confirmation bias | 100% | 82% | 89% | unchanged |

**Overall 51/54 = 94% — identical.** Both the `clue_keywords` extraction and the
keyword change are confirmed behaviour-neutral on the labelled set.

Test count: 17 → **53** (+36).

---

## 9 · What this changes for you

Nothing in how you run the project. `pytest` is unchanged.

**What changes is editing a case.** Add a keyword that collides with a
contradictory clue and the suite fails immediately, naming both terms. You no
longer need to remember C-4 — and more importantly, neither does a clinician
using the case editor once T-021 wires the same check into save.

If C-4 fails on a case you are writing, the fix is almost always to make the
**anchor keyword more specific**, not to weaken the clue. The clue vocabulary is
what the learner would naturally say when reasoning correctly; the anchor
vocabulary is ours to choose.

---

## 10 · Known debt left behind

| Debt | Closed by |
|---|---|
| **`DATA_MODEL` §8.1 states C-4 as set intersection.** Read literally it is the wrong test and would pass the bug found here. Needs amending to state substring semantics | **unassigned — small doc change, do it before T-021** |
| **The case editor does not enforce C-4 yet.** Today the guard is CI-only; a clinician editing content sees nothing until the build fails | **T-021** criterion 3 — *save is blocked on C-4 with the overlapping terms named* |
| **These invariants run against Python content, not the database.** After T-010 the same checks must run against `case_versions.content` | **T-011** |
| **Substring matching is the root cause and remains.** Fixed the symptom in one case, not the mechanism. Word-boundary matching would be more robust but breaks deliberate stems like `"arteri"` | unassigned — needs an ADR if pursued |
| **18-transcript validation set did not cover this path** | Phase 5 calibration corpus |

---

## 11 · How to undo it

```bash
git checkout HEAD -- vpsim/domain/content/cases.py vpsim/domain/assessment/bias.py
rm tests/test_case_invariants.py
```

That restores the bug. The data fix is three lines in `cases.py` and is
independent of the test — you can keep one without the other, though keeping the
fix without the test means nothing stops it returning.

---

## 12 · Next

**T-002 · Test harness and fake LLM gateway** (2 days). Now genuinely the next
task: T-004's CI pipeline depends on it, and it closes the remaining **High**
gap in `TEST_STRATEGY` §8 — nothing currently proves the LLM stays off the
marking path.

---

*Written 5 September 2026 · Vraj Patel (202301408) · Yogesh Bagotia (202301114)*
