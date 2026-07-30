# References — Bias-Aware Virtual Patient Simulator
# Project: B.Tech Summer Internship 2026 — DA-IICT
# Last updated: Day 1 — May 11, 2026

---

## HOW TO USE THIS FILE
For every paper: read the "Gap it leaves" section carefully.
These gaps are what your project fills. Use them directly
in your Introduction and Literature Review sections.

---

## ====== YOUR 4 CORE PAPERS ======

---

## [1] Katarci & Topalli (2025) — A Focused Survey on Patient Simulation with LLMs

**Full title:** "A Focused Survey on Patient Simulation with Large Language Models"

**Published in:** 2025 Medical Technologies Congress (TIPTEKNO), IEEE
**DOI:** 10.1109/TIPTEKNO68206.2025.11270103

**What it does:**
Critically reviews and compares 10 peer-reviewed studies (2021–2025)
that use ChatGPT-based virtual or standardized patients in healthcare
education. Covers history-taking, empathy training, gamified platforms,
and structured simulation tools. Uses qualitative synthesis to evaluate
implementation strategies, learner engagement, and educational outcomes.

**Key findings:**
- LLM-powered virtual patients improve communication skills, diagnostic
  reasoning, and learner autonomy
- Cost and scalability advantages over traditional simulation (actors, manikins)
- High realism scores reported across multiple studies (e.g., 94% script match)
- Emotional depth and non-verbal communication remain unsolved limitations
- Most systems are still experimental or supplementary

**What NONE of the 10 reviewed systems do — the critical gap:**
Not a single one of the 10 systems reviewed detects cognitive bias during
the consultation. Every system evaluates whether the student got the
CORRECT final answer — none of them evaluate HOW the student reasoned
to get there. There is no detection of anchoring, premature closure, or
confirmation bias. There is no process-level feedback during the
consultation — only outcome-level feedback at the end.

**How it connects to your project:**
This is your most important reference. It confirms with a systematic
review that real-time cognitive bias detection in virtual patient
simulation is a completely unaddressed gap in the literature as of 2025.
Use this as your primary justification for why your project exists.

**Quote to use in your Introduction (paraphrase this):**
None of the reviewed systems provide feedback on the student's reasoning
process during simulation — only on the correctness of the final diagnosis.
This is the gap your system fills.

**IEEE Citation:**
[1] S. Katarci and A. K. Topalli, "A focused survey on patient simulation
with large language models," in Proc. 2025 Medical Technologies Congress
(TIPTEKNO), 2025, doi: 10.1109/TIPTEKNO68206.2025.11270103.

---

## [2] Han, Park & Lee (2025) — Chatbot Education Program for Nursing Students

**Full title:** "Development and Effects of a Chatbot Education Program
for Self-Directed Learning in Nursing Students"

**Published in:** BMC Medical Education, vol. 25, article 825, 2025
**DOI:** 10.1186/s12909-025-07316-2

**What it does:**
A randomized controlled trial (RCT) with 60 fourth-year nursing students
in South Korea. Experimental group (n=31) used a chatbot program for
mechanical ventilation nursing via LandBot; control group (n=29) received
only video lectures. Measured clinical reasoning competency, knowledge,
self-confidence, and education satisfaction pre- and post-intervention.

**Key results (quantitative — use these in your report):**
- Clinical reasoning competency: significantly higher in chatbot group
  (t = -5.00, p < .001) — pre: 43.68 → post: 56.10 vs control 46.55 → 47.21
- Self-confidence: significantly higher (t = -2.62, p = .011)
- Education satisfaction: significantly higher (t = -3.51, p < .001)
- Knowledge: NO significant difference (t = -0.09, p = .926)

**What it does NOT do — the gap:**
The chatbot in this study is a pre-scripted flow (built on LandBot, a
chatbot builder — not an LLM). It does not detect any form of cognitive
bias in the student's reasoning process. It improves clinical reasoning
competency as a general outcome but gives no information about WHICH
specific reasoning errors the student made or WHY. It does not simulate
a patient — it acts as a teaching assistant/tutor.

**How it connects to your project:**
This paper gives you your evaluation methodology. It shows you what
to measure: clinical reasoning competency, confidence, and satisfaction.
Their RCT design validates using pre/post measurement with a control
group. The fact that knowledge showed no significant difference despite
chatbot use is also relevant — it suggests process feedback (what your
system provides) may be more important than knowledge delivery alone.

**Important for your methodology:**
They used a 15-item clinical reasoning competency scale (Liou et al.,
Cronbach's α = 0.94) and simple NRS (0–10) for confidence and
satisfaction. You can reference their approach when designing your
own post-session survey.

**Limitation you can point out:**
No LLM, no real patient simulation, no bias detection — purely
knowledge delivery with scripted flows.

**IEEE Citation:**
[2] J. Han, J. Park, and H. Lee, "Development and effects of a chatbot
education program for self-directed learning in nursing students," BMC
Med. Educ., vol. 25, art. 825, 2025, doi: 10.1186/s12909-025-07316-2.

---

## [3] Hong, Xiao, Zhang & Chen (2024) — ArgMed-Agents

**Full title:** "ArgMed-Agents: Explainable Clinical Decision Reasoning
with LLM Discussion via Argumentation Schemes"

**Published in:** 2024 IEEE International Conference on Bioinformatics
and Biomedicine (BIBM), pp. 5486–5493
**DOI:** 10.1109/BIBM62325.2024.10822109

**What it does:**
Proposes a multi-agent LLM framework (ArgMed-Agents) for explainable
clinical decision reasoning. Uses three agent types: Generator (proposes
clinical arguments), Verifier (challenges arguments using critical
questions from Argumentation Scheme for Clinical Discussion / ASCD),
and Reasoner (uses a symbolic solver to identify coherent, non-
contradictory arguments as a final decision). Tested on MedQA and
PubMedQA in a zero-shot setting.

**Key results:**
- GPT-3.5-turbo: Direct 52.7% → CoT 48.0% → ArgMed-Agents 62.1%
  on MedQA (clinical decision subset)
- GPT-4: Direct 67.8% → CoT 71.4% → ArgMed-Agents 83.3% on MedQA
- Explainability (predictive accuracy by evaluator LLM):
  ArgMed-Agents GPT-4 = 0.91, approaching knowledge-based CDSS (0.95)
- In 63% of failure cases, identifiable clinical reasoning errors were
  present; 76% due to conflicting knowledge, 24% insufficient domain knowledge

**The Argumentation Scheme for Decision Making (ASDM) structure:**
This is relevant to your bias detection design. ASDM takes:
  Premise: Given patient fact F
  Premise: To achieve Goal G
  Premise: Decision D promotes Goal G
  Conclusion: Decision D should be considered
With Critical Questions (CQs): evidence for D, side effects of D,
alternatives to D, whether D can achieve G.
Your bias feedback engine can borrow this structure — instead of arguing
FOR a decision, your system argues AGAINST a biased reasoning pattern.

**What it does NOT do — the gap:**
ArgMed-Agents is designed for clinical DECISION SUPPORT — it helps the
AI make better decisions. It does NOT detect or give feedback on the
cognitive biases of a HUMAN user interacting with a patient simulation.
The system reasons on behalf of the clinician, not alongside them to
catch their errors. There is no virtual patient, no user interaction
design, no pedagogical feedback component.

**How it connects to your project:**
The argumentation framework directly inspires your Bias Feedback Engine.
Instead of using argumentation to reach a clinical decision, you use it
to construct Socratic challenges to a user's reasoning pattern. Their
Generator/Verifier/Reasoner pattern maps to your:
  Session Tracker (Generator — records what the user "argued" through
  their questions) → Bias Detector (Verifier — challenges the argument) →
  Feedback Generator (Reasoner — produces coherent feedback).

**IEEE Citation:**
[3] S. Hong, L. Xiao, X. Zhang, and J. Chen, "ArgMed-Agents: Explainable
clinical decision reasoning with LLM discussion via argumentation
schemes," in Proc. 2024 IEEE Int. Conf. Bioinformatics and Biomedicine
(BIBM), 2024, pp. 5486–5493, doi: 10.1109/BIBM62325.2024.10822109.

---

## [4] Greengrass (2026) — Transforming Clinical Reasoning: The Role of AI

**Full title:** "Transforming Clinical Reasoning—The Role of AI in
Supporting Human Cognitive Limitations"

**Published in:** Frontiers in Digital Health, vol. 7, art. 1715440, 2026
**DOI:** 10.3389/fdgth.2025.1715440

**What it does:**
A narrative review examining human cognitive limitations in diagnostic
reasoning and how AI can address them. Covers working memory constraints,
cognitive load theory (intrinsic, extraneous, germane), dual-process theory
(System 1 intuitive vs. System 2 analytical reasoning), heuristics, and
cognitive biases. Introduces Mutual Theory of Mind (MToM) as a framework
for future human-AI clinical decision support design.

**THIS PAPER IS YOUR THEORETICAL FOUNDATION. Extract these definitions
and use them verbatim (paraphrased) in your Introduction:**

**Definition — Anchoring Bias (from paper):**
Clinicians fixate on an early impression and fail to adjust their
judgment as new information becomes available. Occurs when System 1
dominates — an initial heuristic-based diagnosis is formed and System 2
is not engaged to re-evaluate. The anchor is typically the most salient
or first-presented symptom.

**Definition — Premature Closure (from paper):**
Halting the diagnostic process once a plausible explanation is found,
despite the diagnostic workup being insufficient. Consistently listed
as the most frequent cognitive cause of diagnostic error in empirical
studies. Closely related to pattern recognition — once a matching
illness script is found, the clinician stops searching.

**Definition — Confirmation Bias (from paper):**
Clinicians favour information that supports their initial diagnosis
while dismissing contradictory evidence. Can occur in both System 1
and System 2 reasoning — even deliberate analytical reasoning can be
biased when the schema applied is incomplete or incorrect.

**Key cognitive constraints to cite in your project:**
- Working memory capacity: approximately 4–5 discrete items at a time
- Temporal decay: information retained for only 10–20 seconds without rehearsal
- These constraints directly explain why students miss important history
  topics — cognitive overload causes premature closure

**AI's role as framed in this paper (use in your Discussion):**
AI can act as real-time metacognitive support — detecting behavioural
markers of premature closure (rapid narrowing of differential, failure
to integrate discordant findings) and triggering a diagnostic pause.
This is EXACTLY what your Bias Feedback Engine does.

**Mutual Theory of Mind (MToM) — relevant for your Future Work section:**
A bidirectional mental-modelling framework where AI models the clinician's
reasoning state and the clinician interprets AI outputs. Your system
is an early, simplified implementation of this concept — the session
tracker models the student's reasoning behaviour, and the feedback engine
responds to that model.

**What it does NOT do — the gap:**
This is a theoretical/narrative review — it proposes concepts but does
not build or evaluate any system. It identifies that AI detecting
"behavioural markers of premature closure" would be valuable, but
no implementation is described. Your project implements this idea.

**How it connects to your project:**
This paper justifies WHY cognitive bias detection matters (the theory),
while Katarci & Topalli [1] justifies WHY no current system does it
(the gap). Together these two papers build your entire Introduction.

**IEEE Citation:**
[4] C. J. Greengrass, "Transforming clinical reasoning—the role of AI
in supporting human cognitive limitations," Front. Digit. Health, vol. 7,
art. 1715440, 2026, doi: 10.3389/fdgth.2025.1715440.

---

## ====== PAPERS TO FIND ON GOOGLE SCHOLAR — DAY 1 TASK ======
## Run these 6 queries and add 6–8 more papers below in the same format.
## Target: 10–12 total papers in this file by end of Day 1.

## Search queries to run on scholar.google.com (filter: Since 2022):
## Query 1: "virtual patient simulator" "cognitive bias" clinical reasoning
## Query 2: "anchoring bias" "clinical decision" AI feedback
## Query 3: "premature closure" diagnosis detection natural language
## Query 4: "chatbot" "clinical reasoning" education Socratic feedback 2023
## Query 5: "LLM" "diagnostic reasoning" bias mitigation healthcare
## Query 6: argumentation clinical decision explainable AI LLM

## Add each new paper below using this exact template:
##
## ## [5] Author (Year) — Short Title
## **Full title:** ...
## **Published in:** ...
## **DOI:** ...
## **What it does:** ...
## **Key findings:** ...
## **Gap it leaves:** ...
## **How it connects to your project:** ...
## **IEEE Citation:** [5] ...

---

## ====== PAPERS TO ADD (slots 5–12) ======
## Fill these in during your Google Scholar session today (11:00–13:30)

## [5] — TO BE ADDED
## [6] — TO BE ADDED
## [7] — TO BE ADDED
## [8] — TO BE ADDED
## [9] — TO BE ADDED
## [10] — TO BE ADDED
## [11] — TO BE ADDED (if found)
## [12] — TO BE ADDED (if found)

---

## ====== YOUR PROJECT GAP — WRITE THIS AS YOUR RESEARCH GAP STATEMENT ======

## Based on papers [1]–[4], your research gap is:

## Existing LLM-powered virtual patient simulators evaluate whether
## the student reaches the correct final diagnosis, but none detect
## the cognitive reasoning process that led to that outcome. Specifically:
## - No system detects anchoring bias (over-focus on salient symptom)
## - No system detects premature closure (concluding too early)
## - No system detects confirmation bias (one-sided questioning)
## - No system provides process-level Socratic feedback during the session
##
## Greengrass (2026) [4] identifies that AI detecting "behavioural markers
## of premature closure" would be a valuable clinical education tool,
## but no implementation exists. This project builds that implementation.


---

## ====== GOOGLE SCHOLAR PAPERS — VERIFIED MAY 11 2026 ======

---

## [5] Bach, Nørgaard, Brok & van Berkel (2023) — Anchoring Bias Mitigation in Clinical AI

**Full title:** "If I Had All the Time in the World": Ophthalmologists'
Perceptions of Anchoring Bias Mitigation in Clinical AI Support

**Published in:** Proceedings of the 2023 CHI Conference on Human
Factors in Computing Systems (CHI '23), Hamburg, Germany, April 2023
**DOI:** 10.1145/3544548.3581513
**Venue quality:** CHI is the top-tier HCI conference — high credibility

**What it does:**
Used contextual inquiry and interviews to study ophthalmologists using
an existing clinical AI decision support system. Identified anchoring
bias concerns and misunderstanding of AI capabilities. Then evaluated
clinicians' perceptions of three bias mitigation strategies integrated
into the same system.

**Key findings:**
- Clinicians recognised the danger of anchoring bias but worried that
  mitigation strategies would slow down their workflow
- Participants were divided on whether mitigation would improve accuracy
  — this depended on how much they already relied on the AI
- Three mitigation strategies were evaluated: the paper provides
  design insights for what works and what frustrates clinicians

**Gap it leaves:**
This study focuses on how to mitigate anchoring bias when an AI is
GIVING recommendations to a clinician. It does not address the inverse
situation — detecting anchoring bias in a LEARNER who is asking
questions of a simulated patient. There is no educational or training
component, no virtual patient, and no Socratic feedback mechanism.

**How it connects to your project:**
The finding that bias mitigation must not slow users down is a direct
design constraint for your feedback system. Your Socratic feedback
appears AFTER the consultation ends (not during), which avoids the
workflow disruption problem this paper identifies. Also provides
vocabulary and framing for discussing bias mitigation design trade-offs
in your Discussion section.

**IEEE Citation:**
[5] A. K. P. Bach, T. M. Nørgaard, J. C. Brok, and N. van Berkel,
"'If I Had All the Time in the World': Ophthalmologists' Perceptions
of Anchoring Bias Mitigation in Clinical AI Support," in Proc. 2023
CHI Conf. Human Factors in Computing Systems (CHI '23), Hamburg,
Germany, Apr. 2023, pp. 1–14, doi: 10.1145/3544548.3581513.

---

## [6] Rosbach, Ammeling, Ganz et al. (2026) — Automation Bias and Anchoring in Pathology AI

**Full title:** Stuck on Suggestions: Automation Bias, the Anchoring
Effect, and the Factors That Shape Them in Computational Pathology

**Published in:** Machine Learning for Biomedical Imaging (MELBA),
vol. 2026, MELBA-BVM 2025 Special Issue, pp. 126–147
**DOI:** 10.59275/j.melba.2026-87b1

**What it does:**
Online experiment with 28 pathology experts estimating tumor cell
percentages. Each expert worked independently first, then with AI
support. Measured automation bias (blindly following AI) and anchoring
bias (being disproportionately influenced by AI's first suggestion)
as separate phenomena. Also examined the effect of time pressure
on these biases.

**Key findings:**
- Both automation bias and anchoring bias were detected and measurable
  in real clinical experts using AI tools
- Time pressure amplified both bias types — experts under time
  constraints relied more on AI suggestions uncritically
- Individual user characteristics (e.g. prior experience, confidence)
  shaped bias susceptibility — not everyone anchors equally

**Gap it leaves:**
This study measures bias in experts receiving AI suggestions in
radiology/pathology — not in learners conducting clinical history-taking.
It does not attempt to detect or correct bias in real time, and has
no educational feedback component whatsoever.

**How it connects to your project:**
Provides strong empirical evidence that anchoring bias in clinical
AI settings is real, measurable, and significant even in trained
professionals. Strengthens your Introduction's argument that bias
detection is a necessary component of any clinical training system.
The finding about time pressure is also relevant — your system removes
time pressure by letting users proceed at their own pace.

**IEEE Citation:**
[6] E. Rosbach, J. Ammeling, J. Ganz, C. A. Bertram, T. Conrad,
A. Riener, and M. Aubreville, "Stuck on Suggestions: Automation Bias,
the Anchoring Effect, and the Factors That Shape Them in Computational
Pathology," Mach. Learn. Biomed. Imaging, vol. 2026, pp. 126–147,
2026, doi: 10.59275/j.melba.2026-87b1.

---

## [7] Qazi, Ali, Khawaja et al. (2026) — Automation Bias in LLM-Assisted Diagnostic Reasoning

**Full title:** Automation Bias in Large Language Model–Assisted
Diagnostic Reasoning among Physicians Trained in AI Literacy —
A Randomized Clinical Trial

**Published in:** NEJM AI, vol. 3, no. 5, 2026
**DOI:** 10.1056/AIoa2501001
**Venue quality:** NEJM AI is one of the most prestigious medical AI
journals — this is a very strong citation

**What it does:**
Single-blind RCT with 44 physicians who had completed 20-hour
AI-literacy training. Physicians diagnosed 6 clinical vignettes in
75 minutes. Treatment group received ChatGPT-4o suggestions that
contained deliberate errors in 3 of 6 cases. Control group received
error-free AI advice. All physicians could consult, modify, or
ignore the LLM suggestions freely.

**Key findings:**
- Erroneous LLM recommendations significantly degraded diagnostic
  performance even in AI-trained physicians — automation bias was present
- Physicians voluntarily deferred to flawed AI output even when they
  had been specifically trained to critically evaluate AI
- The study concludes robust safeguards ensuring human oversight are
  necessary before widespread LLM deployment in clinical settings

**Gap it leaves:**
This study shows what happens when a physician receives a wrong AI
recommendation — it does not study the inverse, which is detecting
and correcting the human's own reasoning biases independently of
whether the AI is wrong or right. There is no educational simulation,
no patient interaction, and no training feedback component.

**How it connects to your project:**
This paper directly justifies why your feedback system matters. If
even AI-trained physicians are susceptible to automation bias when
using LLMs, then clinical training systems must actively develop
learners' critical reasoning skills — exactly what your Socratic
feedback engine does. Use this in your Introduction to argue that
bias detection in training is necessary, not optional.

**IEEE Citation:**
[7] I. A. Qazi, A. Ali, A. U. Khawaja, M. J. Akhtar, A. Z. Sheikh,
and M. H. Alizai, "Automation bias in large language model–assisted
diagnostic reasoning among physicians trained in AI literacy: A
randomized clinical trial," NEJM AI, vol. 3, no. 5, 2026,
doi: 10.1056/AIoa2501001.

---

## [8] Newman-Toker (2013) — Premature Closure and Anchoring: A Real Case

**Full title:** From Possible to Probable to Sure to Wrong—Premature
Closure and Anchoring in a Complicated Case

**Published in:** AHRQ PSNet (Agency for Healthcare Research and
Quality, Patient Safety Network), April 2013
**URL:** https://psnet.ahrq.gov/web-mm/possible-probable-sure-wrong-premature-closure-and-anchoring-complicated-case
**Note:** This is a clinical commentary, not a research paper.
Use only in Introduction to illustrate real-world consequences.

**What it does:**
Clinical case commentary describing a real patient (44-year-old male)
admitted with headache and word-finding difficulties. Initial diagnosis
of CNS vasculitis was reached through anchoring on the MRI findings.
Despite worsening lesions on serial imaging, the team anchored on their
initial diagnosis. Four months later re-biopsy revealed glioblastoma —
a missed cancer diagnosis caused by anchoring and premature closure.

**Key findings:**
- Anchoring on the initial diagnosis of CNS vasculitis prevented the
  team from re-evaluating even as contradictory evidence mounted
- Premature closure occurred because a plausible explanation was found
  and the diagnostic process was stopped prematurely
- The author explicitly defines and differentiates premature closure
  from anchoring in clinical terms

**Gap it leaves:**
This is a retrospective commentary on a single case — not a study
of how to detect or mitigate these biases in training. It identifies
the problem but proposes no technological solution.

**How it connects to your project:**
Use this in your Introduction ONLY — as a compelling real-world
example of why premature closure and anchoring cause patient harm.
One concrete case of a missed cancer diagnosis is more persuasive to
a reader than abstract statistics. Cite it alongside Greengrass [4]
to establish the clinical stakes.

**IEEE Citation:**
[8] D. E. Newman-Toker, "From possible to probable to sure to
wrong—premature closure and anchoring in a complicated case,"
AHRQ PSNet, Apr. 2013. [Online]. Available:
https://psnet.ahrq.gov/web-mm/possible-probable-sure-wrong-premature-closure-and-anchoring-complicated-case

---

## [9] Pereira (2025) — Smart-Doc: AI-Powered Medical Education through Diagnostic Interactions

**Full title:** Smart-Doc: AI-Powered Medical Education through
Diagnostic Interactions

**Published in:** Master's Dissertation, Faculty of Engineering
(FEUP), University of Porto, Portugal, November 2025
**Repository:** https://repositorio-aberto.up.pt/handle/10216/170910
**Note:** This is a Master's thesis, not a journal article.
Cite as a thesis. It is peer-reviewed by the university committee
and is publicly available in the FEUP open repository.

**What it does:**
A CS/Engineering Master's thesis building an AI-powered medical
education platform called Smart-Doc that uses diagnostic interactions
— meaning learners interact with AI to practice clinical diagnosis.
The exact implementation details require reading the full thesis PDF
but the title and venue directly indicate it is a virtual patient
simulation system for medical education using AI.

**Gap it leaves (based on title and venue — thesis not fully read):**
As a Master's thesis from a Portuguese engineering faculty, it is
unlikely to include real-time cognitive bias detection or Socratic
feedback targeting specific reasoning errors. Most such projects focus
on the patient simulation quality rather than the learner's reasoning
process. However — VERIFY THIS when you read the thesis PDF before
your report writing phase (Week 7). If Smart-Doc does detect bias,
you must acknowledge it and clearly differentiate your approach.

**How it connects to your project:**
This is your closest competitor in the literature. A CS student
building an AI diagnostic interaction system for medical education
in 2025 is almost exactly your project description. You must read
this thesis before writing your final report. Use it in your
literature review to show your project is positioned in a growing
field, and explain precisely how your bias detection + Socratic
feedback layer differentiates you from Smart-Doc.

**ACTION REQUIRED before Week 7:**
Download the full PDF from:
https://repositorio-aberto.up.pt/bitstream/10216/170910/2/749584.pdf
Read it completely and update this entry with what it actually does
and does not do. This is the single most important paper to read
after your 4 core papers.

**Citation (Master's Thesis format):**
[9] B. de Sena Pereira, "Smart-Doc: AI-Powered Medical Education
through Diagnostic Interactions," M.S. dissertation, Fac. Eng.,
Univ. Porto, Porto, Portugal, 2025. [Online]. Available:
https://repositorio-aberto.up.pt/handle/10216/170910

---

## ====== REJECTED PAPERS — DO NOT CITE ======

## Sanchez — "Integrating AI and Socratic Inquiry in Medical Education"
REJECTED: No verifiable DOI, not indexed in Scopus/PubMed/IEEE,
from a non-ranked institution with no citation data. Cannot verify
content or peer review status. Using it would undermine your
literature review's credibility.

## Loomis et al. (2024) — Cranial Nerve Anatomy Module
ASSESSED AS LOW RELEVANCE: No AI, no chatbot, no bias detection.
Only connects to your project through the general argument that
clinical reasoning is undertaught. If you need a 10th paper, you
may include it, but it adds very little to your narrative.

---

## ====== FINAL PAPER COUNT ======
## Papers [1]–[4]: Your 4 core papers (fully annotated above)
## Papers [5]–[9]: 5 verified Google Scholar papers
## Total: 9 papers — sufficient for a strong literature review
## Target was 10+ — you are at 9. This is acceptable.
## If you want 10, include the Loomis paper as [10].

