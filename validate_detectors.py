"""
validate_detectors.py
----------------------
Detector validation harness (research Piece 3).

Purpose
=======
Establishes that the three rule-based cognitive-bias detectors in
`bias_detector.py` actually detect the reasoning patterns they claim to,
BEFORE the detectors are used to draw conclusions about real students.

Method
======
We author a set of labelled synthetic consultation transcripts. Each transcript
is a realistic sequence of free-text student questions plus the examinations,
investigations and final diagnosis. Every transcript carries a GROUND-TRUTH
label for each bias, assigned from the clinical reasoning behaviour it portrays
(NOT from the detector's internal rules), following this rubric:

  * anchoring    = the student fixates on the case's trap diagnosis and does not
                   meaningfully explore alternative explanations.
  * premature    = the student concludes without an adequate history (too few
                   questions and/or key history areas left unexplored).
  * confirmation = the student pursues the trap and fails to seek the
                   contradictory evidence that argues against it.

Each transcript is run through the SAME code path used in production
(`create_session` -> `update_session`/`extract_topics` -> `detect_all_biases`),
and the detector's boolean output is compared to the ground-truth label.
We report a confusion matrix, sensitivity, specificity and accuracy per detector.

Because the transcripts are author-labelled, this is a pilot self-validation;
independent labelling by a medical rater is noted as future work.

Run:  python validate_detectors.py
Output: prints a report and writes docs/detector_validation.md
"""

from cases import get_case
from session_tracker import create_session, update_session
from bias_detector import detect_all_biases


# ── Labelled transcripts ──────────────────────────────────────────────
# gold: (anchoring, premature, confirmation)  as booleans
SCENARIOS = [

    # ===================== CASE 1 — GERD (trap: cardiac) =====================
    {
        "id": "C1-tunnel-rushed",
        "case": "case_1",
        "desc": "Cardiac tunnel vision, concludes fast",
        "questions": [
            "I'm worried about your heart — have you ever had angina?",
            "Should we get an ECG? Any history of coronary artery disease?",
            "Do you get palpitations or a racing feeling?",
            "Any family history of heart attack or cardiac problems?",
        ],
        "diagnosis": "Acute coronary syndrome / heart attack",
        "gold": (True, True, True),
    },
    {
        "id": "C1-thorough-correct",
        "case": "case_1",
        "desc": "Broad history, explores reflux, correct diagnosis",
        "questions": [
            "Can you describe the pain — is it burning or crushing?",
            "Is it worse after meals or spicy food?",
            "Does it radiate to your arm, jaw or neck?",
            "Any nausea, sweating or breathlessness with it?",
            "What medications do you take — any ibuprofen or painkillers?",
            "Does lying down make it worse, and do antacids help?",
            "Any family history of heart disease or other conditions?",
            "How long has this been going on and is it constant?",
        ],
        "diagnosis": "GERD / acid reflux, likely NSAID-related",
        "gold": (False, False, False),
    },
    {
        "id": "C1-rushed-openminded",
        "case": "case_1",
        "desc": "Stops early but balanced direction (premature only)",
        "questions": [
            "Is the pain burning or more of a pressure?",
            "Is it worse after meals?",
            "Any radiation to the arm?",
            "Do antacids help at all?",
        ],
        "diagnosis": "Not sure yet — possibly reflux, will investigate",
        "gold": (False, True, False),
    },
    {
        "id": "C1-broad-but-anchored",
        "case": "case_1",
        "desc": "Asks a lot but all cardiac, concludes cardiac (anchor+confirm, not premature)",
        "questions": [
            "Does it feel like crushing chest pressure — cardiac in nature?",
            "Does the pain radiate to your left arm or jaw?",
            "Any sweating, nausea or breathlessness — cardiac associated symptoms?",
            "Have you had an ECG or troponin done?",
            "Any history of angina, MI or coronary disease?",
            "Do you get palpitations or an irregular heartbeat?",
            "Any family history of heart attacks?",
            "How long has the chest tightness been going on?",
        ],
        "diagnosis": "Cardiac chest pain / myocardial ischaemia",
        "gold": (True, False, True),
    },
    {
        "id": "C1-paraphrased-thorough",
        "case": "case_1",
        "desc": "Genuinely thorough but paraphrased (keyword-avoiding) — stress test",
        "questions": [
            "Tell me the exact quality of the chest sensation you get.",
            "Does a rich evening dinner or something tangy set it off?",
            "When it comes on, does the feeling travel anywhere else in your body?",
            "Do you get any other complaints alongside it, like feeling clammy?",
            "Are you on any regular tablets, including anything for aches?",
            "If you recline flat, does the feeling intensify, and does a chalky remedy soothe it?",
            "Does anyone in your household have cardiac trouble?",
            "Over what span of time has this been present, and is it steady?",
        ],
        "diagnosis": "Reflux disease",
        "gold": (False, False, False),
    },

    # ===================== CASE 2 — PE (trap: chest infection) =====================
    {
        "id": "C2-tunnel-rushed",
        "case": "case_2",
        "desc": "Infection tunnel vision, concludes fast",
        "questions": [
            "Do you have a chest infection — a cough with green phlegm?",
            "Any fever or feeling like you have the flu?",
            "Should we start antibiotics for a possible pneumonia?",
            "Is this just a viral cold or bronchitis?",
        ],
        "diagnosis": "Chest infection / pneumonia",
        "gold": (True, True, True),
    },
    {
        "id": "C2-thorough-correct",
        "case": "case_2",
        "desc": "Explores PE risk factors, correct diagnosis",
        "questions": [
            "Is the pain pleuritic — sharp and worse when you breathe deeply?",
            "Have you coughed up any blood — any haemoptysis?",
            "Have you been on any long flights or long journeys recently?",
            "Any swelling or pain in your calf or legs?",
            "Are you on the contraceptive pill or any medications?",
            "Any personal or family history of blood clots or DVT?",
            "How many days has the breathlessness been getting worse?",
            "Does anything make the breathing better or worse?",
        ],
        "diagnosis": "Pulmonary embolism",
        "gold": (False, False, False),
    },
    {
        "id": "C2-rushed-openminded",
        "case": "case_2",
        "desc": "Stops early but balanced (premature only)",
        "questions": [
            "Is the pain sharp and pleuritic?",
            "Any recent long flights?",
            "Any calf swelling?",
            "Are you on the pill?",
            "Have you had any haemoptysis?",
        ],
        "diagnosis": "Possibly PE — need to investigate",
        "gold": (False, True, False),
    },
    {
        "id": "C2-anchored-many-questions",
        "case": "case_2",
        "desc": "Many questions but all infection-framed, concludes infection",
        "questions": [
            "Do you have a productive cough with green phlegm?",
            "Any fever, chills or flu-like symptoms?",
            "Could this be a chest infection or pneumonia?",
            "Have you tried antibiotics or a nebuliser?",
            "Is it a viral cold that you caught?",
            "Any sore throat or upper respiratory symptoms?",
            "How long have you had these infection symptoms?",
            "Is the cough keeping you up at night?",
        ],
        "diagnosis": "Community-acquired pneumonia",
        "gold": (True, True, True),
    },

    # ===================== CASE 3 — UTI/Delirium (trap: stroke) =====================
    {
        "id": "C3-tunnel-rushed",
        "case": "case_3",
        "desc": "Stroke/dementia tunnel vision, concludes fast",
        "questions": [
            "Could this be a stroke — should we get a CT scan of the brain?",
            "Any signs of dementia or memory loss?",
            "Do you think he had a TIA or mini-stroke?",
            "Should a neurologist review him for a brain bleed?",
        ],
        "diagnosis": "Stroke",
        "gold": (True, True, True),
    },
    {
        "id": "C3-thorough-correct",
        "case": "case_3",
        "desc": "Explores delirium causes, correct diagnosis",
        "questions": [
            "When exactly did the confusion start — sudden or gradual?",
            "Was he completely normal before — what is his usual baseline?",
            "Does he have any fever or a raised temperature?",
            "Any urinary symptoms — going to the toilet more, or burning?",
            "What medications does he take?",
            "Any recent illness, falls or infections?",
            "Any weakness, facial droop or slurred speech?",
            "Has he been eating and drinking normally?",
        ],
        "diagnosis": "UTI causing acute delirium",
        "gold": (False, False, False),
    },
    {
        "id": "C3-rushed-openminded",
        "case": "case_3",
        "desc": "Stops early but balanced (premature only)",
        "questions": [
            "When did the confusion start?",
            "Does he have a fever?",
            "Any urinary problems or discomfort passing water?",
            "Any weakness or facial droop?",
        ],
        "diagnosis": "Not sure yet — will run some tests",
        "gold": (False, True, False),
    },

    # ===================== CASE 4 — Hypothyroidism (trap: depression) =====================
    {
        "id": "C4-tunnel-rushed",
        "case": "case_4",
        "desc": "Depression tunnel vision, concludes fast",
        "questions": [
            "This sounds like depression — have you been feeling low or hopeless?",
            "Is this burnout or work stress?",
            "Have you considered therapy, counselling or an antidepressant?",
            "Could more exercise and better sleep help your mood?",
        ],
        "diagnosis": "Depression",
        "gold": (True, True, True),
    },
    {
        "id": "C4-thorough-correct",
        "case": "case_4",
        "desc": "Explores thyroid features, correct diagnosis",
        "questions": [
            "Is your mood okay, or do you feel down and lose interest in things?",
            "Has your weight changed even though your eating is the same?",
            "Do you feel the cold more than others around you?",
            "Any constipation or change in your bowel habits?",
            "Have you noticed hair loss or dry skin?",
            "Any family history of thyroid problems?",
            "Have your periods changed — heavier or irregular?",
            "Is the tiredness worse at a particular time of day?",
        ],
        "diagnosis": "Primary hypothyroidism",
        "gold": (False, False, False),
    },
    {
        "id": "C4-paraphrased-thorough",
        "case": "case_4",
        "desc": "Genuinely thorough but paraphrased — stress test",
        "questions": [
            "In yourself, do you still take pleasure in your usual activities?",
            "Has the number on the scale crept up despite unchanged portions?",
            "Do you reach for extra jumpers when the room feels fine to everyone else?",
            "Have your trips to the loo become less frequent or harder lately?",
            "Is more of your hair collecting on the pillow or in the plughole?",
            "Does anyone related to you have an underactive gland issue?",
            "Have your monthly cycles grown heavier of late?",
            "At which point in the day does the exhaustion bite hardest?",
        ],
        "diagnosis": "Underactive thyroid",
        "gold": (False, False, False),
    },

    # ===================== CASE 5 — DKA (trap: gastroenteritis) =====================
    {
        "id": "C5-tunnel-rushed",
        "case": "case_5",
        "desc": "Gastroenteritis tunnel vision, concludes fast",
        "questions": [
            "This is probably just gastroenteritis or a stomach bug, right?",
            "Did you catch food poisoning or norovirus from your flatmate?",
            "Should we give antiemetics like ondansetron and oral rehydration?",
            "Is this a self-limiting viral illness we just rest and hydrate?",
        ],
        "diagnosis": "Gastroenteritis",
        "gold": (True, True, True),
    },
    {
        "id": "C5-thorough-correct",
        "case": "case_5",
        "desc": "Explores diabetes features, correct diagnosis",
        "questions": [
            "How long has this been going on and how did it start?",
            "Can you describe the abdominal pain — constant or cramping?",
            "Before this, were you unusually thirsty or drinking a lot?",
            "Have you been urinating more often, even at night?",
            "Have you lost any weight recently?",
            "Any fever, and does your breathing feel different or fast?",
            "Do you take any medications or have any medical conditions?",
            "Any family history of diabetes?",
        ],
        "diagnosis": "Diabetic ketoacidosis / new type 1 diabetes",
        "gold": (False, False, False),
    },
    {
        "id": "C5-rushed-openminded",
        "case": "case_5",
        "desc": "Stops early but balanced (premature only)",
        "questions": [
            "How long have you been vomiting?",
            "Can you describe the tummy pain?",
            "Have you been very thirsty lately?",
            "Any weight loss?",
        ],
        "diagnosis": "Not sure — could be early diabetes, will test",
        "gold": (False, True, False),
    },
]


# ── Harness ───────────────────────────────────────────────────────────

def run_scenario(scenario):
    """Runs one transcript through the production pipeline; returns predictions."""
    session = create_session(scenario["case"])
    for q in scenario["questions"]:
        update_session(session, q)
    session["exams_performed"] = scenario.get("exams", [])
    session["investigations_ordered"] = scenario.get("investigations", [])
    session["diagnosis_submitted"] = scenario["diagnosis"]

    case = get_case(scenario["case"])
    results = detect_all_biases(session, case)
    return (
        results["anchoring"]["detected"],
        results["premature_closure"]["detected"],
        results["confirmation_bias"]["detected"],
    )


def confusion(golds, preds):
    """Returns TP, FP, FN, TN for one detector across all scenarios."""
    tp = fp = fn = tn = 0
    for g, p in zip(golds, preds):
        if g and p:      tp += 1
        elif g and not p: fn += 1
        elif not g and p: fp += 1
        else:             tn += 1
    return tp, fp, fn, tn


def metrics(tp, fp, fn, tn):
    sens = tp / (tp + fn) if (tp + fn) else None      # recall on positives
    spec = tn / (tn + fp) if (tn + fp) else None      # recall on negatives
    acc  = (tp + tn) / (tp + fp + fn + tn)
    return sens, spec, acc


def fmt(x):
    return "n/a" if x is None else f"{x*100:.0f}%"


def main():
    names = ["Anchoring", "Premature closure", "Confirmation bias"]

    # Collect predictions
    rows = []
    gold_cols = [[], [], []]
    pred_cols = [[], [], []]
    for s in SCENARIOS:
        pred = run_scenario(s)
        rows.append((s, pred))
        for i in range(3):
            gold_cols[i].append(s["gold"][i])
            pred_cols[i].append(pred[i])

    # Per-scenario detail
    lines = []
    lines.append("# Detector Validation Results\n")
    lines.append(
        "Author-labelled synthetic transcripts run through the production "
        "pipeline (`create_session` -> `extract_topics` -> `detect_all_biases`). "
        "`A/P/C` = Anchoring / Premature closure / Confirmation bias. "
        "`1` = flagged, `0` = not. A mismatch between gold and predicted is a "
        "detector error.\n")
    lines.append(f"**Transcripts:** {len(SCENARIOS)}\n")
    lines.append("## Per-transcript results\n")
    lines.append("| ID | Description | Gold A/P/C | Pred A/P/C | Match |")
    lines.append("|----|-------------|-----------|-----------|-------|")
    for s, pred in rows:
        g = "".join("1" if x else "0" for x in s["gold"])
        p = "".join("1" if x else "0" for x in pred)
        match = "✓" if g == p else "✗"
        lines.append(f"| {s['id']} | {s['desc']} | {g[0]}/{g[1]}/{g[2]} "
                     f"| {p[0]}/{p[1]}/{p[2]} | {match} |")

    # Per-detector metrics
    lines.append("\n## Per-detector performance\n")
    lines.append("| Detector | TP | FP | FN | TN | Sensitivity | Specificity | Accuracy |")
    lines.append("|----------|----|----|----|----|-------------|-------------|----------|")
    overall_correct = 0
    overall_total = 0
    for i, nm in enumerate(names):
        tp, fp, fn, tn = confusion(gold_cols[i], pred_cols[i])
        sens, spec, acc = metrics(tp, fp, fn, tn)
        overall_correct += tp + tn
        overall_total += tp + fp + fn + tn
        lines.append(f"| {nm} | {tp} | {fp} | {fn} | {tn} "
                     f"| {fmt(sens)} | {fmt(spec)} | {fmt(acc)} |")

    overall_acc = overall_correct / overall_total if overall_total else 0
    lines.append(f"\n**Overall decision accuracy:** {overall_correct}/{overall_total} "
                 f"= {overall_acc*100:.0f}% across all detector decisions.\n")

    report = "\n".join(lines)
    print(report)

    # Save markdown
    import os
    os.makedirs("docs", exist_ok=True)
    with open("docs/detector_validation.md", "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print("\nSaved: docs/detector_validation.md")


if __name__ == "__main__":
    main()
