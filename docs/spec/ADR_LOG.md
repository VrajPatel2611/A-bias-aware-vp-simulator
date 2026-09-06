# VPSim — Architecture Decision Records

One decision per record. **Accepted ADRs are never edited** — they are superseded by a new record.

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

# ADR-0002 · Supabase Auth rather than custom authentication

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The product needs accounts, OAuth, and password reset. App Store policy requires Sign in with Apple if any other social login is offered. The team has no security reviewer, and a mistake here compromises medical professionals' accounts.

## Decision

Delegate authentication to Supabase Auth. Verify JWTs in the backend; never handle passwords.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Build our own | ~15 developer-days, permanent security liability, App Store risk, zero differentiating value. |
| Clerk | Good, but a second vendor alongside Supabase-the-database. |
| Auth0 | Enterprise pricing, overkill. |
| Firebase Auth | Users in Google's system, data in Postgres — the split-brain problem of ADR-0001. |

## Consequences

+ ~1 day to integrate versus ~15 to build
+ Users live in our own Postgres (`auth.users`) — no data lock-in
+ Google and Apple OAuth handled, including Apple private-relay emails
+ Free to 50 000 monthly active users
− Auth availability is now a dependency
− Some customisation of email templates is constrained

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

# ADR-0004 · Rule-based bias detection, not machine learning

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The three detectors must produce feedback a learner can act on. We have 16 real sessions — nowhere near enough to train a classifier. The detectors were validated at 94 % accuracy with 100 % sensitivity.

## Decision

Detection stays rule-based and deterministic. Every flag returns a human-readable reason and the evidence that triggered it.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Train a classifier on session features | No labelled corpus; 16 sessions is noise; destroys traceability. |
| LLM-as-judge for bias detection | Non-deterministic, unauditable, and would put the LLM in the marking path (ADR-0005). |

## Consequences

+ Every flag is explainable and contestable — the property that makes feedback teachable
+ Deterministic, so results are reproducible and verifiable
+ Fast (microseconds) and free
− Bounded by lexical coverage; paraphrased questions are missed
− Thresholds are heuristic, not calibrated (see ADR-0013)
− Revisit only with 10³+ labelled sessions, and then as a comparator, not a replacement

# ADR-0005 · The LLM is excluded from the marking path

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

The system uses an LLM for the patient persona and for feedback prose. Assessment results must be reproducible for research credibility and for the data-integrity check.

## Decision

The LLM generates text only. Every flag, score, coverage figure and verdict is computed by deterministic Python. No assessment decision is delegated to a model.

## Alternatives considered

| Option | Why rejected |
|---|---|
| LLM scores the consultation | Non-reproducible at temperature > 0; unauditable; would have made the pilot integrity check impossible. |
| Hybrid — LLM adjusts rule output | Inherits the worst of both: non-determinism without interpretability. |

## Consequences

+ Recomputation from stored questions verifies data authenticity (used in the pilot)
+ Threshold replay is possible
+ Assessment latency is sub-millisecond and free
+ Removes an entire class of prompt-injection attack on grading
− Assessment quality is bounded by rule quality

# ADR-0006 · Next.js for the consumer app, Jinja + HTMX for admin

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | reverses an earlier Jinja-only recommendation |

## Context

The original recommendation was server-rendered Jinja + HTMX throughout, on the assumption that no mobile app meant no API was needed. The product now targets native apps, which require a JSON API. React Native shares concepts and code with React; Jinja templates share nothing with a mobile app.

## Decision

Consumer web app in Next.js + TypeScript. Mobile in React Native + Expo, reusing the API client. Admin console stays Jinja + HTMX.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Jinja + HTMX everywhere | Means writing the frontend twice once mobile arrives (~22–31 days of migration). |
| Next.js everywhere including admin | Admin is internal, form-heavy, low-traffic — server rendering genuinely wins there, and it does not block API work. |
| Vue / Svelte | No React Native equivalent with comparable maturity. |

## Consequences

+ The API is built once and serves web, mobile, and any future client
+ React knowledge transfers to React Native
+ Admin console can be built in parallel without blocking API work
− ~8–10 extra days of initial effort versus Jinja-only
− JavaScript dependency churn is a real ongoing cost; mitigate by keeping dependencies minimal

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

# ADR-0013 · Prebuilt embeddings first; fine-tune later

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

Keyword matching caused every detector error observed in validation. Semantic matching would fix it. Training an embedding model from scratch is not viable; fine-tuning requires labelled pairs we do not yet have.

## Decision

Ship with a prebuilt sentence-transformer in a hybrid keyword-plus-embedding matcher. Collect labelled pairs through an admin review queue. Fine-tune once ~2 000 pairs exist, and only ship the fine-tuned model if it beats the baseline on a held-out set.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Train from scratch | Millions of pairs, multi-GPU weeks — not viable for this team, and unnecessary. |
| Fine-tune immediately | Would overfit on a few hundred hand-made pairs and perform worse than the baseline. |
| API embeddings | Adds latency, cost, and an external dependency to every question. |

## Consequences

+ Ships now at zero cost, on CPU, with data never leaving the server
+ Creates the labelled corpus as a by-product of normal operation
+ Fine-tuning later is a contained, measurable change
− Encoder version becomes part of `engine_version`; changing it requires replay

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
