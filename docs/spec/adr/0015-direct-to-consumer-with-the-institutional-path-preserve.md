# ADR-0015 · Direct-to-consumer, with the institutional path preserved

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The original design assumed institutional B2B: institutions, cohorts, educators assigning cases. The product decision is to serve individual medical professionals directly.

## Decision

Build for individual accounts with subscriptions. Retain a nullable `institution_id` on `profiles` so a cohort product remains possible without a migration.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Institutional B2B first | Long sales cycles, procurement, and a product shaped by buyers who are not users. |
| Build both simultaneously | Doubles surface area before either is validated. |
| Drop institutional support entirely | A nullable column costs nothing now and saves weeks later. |

## Consequences

+ Faster path to real users and revenue
+ Self-serve growth rather than sales-led
+ B2B remains reachable without a schema rewrite
− Educator features, cohort assignment and aggregate dashboards are out of scope for v1
− Research studies become opt-in rather than cohort-wide (see TECH_SPEC §10)
