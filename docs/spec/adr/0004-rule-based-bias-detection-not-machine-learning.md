# ADR-0004 · Rule-based bias detection, not machine learning

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The three detectors must produce feedback a learner can act on. We have 16 real sessions — nowhere near enough to train a classifier. The detectors were validated at 94 % accuracy with 100 % sensitivity.

## Decision

Detection stays rule-based and deterministic. Every flag returns a human-readable reason and the evidence that triggered it.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Train a classifier on session features | No labelled corpus; 16 sessions is noise; destroys traceability. |
| LLM-as-judge for bias detection | Non-deterministic, unauditable, and would put the LLM in the marking path (ADR-0005). |

## Consequences

+ Every flag is explainable and contestable — the property that makes feedback teachable
+ Deterministic, so results are reproducible and verifiable
+ Fast (microseconds) and free
− Bounded by lexical coverage; paraphrased questions are missed
− Thresholds are heuristic, not calibrated (see ADR-0013)
− Revisit only with 10³+ labelled sessions, and then as a comparator, not a replacement
