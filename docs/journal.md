# Project Journal — Bias-Aware Virtual Patient Simulator
# Roll No: 202301408 | Mentor: Abhishek Gupta | DA-IICT

---

## Day 1 — May 11, 2026 ✅ COMPLETE

**What I completed today:**
Read and fully annotated all 4 core reference papers. Ran 6 Google
Scholar queries and found 7 additional papers. After verification,
5 were accepted and 2 rejected (1 unverifiable, 1 low relevance).
references.md now has 9 fully annotated papers with gap analysis.
Identified the core research gap. Day 1 complete.

**Papers found and verified today:**
- [5] Bach et al. (2023) — Anchoring bias mitigation in clinical AI,
  CHI conference — HIGH relevance
- [6] Rosbach et al. (2026) — Automation bias and anchoring in
  pathology AI — MEDIUM relevance
- [7] Qazi et al. (2026) — Automation bias in LLM-assisted diagnosis,
  NEJM AI RCT — HIGH relevance
- [8] Newman-Toker (2013) — Real case of premature closure causing
  missed cancer diagnosis — use in Introduction only
- [9] Pereira (2025) — Smart-Doc Master's thesis, FEUP Porto —
  HIGH relevance, closest competitor. MUST READ full PDF before Week 7.

**Papers rejected:**
- Sanchez paper: no DOI, not indexed, cannot verify — rejected
- Loomis et al. 2024: low relevance, no AI component — skipped

**The single most important thing I learned from the papers:**
Katarci & Topalli (2025) reviewed 10 virtual patient systems (2021-2025)
and confirmed NONE detect cognitive bias during the consultation.
Every system checks only if the final diagnosis is correct.
This directly justifies why this project exists.

**Second most important finding:**
The Qazi et al. NEJM AI RCT (2026) showed that even physicians who
completed 20-hour AI-literacy training still suffered automation bias
from erroneous LLM suggestions. If trained physicians cannot resist
bias with AI, then training systems must actively develop critical
reasoning — which is exactly what the Socratic feedback engine does.

**Critical alert — closest competitor found:**
Bruno de Sena Pereira's 2025 FEUP Master's thesis "Smart-Doc:
AI-Powered Medical Education through Diagnostic Interactions" is
almost the same project title. MUST download and read the full PDF
before writing the final report. If Smart-Doc does bias detection,
this project must clearly differentiate its approach.
PDF: https://repositorio-aberto.up.pt/bitstream/10216/170910/2/749584.pdf

**Key insight — theory-to-implementation gap:**
Greengrass (2026) explicitly states that AI detecting "behavioural
markers of premature closure" would be valuable and describes exactly
what that looks like. But he builds nothing. This project builds it.
This is the clearest possible justification for the project.

**One decision made today and why:**
Targeting only 3 bias types (anchoring, premature closure, confirmation
bias) not all 6 Greengrass lists. Reason: these 3 are operationalizable
as text-based behavioral patterns. The other 3 (availability bias,
overconfidence, representativeness) require background knowledge about
the user that cannot be reliably inferred from question text alone.

**Design constraint learned from Bach et al. (2023):**
Clinicians found bias mitigation frustrating when it interrupted their
workflow. This means bias feedback in this project must appear AFTER
the consultation, not during it. Mid-consultation interruptions will
feel intrusive and may be ignored. Post-session Socratic feedback
avoids this problem entirely.

**What I am most uncertain about going into Day 2:**
Whether the 5 case designs will produce reliable bias detection.
If an anchor trap is too obvious, no one anchors and there is nothing
to detect. If it is too subtle, users will be confused rather than
biased. The case design quality is the single most important variable
in the whole project.

**One thing I would do differently:**
Read Greengrass (2026) before the initial project scoping conversation.
It alone provides the complete theoretical framework and even identifies
the exact gap this project fills. Could have saved hours of discussion.

**End of day commit message:**
"Day 1 complete: references.md with 9 verified papers, journal.md
started, Day 1 entry complete"

---

## Day 2 — May 12, 2026 ✅ COMPLETE

**What I completed today:**
Downloaded and reviewed the complete cases_design.md file (1223 lines).
All 5 clinical cases are fully designed with all 8 required components
per case. Ran the 4-question verification test and anchor test for
each case. All 5 cases passed. Reviewed patient voice notes for each
case. Committed to GitHub.

**The 5 cases designed:**
- Case 1: Ramesh Kumar, 48M — Chest Pain — Correct: GERD,
  Anchor: Cardiac/MI, Min questions: 7
- Case 2: Priya Sharma, 28F — Headache — Correct: Hypertension,
  Anchor: Stress/Tension headache, Min questions: 7
- Case 3: Gopal Mehta, 74M — Confusion — Correct: UTI/Delirium,
  Anchor: Stroke/Dementia, Min questions: 8
- Case 4: Meera Patel, 35F — Fatigue+Weight gain —
  Correct: Hypothyroidism, Anchor: Depression/Burnout, Min questions: 8
- Case 5: Arjun Shah, 10M — Cough+Wheeze —
  Correct: Asthma, Anchor: Respiratory Infection, Min questions: 7

**Anchor test results — all cases passed:**
- Case 1: 3/5 natural first questions were cardiac-focused. PASS.
- Case 2: 4/5 natural first questions were stress/lifestyle. PASS.
- Case 3: 4/5 natural first questions were neurological. PASS.
- Case 4: 5/5 natural first questions were depression/lifestyle. PASS.
- Case 5: 3/5 natural first questions were infection-focused. PASS.

**Key design decision made:**
Case 3 (Gopal, elderly confusion) uses BOTH the patient AND the
daughter as speakers in the simulation. The daughter (Anita) is the
primary historian. This is clinically realistic — elderly confused
patients cannot give reliable history — and it makes the case
more interesting than a simple one-speaker consultation.

**Important technical note for Day 10 (bias_detector.py):**
Some topic keywords overlap between cases. For example "fever" appears
in both Case 3 and Case 5 as a required topic, but it means something
different in each. The TOPIC_KEYWORDS dictionary in session_tracker.py
must be case-agnostic (shared across all cases) while the required_topics
list per case defines which topics actually matter for that case's
premature closure detection. This separation is critical.

**What I am most uncertain about going into Day 3:**
How to write the pseudocode for confirmation bias detection without
being able to truly understand a user's intent from text alone.
The rule-based approach may produce false positives if a user asks
what appears to be a confirmation-seeking question but is actually
just exploring systematically.

**Did I find any problems with the cases that need fixing:**
Case 5 has only 7 required topics vs 8 for the other cases. This is
intentional — paediatric consultations have fewer history dimensions
than adult ones. However the minimum_questions is also 7, which means
a user who asks all 7 required topic questions will just barely avoid
the premature closure flag. This may be too lenient. Will monitor
during user testing and adjust if needed.

**End of day commit message:**
"Day 2: cases_design.md complete, all 5 cases verified, anchor tests
passed, patient voice notes written"

---

## Day 3 — May 13, 2026
## (Fill in at end of day)

**Template — answer these questions:**
1. What did I complete today?
2. Which bias type was hardest to write pseudocode for and why?
3. One decision about the detection logic (e.g. why score 0-1 not True/False)
4. Did I find any conflict between cases when writing shared topic keywords?
5. What am I most uncertain about going into Day 4?

---

## Day 4 — May 14, 2026
## (Fill in at end of day)

**Template — answer these questions:**
1. What folder structure did I create?
2. Did all packages install without errors?
3. One thing I learned from writing the file skeletons?
4. Did I encounter any issues with the Gemini library setup?
5. What is my biggest concern going into Day 5?

---

## Day 5 — May 15, 2026
## (Fill in at end of day)

---

## Day 6 — May 16, 2026
## (Fill in at end of day)

---

## Day 7 — May 17, 2026
## (Fill in at end of day — Phase 1 review)

