# ADR-0012 · Natural Language Inference for grounding, not an LLM

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The Case Factory must verify that every generated clinical fact is supported by its source record. This is textual entailment — a well-defined classification task with purpose-built models.

## Decision

Use a DeBERTa-class NLI model for the grounding check, escalating to an LLM only for cases the NLI model marks uncertain.

## Alternatives considered

| Option | Why rejected |
|---|---|
| LLM for every grounding check | Slower, more expensive, and non-deterministic for a task that is fundamentally classification. |
| String matching only | Misses paraphrase; too brittle. |

## Consequences

+ Deterministic and auditable
+ Runs on CPU at no per-call cost
+ More appropriate to the task than open-ended generation
− One more model artefact to version
− Requires a confidence threshold for escalation
