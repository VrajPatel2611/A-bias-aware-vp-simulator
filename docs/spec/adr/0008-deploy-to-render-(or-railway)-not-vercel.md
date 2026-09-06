# ADR-0008 · Deploy to Render (or Railway), not Vercel

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The brief proposed Vercel. Vercel runs Python as serverless functions with execution-time caps and cold starts. Our app is a persistent server-rendered Python service that loads an embedding model and makes multi-second LLM calls with retries.

## Decision

Deploy as a Docker web service on Render (Railway equivalent). Managed Postgres via Supabase. Revisit Vercel only if the frontend is split out as a standalone Next.js deployment.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Vercel | Serverless model conflicts with persistent process, embedding-model load time, and long LLM calls. |
| AWS / GCP / Azure directly | Construction kits; unnecessary operational surface for one service and one database at this stage. |
| Self-hosted VPS | No ops owner. |

## Consequences

+ Docker-native deploys, persistent processes, cron for the Case Factory
+ Free tier adequate for pilot; ~$25/month at early launch
+ Containerisation keeps migration cost low if we outgrow it
− Less control than a hyperscaler
− Move to GCP Cloud Run when the bill passes roughly $500/month or a structural need appears
