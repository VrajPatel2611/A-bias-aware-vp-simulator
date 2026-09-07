# ADR-0007 · Retain Flask; do not migrate to FastAPI

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The existing backend is Flask and works. The team knows it. FastAPI offers native async, automatic OpenAPI, and Pydantic integration.

## Decision

Stay on Flask. Add `apiflask` or `flask-pydantic` for typed request/response schemas and generated OpenAPI documentation.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Migrate to FastAPI | A rewrite of the HTTP layer for benefits largely obtainable by adding a library — while simultaneously adding a database and a new frontend. Three destabilising changes at once. |

## Consequences

+ Zero migration cost; existing routes and tests keep working
+ Typed schemas and OpenAPI obtained via library
− No native async; concurrent LLM calls handled with threads
− Revisit only if async concurrency becomes a measured bottleneck
