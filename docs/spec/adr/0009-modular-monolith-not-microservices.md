# ADR-0009 · Modular monolith, not microservices

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The system has a web app, an assessment engine, an LLM gateway, and an offline Case Factory. Two developers, no dedicated ops.

## Decision

Single deployable application with enforced internal layering: `domain/` must not import `infra/`, checked by import-linter in CI. The Case Factory runs as a separate process because it is a batch job, not because it is a separate service.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Microservices | Distributed transactions and network failure modes for a workload that fits on one small instance. |
| Unstructured monolith | The current state; assessment logic is not independently testable. |

## Consequences

+ Separation of concerns without network boundaries
+ Domain layer unit-testable with no database
+ One thing to deploy, monitor, and debug
− Requires discipline to maintain the import boundary (automated in CI)
