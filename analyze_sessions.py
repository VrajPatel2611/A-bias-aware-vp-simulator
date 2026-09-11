"""
analyze_sessions.py
--------------------
Analysis pipeline for the bias-aware VP simulator study.

Reads a folder of session JSON logs, pairs each participant's first
(pre-feedback) and second (post-feedback) consultation using the
participant_id / session_sequence fields, and reports:

  * per-participant before/after detail
  * paired group summary for the six outcome measures
  * McNemar's exact test for the three binary bias flags
  * Wilcoxon signed-rank test for the continuous measures
  * confidence vs diagnostic accuracy (overconfidence probe)

Sessions with a blank participant_id are ignored (they cannot be paired).
Records flagged "synthetic": true are counted separately and reported, so
system-test data can never be silently mixed into real results.

Usage:
    python analyze_sessions.py                # reads sessions/
    python analyze_sessions.py sessions_dummy # reads a different folder

Only the Python standard library is required.
"""

import json
import math
import os
import subprocess
import sys
from collections import defaultdict

# Windows consoles default to cp1252, which cannot encode the box-drawing and
# tick characters this script prints — `print("✓")` raises UnicodeEncodeError
# and the run dies with a traceback rather than a result. Retarget the stream.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
BIAS_KEYS = [
    ("anchoring", "Anchoring"),
    ("premature_closure", "Premature closure"),
    ("confirmation_bias", "Confirmation bias"),
]


# ── Loading ───────────────────────────────────────────────────────────

def _tracked_json(folder):
    """
    The JSON files in `folder` that git tracks, or None if git cannot say.

    The research dataset is what has been committed. The running application
    writes a session file to sessions/ after every consultation, so a demo or a
    container test drops files into the same directory — and those are working
    artefacts, not participants.

    This is not hypothetical: six such files were committed during Phase 0 and
    inflated the reported dataset from 16 to 22 before anyone noticed.
    `.gitignore` now stops them being committed; this stops them being counted.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "--", os.path.join(folder, "*.json")],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=10, cwd=os.path.dirname(
                os.path.abspath(__file__)) or ".",
        )
        if out.returncode != 0:
            return None
        names = {os.path.basename(line) for line in out.stdout.split() if line}
        return names or None
    except Exception:
        return None          # not a git checkout, or git unavailable


def load_sessions(folder):
    """
    Loads the session records that make up the research dataset.

    Untracked files are skipped and reported — see _tracked_json for why. If
    git cannot answer (an unpacked archive, say), every file is loaded and a
    warning is printed, because silently analysing a different dataset than the
    one you think you have is the worse failure.
    """
    records = []
    if not os.path.isdir(folder):
        print(f"Folder not found: {folder}")
        return records

    tracked = _tracked_json(folder)
    if tracked is None:
        print("  ! not a git checkout — loading every file in "
              f"{folder}/, including any working artefacts")

    skipped = []
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".json"):
            continue
        if tracked is not None and fname not in tracked:
            skipped.append(fname)
            continue
        try:
            with open(os.path.join(folder, fname), encoding="utf-8") as f:
                records.append(json.load(f))
        except Exception as e:
            print(f"  ! skipped unreadable file {fname}: {e}")

    if skipped:
        print(f"  · ignored {len(skipped)} untracked file(s) in {folder}/ "
              f"— written by the running app, not participant data")
        for fname in skipped[:5]:
            print(f"      {fname}")
        if len(skipped) > 5:
            print(f"      ... and {len(skipped) - 5} more")
    return records


def coverage_percent(rec):
    """History coverage % = topics covered that were required, / required."""
    # Required topics are not stored in the log, so we recompute from the case.
    from nidan.domain.content.cases import get_case
    case = get_case(rec.get("case_id", ""))
    if not case:
        return None
    required = case.get("required_topics", [])
    if not required:
        return None
    covered = rec.get("topics_covered", [])
    hit = [t for t in required if t in covered]
    return 100.0 * len(hit) / len(required)


def key_investigation_percent(rec):
    """% of the case's key investigations that were ordered."""
    ce = rec.get("clinical_eval", {}).get("investigations", {})
    total = ce.get("total_key", 0)
    if not total:
        return None
    done = len(ce.get("key_done", []))
    return 100.0 * done / total


def measures(rec):
    """Extracts the six outcome measures from one session record."""
    biases = rec.get("biases_detected", {})
    return {
        "anchoring": bool(biases.get("anchoring", {}).get("detected")),
        "premature_closure": bool(biases.get("premature_closure", {}).get("detected")),
        "confirmation_bias": bool(biases.get("confirmation_bias", {}).get("detected")),
        "coverage": coverage_percent(rec),
        "key_inv": key_investigation_percent(rec),
        "questions": rec.get("question_count", 0),
        "verdict": rec.get("diagnosis_verdict", "unknown"),
    }


# ── Statistics (standard library only) ────────────────────────────────

def mcnemar_exact(b, c):
    """
    Exact McNemar test (binomial) for paired binary data.
      b = improved (flagged before, not after)
      c = worsened (not flagged before, flagged after)
    Returns two-sided p-value.
    """
    n = b + c
    if n == 0:
        return 1.0
    # two-sided exact binomial p at q=0.5
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def wilcoxon_signed_rank(pairs):
    """
    Wilcoxon signed-rank test for paired continuous data.
    pairs: list of (before, after). Returns (W, p_approx, n_used).
    Uses the normal approximation; with small n this is indicative only.
    """
    diffs = [(a - b) for b, a in pairs if b is not None and a is not None and a != b]
    n = len(diffs)
    if n == 0:
        return None, 1.0, 0

    # rank absolute differences (average ranks for ties)
    order = sorted(range(n), key=lambda i: abs(diffs[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(diffs[order[j + 1]]) == abs(diffs[order[i]]):
            j += 1
        avg = (i + j + 2) / 2.0          # ranks are 1-based
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1

    w_pos = sum(ranks[i] for i in range(n) if diffs[i] > 0)
    w_neg = sum(ranks[i] for i in range(n) if diffs[i] < 0)
    W = min(w_pos, w_neg)

    mean = n * (n + 1) / 4.0
    sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    if sd == 0:
        return W, 1.0, n
    z = (W - mean) / sd
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return W, min(1.0, p), n


def mean(xs):
    vals = [x for x in xs if x is not None]
    return sum(vals) / len(vals) if vals else None


def fmt(x, suffix=""):
    return "n/a" if x is None else f"{x:.1f}{suffix}"


# ── Report ────────────────────────────────────────────────────────────

def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "sessions"
    records = load_sessions(folder)

    # A record counts as synthetic if ANY recognised marker is present.
    # Generators have used different spellings ("synthetic", "_synthetic"),
    # so check all of them - a missed marker would let test data be reported
    # as though it were real participant data.
    def is_synthetic(rec):
        for key in ("synthetic", "_synthetic", "is_synthetic", "dummy", "_dummy"):
            if rec.get(key):
                return True
        note = str(rec.get("note", "")) + str(rec.get("_note", ""))
        return "synthetic" in note.lower() or "example only" in note.lower()

    synthetic = [r for r in records if is_synthetic(r)]
    real = [r for r in records if not is_synthetic(r)]

    print("=" * 66)
    print(f"ANALYSIS OF: {folder}/")
    print("=" * 66)
    print(f"Total session files      : {len(records)}")
    print(f"  synthetic (system test): {len(synthetic)}")
    print(f"  real participant data  : {len(real)}")
    if synthetic:
        print("\n  *** WARNING: this folder contains SYNTHETIC system-test data. ***")
        print("  *** These are NOT research results.                          ***")

    # Group by participant
    by_pid = defaultdict(dict)
    unpaired = 0
    for r in records:
        p = r.get("participant", {})
        pid = (p.get("participant_id") or "").strip()
        seq = p.get("session_sequence")
        if not pid or not seq:
            unpaired += 1
            continue
        by_pid[pid][seq] = r

    paired = {pid: d for pid, d in by_pid.items() if 1 in d and 2 in d}
    print(f"\nParticipants with linked pre/post sessions: {len(paired)}")
    if unpaired:
        print(f"Sessions ignored (no participant id/sequence): {unpaired}")
    if not paired:
        print("\nNo paired sessions available - nothing to analyse.")
        return

    # ── Per-participant table ─────────────────────────────────────────
    print("\n" + "-" * 66)
    print("PER-PARTICIPANT (case 1 = before feedback, case 2 = after)")
    print("-" * 66)
    header = (f"{'ID':<5}{'Yr':<7}{'A':>4}{'P':>3}{'C':>3}  "
              f"{'A':>4}{'P':>3}{'C':>3}   {'Cov%':>10}  {'Qs':>7}  {'Verdict':>18}")
    print(f"{'':<12}{'--before--':^12} {'--after--':^11}")
    print(header)
    for pid in sorted(paired):
        pre = measures(paired[pid][1])
        post = measures(paired[pid][2])
        yr = paired[pid][1].get("participant", {}).get("year_of_study", "")
        def b(v): return "Y" if v else "."
        print(f"{pid:<5}{yr:<7}"
              f"{b(pre['anchoring']):>4}{b(pre['premature_closure']):>3}{b(pre['confirmation_bias']):>3}  "
              f"{b(post['anchoring']):>4}{b(post['premature_closure']):>3}{b(post['confirmation_bias']):>3}   "
              f"{fmt(pre['coverage']):>4}->{fmt(post['coverage']):<5}  "
              f"{pre['questions']:>2}->{post['questions']:<3}  "
              f"{pre['verdict'][:8]:>9}->{post['verdict'][:8]:<8}")
    print("\n  A=Anchoring  P=Premature closure  C=Confirmation bias  (Y=flagged)")

    # ── Group summary + statistics ────────────────────────────────────
    print("\n" + "-" * 66)
    print("PAIRED GROUP SUMMARY")
    print("-" * 66)
    n = len(paired)
    pres = [measures(paired[p][1]) for p in sorted(paired)]
    posts = [measures(paired[p][2]) for p in sorted(paired)]

    print(f"{'Measure':<28}{'Before':>10}{'After':>10}{'Test':>18}")
    for key, label in BIAS_KEYS:
        before_n = sum(1 for m in pres if m[key])
        after_n = sum(1 for m in posts if m[key])
        b = sum(1 for i in range(n) if pres[i][key] and not posts[i][key])   # improved
        c = sum(1 for i in range(n) if not pres[i][key] and posts[i][key])   # worsened
        p = mcnemar_exact(b, c)
        print(f"{label:<28}{f'{before_n}/{n}':>10}{f'{after_n}/{n}':>10}"
              f"{f'McNemar p={p:.3f}':>18}")

    for key, label, suffix in [("coverage", "History coverage", "%"),
                               ("key_inv", "Key investigations", "%"),
                               ("questions", "Questions asked", "")]:
        pairs = [(pres[i][key], posts[i][key]) for i in range(n)]
        mb = mean([x[0] for x in pairs])
        ma = mean([x[1] for x in pairs])
        _, p, used = wilcoxon_signed_rank(pairs)
        test = f"Wilcoxon p={p:.3f}" if used else "no change"
        print(f"{label:<28}{fmt(mb, suffix):>10}{fmt(ma, suffix):>10}{test:>18}")

    correct_before = sum(1 for m in pres if m["verdict"] == "correct")
    correct_after = sum(1 for m in posts if m["verdict"] == "correct")
    print(f"{'Correct diagnoses':<28}{f'{correct_before}/{n}':>10}{f'{correct_after}/{n}':>10}{'':>18}")

    # ── Confidence probe ──────────────────────────────────────────────
    print("\n" + "-" * 66)
    print("CONFIDENCE vs ACCURACY (first case only)")
    print("-" * 66)
    buckets = defaultdict(lambda: [0, 0])
    for pid in sorted(paired):
        rec = paired[pid][1]
        conf = rec.get("participant", {}).get("confidence_pre", "")
        if not conf:
            continue
        correct = rec.get("diagnosis_verdict") == "correct"
        buckets[conf][0] += 1
        buckets[conf][1] += 1 if correct else 0
    if buckets:
        print(f"{'Confidence':<12}{'n':>4}{'correct':>10}{'accuracy':>12}")
        for conf in sorted(buckets):
            tot, corr = buckets[conf]
            print(f"{conf:<12}{tot:>4}{corr:>10}{100.0*corr/tot:>11.0f}%")
    else:
        print("No confidence data recorded.")

    print("\n" + "=" * 66)
    if synthetic:
        print("REMINDER: output above is based on SYNTHETIC system-test data.")
        print("=" * 66)


if __name__ == "__main__":
    main()
