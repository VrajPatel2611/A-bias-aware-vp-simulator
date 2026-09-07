# ADR-0014 · No case retirement policy; use variants instead

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

Repeated exposure degrades a trap case's validity once answers circulate. A retirement policy would cap the useful life of expensive hand-authored content.

## Decision

No automatic retirement. Instead: system-selected cases rather than user choice, a deep bank, generated case variants (same trap, different patient details and values), anomaly detection for suspiciously fast-and-perfect sessions, and per-case difficulty monitoring so a collapsing trap rate can be acted on individually.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Retire after N uses | Discards expensive content on a schedule rather than on evidence. |
| Do nothing | Answer sharing would silently degrade the measurement. |

## Consequences

+ Authoring effort retains value indefinitely
+ Variants multiply the return on each authored case
+ Retirement remains available as a per-case judgement
− Requires variant generation and anomaly detection to be built
