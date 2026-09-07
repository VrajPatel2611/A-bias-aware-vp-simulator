# ADR-0010 · Cases are immutable and versioned

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

A session's results are only interpretable in the context of the exact case content the learner saw. Editing a published case would silently invalidate historical data.

## Decision

`cases` holds identity; `case_versions` holds immutable content. Sessions reference `case_version_id`, never `case_id`. Editing a published case creates a new draft version.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Mutable case rows | Historical results become uninterpretable after any edit. |
| Full-database snapshots | Heavy and does not localise the problem. |

## Consequences

+ Historical results remain valid indefinitely
+ Clinical review attaches to a specific, frozen version
+ Enables safe A/B testing of case variants
− More rows and a slightly more complex publish flow
