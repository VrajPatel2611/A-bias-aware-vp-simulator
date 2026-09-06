# ADR-0005 · The LLM is excluded from the marking path

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The system uses an LLM for the patient persona and for feedback prose. Assessment results must be reproducible for research credibility and for the data-integrity check.

## Decision

The LLM generates text only. Every flag, score, coverage figure and verdict is computed by deterministic Python. No assessment decision is delegated to a model.

## Alternatives considered

| Option | Why rejected |
|---|---|
| LLM scores the consultation | Non-reproducible at temperature > 0; unauditable; would have made the pilot integrity check impossible. |
| Hybrid — LLM adjusts rule output | Inherits the worst of both: non-determinism without interpretability. |

## Consequences

+ Recomputation from stored questions verifies data authenticity (used in the pilot)
+ Threshold replay is possible
+ Assessment latency is sub-millisecond and free
+ Removes an entire class of prompt-injection attack on grading
− Assessment quality is bounded by rule quality
