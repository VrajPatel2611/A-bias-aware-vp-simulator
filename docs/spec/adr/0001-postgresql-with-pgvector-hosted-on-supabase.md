# ADR-0001 · PostgreSQL with pgvector, hosted on Supabase

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

We need persistent storage for users, cases, sessions, an append-only event log, and vector embeddings for semantic topic matching. The team is two developers with no dedicated ops capacity. Data is strongly relational: a session belongs to a user, a case *version*, and an experiment arm.

## Decision

Use a single PostgreSQL 16 database with the `pgvector` extension, hosted on Supabase. One database, one provider.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Neon | Postgres-only. Excellent branching, but no auth or storage, and we need both. |
| MongoDB | Data is relational; document modelling would force duplication or client-side joins. |
| SQLite | Single-writer lock fails under multiple workers. |
| Firebase | NoSQL; unsuited to paired statistical analysis. |
| Postgres + separate vector DB | Two datastores and two failure modes for ~10³–10⁴ vectors. |
| **Supabase + Neon together** | **Actively broken** — users and sessions in separate databases means no foreign keys and no joins. |

## Consequences

+ `JSONB` covers evolving detector output without migrations
+ `pgvector` handles embeddings in the same engine
+ Window functions support paired statistical analysis directly
+ Free tier covers pilot scale
− Inherits Supabase availability
− Forgoes Neon's per-PR database branching
− Revisit vector storage past ~10⁶ vectors
