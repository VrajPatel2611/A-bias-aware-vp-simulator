# Detector Validation Results

Author-labelled synthetic transcripts run through the production pipeline (`create_session` -> `extract_topics` -> `detect_all_biases`). `A/P/C` = Anchoring / Premature closure / Confirmation bias. `1` = flagged, `0` = not. A mismatch between gold and predicted is a detector error.

**Transcripts:** 18

## Per-transcript results

| ID | Description | Gold A/P/C | Pred A/P/C | Match |
|----|-------------|-----------|-----------|-------|
| C1-tunnel-rushed | Cardiac tunnel vision, concludes fast | 1/1/1 | 1/1/1 | ✓ |
| C1-thorough-correct | Broad history, explores reflux, correct diagnosis | 0/0/0 | 0/0/0 | ✓ |
| C1-rushed-openminded | Stops early but balanced direction (premature only) | 0/1/0 | 0/1/0 | ✓ |
| C1-broad-but-anchored | Asks a lot but all cardiac, concludes cardiac (anchor+confirm, not premature) | 1/0/1 | 1/0/1 | ✓ |
| C1-paraphrased-thorough | Genuinely thorough but paraphrased (keyword-avoiding) — stress test | 0/0/0 | 0/1/1 | ✗ |
| C2-tunnel-rushed | Infection tunnel vision, concludes fast | 1/1/1 | 1/1/1 | ✓ |
| C2-thorough-correct | Explores PE risk factors, correct diagnosis | 0/0/0 | 0/0/0 | ✓ |
| C2-rushed-openminded | Stops early but balanced (premature only) | 0/1/0 | 0/1/0 | ✓ |
| C2-anchored-many-questions | Many questions but all infection-framed, concludes infection | 1/1/1 | 1/1/1 | ✓ |
| C3-tunnel-rushed | Stroke/dementia tunnel vision, concludes fast | 1/1/1 | 1/1/1 | ✓ |
| C3-thorough-correct | Explores delirium causes, correct diagnosis | 0/0/0 | 0/0/0 | ✓ |
| C3-rushed-openminded | Stops early but balanced (premature only) | 0/1/0 | 0/1/0 | ✓ |
| C4-tunnel-rushed | Depression tunnel vision, concludes fast | 1/1/1 | 1/1/1 | ✓ |
| C4-thorough-correct | Explores thyroid features, correct diagnosis | 0/0/0 | 0/0/0 | ✓ |
| C4-paraphrased-thorough | Genuinely thorough but paraphrased — stress test | 0/0/0 | 0/0/1 | ✗ |
| C5-tunnel-rushed | Gastroenteritis tunnel vision, concludes fast | 1/1/1 | 1/1/1 | ✓ |
| C5-thorough-correct | Explores diabetes features, correct diagnosis | 0/0/0 | 0/0/0 | ✓ |
| C5-rushed-openminded | Stops early but balanced (premature only) | 0/1/0 | 0/1/0 | ✓ |

## Per-detector performance

| Detector | TP | FP | FN | TN | Sensitivity | Specificity | Accuracy |
|----------|----|----|----|----|-------------|-------------|----------|
| Anchoring | 7 | 0 | 0 | 11 | 100% | 100% | 100% |
| Premature closure | 10 | 1 | 0 | 7 | 100% | 88% | 94% |
| Confirmation bias | 7 | 2 | 0 | 9 | 100% | 82% | 89% |

**Overall decision accuracy:** 51/54 = 94% across all detector decisions.

