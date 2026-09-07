# ADR-0011 · Per-job LLM routing rather than one model

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The system makes model calls for five purposes — patient roleplay, feedback, case extraction, quality judging, grounding — with materially different requirements for latency, cost, and capability.

## Decision

Route each purpose to an appropriate model through a single gateway abstraction. Cheap and fast for the high-volume patient turn; stronger models for the once-per-session feedback and for offline Case Factory work. The Factory's judge must be a *different* model from its extractor.

## Alternatives considered

| Option | Why rejected |
|---|---|
| One model for everything | Either overpays on the high-volume path or under-delivers on structured extraction. |
| Same model extracts and judges | Correlated errors; a model does not catch its own blind spots. |

## Consequences

+ Cost optimised where volume is high, quality where it is visible
+ Provider switching is a configuration change
+ Decorrelated errors in the Factory QA gate
− More configuration surface
− Requires per-purpose cost accounting
