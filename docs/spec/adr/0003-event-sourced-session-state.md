# ADR-0003 · Event-sourced session state

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

Session state currently lives in a process-local dictionary, so a restart loses in-flight consultations and the app cannot run more than one worker. Separately, the pilot's data-integrity check worked by recomputing bias flags from stored questions — which is event sourcing in all but name.

## Decision

Persist every consultation action as an append-only row in `session_events`. Derive session state and all assessment results by replaying that log.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Redis for session state | Adds a second stateful service to solve a problem Postgres already solves at this scale. |
| Signed client-side cookie | 4 KB limit; transcripts exceed it; and it would let a user tamper with assessment input. |
| Sticky sessions | Preserves the data-loss bug rather than fixing it. |
| Mutable session row | Loses the ability to replay and recompute. |

## Consequences

+ Consultations survive restarts and support multiple workers
+ Threshold changes can be evaluated by replaying history (enables calibration)
+ Per-event timestamps give think-time data we currently discard
+ Any published result traces to an immutable sequence
− One extra table and a reconstruction function
− Reconstruction cost per request (negligible at ~20 events)
