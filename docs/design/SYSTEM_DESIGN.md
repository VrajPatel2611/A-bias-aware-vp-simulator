# VPSim — System Design & Engineering Specification

**Project:** Bias-Aware Virtual Patient Simulator
**Authors:** Vraj Patel (202301408), Yogesh Bagotia (202301114)
**Mentor:** Abhishek Gupta · DAU (Dhirubhai Ambani University)
**Document status:** Draft v1.0 — for review
**Scope:** Everything required to take VPSim from a validated research prototype to a deployable, multi-tenant web platform.

---

## How to read this document

This is a **decision document**, not a tutorial. Every technology choice below records the alternatives considered and why they were rejected. Where a decision is genuinely open, it is flagged in §16 rather than silently assumed.

Sections are ordered by dependency: you cannot build the Case Factory (§5) before the data model (§3), and you cannot deploy (§9) before session state leaves process memory (§4.2).

**Deliberately excluded from this document**, with reasons, in §15.3 — read that before asking "why is there no Kubernetes section."

---

## Contents

**1. [Current state assessment](#1-current-state-assessment)**

&nbsp;&nbsp;&nbsp;&nbsp;1.1 What exists and works  
&nbsp;&nbsp;&nbsp;&nbsp;1.2 What blocks production use  
&nbsp;&nbsp;&nbsp;&nbsp;1.3 Design properties worth preserving  
**2. [Target architecture](#2-target-architecture)**

&nbsp;&nbsp;&nbsp;&nbsp;2.1 System context  
&nbsp;&nbsp;&nbsp;&nbsp;2.2 Runtime components  
&nbsp;&nbsp;&nbsp;&nbsp;2.3 The end-to-end data flow  
&nbsp;&nbsp;&nbsp;&nbsp;2.4 Why event sourcing here  
**3. [Data architecture](#3-data-architecture)**

&nbsp;&nbsp;&nbsp;&nbsp;3.1 Database selection  
&nbsp;&nbsp;&nbsp;&nbsp;3.2 Logical data model  
&nbsp;&nbsp;&nbsp;&nbsp;3.3 Schema (DDL)  
&nbsp;&nbsp;&nbsp;&nbsp;3.4 Indexing strategy  
&nbsp;&nbsp;&nbsp;&nbsp;3.5 Migrations  
&nbsp;&nbsp;&nbsp;&nbsp;3.6 Migration from JSON files  
&nbsp;&nbsp;&nbsp;&nbsp;3.7 Retention and privacy  
**4. [Backend services](#4-backend-services)**

&nbsp;&nbsp;&nbsp;&nbsp;4.1 Application structure  
&nbsp;&nbsp;&nbsp;&nbsp;4.2 Session state — resolving B1  
&nbsp;&nbsp;&nbsp;&nbsp;4.3 The LLM gateway  
&nbsp;&nbsp;&nbsp;&nbsp;4.4 The assessment engine  
&nbsp;&nbsp;&nbsp;&nbsp;4.5 Experiment allocation — resolving B9  
&nbsp;&nbsp;&nbsp;&nbsp;4.6 API surface  
**5. [The Case Factory](#5-the-case-factory)**

&nbsp;&nbsp;&nbsp;&nbsp;5.1 The problem  
&nbsp;&nbsp;&nbsp;&nbsp;5.2 Design principle  
&nbsp;&nbsp;&nbsp;&nbsp;5.3 Pipeline stages  
&nbsp;&nbsp;&nbsp;&nbsp;5.4 Orchestration and scheduling  
&nbsp;&nbsp;&nbsp;&nbsp;5.5 Cost control  
&nbsp;&nbsp;&nbsp;&nbsp;5.6 Reporting  
**6. [Measurement upgrade — embeddings](#6-measurement-upgrade--embeddings)**

&nbsp;&nbsp;&nbsp;&nbsp;6.1 The problem, precisely  
&nbsp;&nbsp;&nbsp;&nbsp;6.2 The approach  
&nbsp;&nbsp;&nbsp;&nbsp;6.3 Model selection  
&nbsp;&nbsp;&nbsp;&nbsp;6.4 Threshold calibration — closing an acknowledged gap  
&nbsp;&nbsp;&nbsp;&nbsp;6.5 Interpretability must survive  
&nbsp;&nbsp;&nbsp;&nbsp;6.6 Explicitly not doing  
**7. [Authentication, roles, multi-tenancy](#7-authentication-roles-multi-tenancy)**

&nbsp;&nbsp;&nbsp;&nbsp;7.1 Decision  
&nbsp;&nbsp;&nbsp;&nbsp;7.2 Roles  
&nbsp;&nbsp;&nbsp;&nbsp;7.3 Tenant isolation  
**8. [Frontend and UI/UX](#8-frontend-and-uiux)**

&nbsp;&nbsp;&nbsp;&nbsp;8.1 Rendering strategy  
&nbsp;&nbsp;&nbsp;&nbsp;8.2 Information architecture  
&nbsp;&nbsp;&nbsp;&nbsp;8.3 Consultation screen  
&nbsp;&nbsp;&nbsp;&nbsp;8.4 Feedback screen  
&nbsp;&nbsp;&nbsp;&nbsp;8.5 Educator dashboard  
&nbsp;&nbsp;&nbsp;&nbsp;8.6 Accessibility and responsiveness  
&nbsp;&nbsp;&nbsp;&nbsp;8.7 Design system  
**9. [Packaging, CI/CD, deployment](#9-packaging-cicd-deployment)**

&nbsp;&nbsp;&nbsp;&nbsp;9.1 Containerisation  
&nbsp;&nbsp;&nbsp;&nbsp;9.2 Deployment target — the Vercel question  
&nbsp;&nbsp;&nbsp;&nbsp;9.3 CI/CD  
&nbsp;&nbsp;&nbsp;&nbsp;9.4 Configuration and secrets  
&nbsp;&nbsp;&nbsp;&nbsp;9.5 Database operations  
**10. [Observability](#10-observability)**

&nbsp;&nbsp;&nbsp;&nbsp;10.1 Structured logging  
&nbsp;&nbsp;&nbsp;&nbsp;10.2 Error tracking  
&nbsp;&nbsp;&nbsp;&nbsp;10.3 Metrics that matter  
&nbsp;&nbsp;&nbsp;&nbsp;10.4 Health endpoints  
&nbsp;&nbsp;&nbsp;&nbsp;10.5 Alerting  
**11. [Security, privacy, ethics](#11-security-privacy-ethics)**

&nbsp;&nbsp;&nbsp;&nbsp;11.1 Threat model  
&nbsp;&nbsp;&nbsp;&nbsp;11.2 Rate limiting  
&nbsp;&nbsp;&nbsp;&nbsp;11.3 Research ethics  
&nbsp;&nbsp;&nbsp;&nbsp;11.4 An honest residual risk  
**12. [Testing strategy](#12-testing-strategy)**

&nbsp;&nbsp;&nbsp;&nbsp;12.1 The pyramid, adapted  
&nbsp;&nbsp;&nbsp;&nbsp;12.2 Fixtures and determinism  
&nbsp;&nbsp;&nbsp;&nbsp;12.3 Adversarial suites worth building  
&nbsp;&nbsp;&nbsp;&nbsp;12.4 Regression on the research claim  
**13. [Roadmap](#13-roadmap)**

**14. [Non-functional requirements](#14-non-functional-requirements)**

**15. [Decision register](#15-decision-register)**

&nbsp;&nbsp;&nbsp;&nbsp;15.1 Adopted  
&nbsp;&nbsp;&nbsp;&nbsp;15.2 Reversed from the brief  
&nbsp;&nbsp;&nbsp;&nbsp;15.3 Deliberately excluded  
**16. [Open decisions](#16-open-decisions)**

**17. [Summary of what is left to do](#17-summary-of-what-is-left-to-do)**


---

---

# 1. Current state assessment

## 1.1 What exists and works

| Component | State | Evidence |
|---|---|---|
| Flask web application, 10 routes | Working | `app.py`, 586 LOC |
| 5 hand-authored clinical cases | Working | `cases.py`, 2 421 LOC |
| Universal menu: 27 examinations, 86 investigations | Working | `MASTER_EXAMINATIONS`, `MASTER_INVESTIGATIONS` |
| Three rule-based bias detectors | **Validated** | 94 % accuracy, 100 % sensitivity, 54 decisions |
| Clinical evaluator (diagnosis verdict + scorecards) | Working | `clinical_evaluator.py` |
| LLM patient + Socratic feedback | Working | Groq / Llama 3.3 70B, rule-based fallback |
| Session logging, 18-field JSON | Working | 16 real participant sessions collected |
| Participant linking (id + sequence) | Working | Enables paired pre/post analysis |
| Statistical analysis pipeline | Working | `analyze_sessions.py`, McNemar + Wilcoxon, stdlib only |
| Detector validation harness | Working | `validate_detectors.py`, regenerates `detector_validation.md` |

**Total: 9 Python modules, 4 902 LOC, 33 pinned dependencies.**

## 1.2 What blocks production use

These are ordered by severity. Each is addressed later in this document.

| # | Blocker | Consequence today | Addressed in |
|---|---|---|---|
| B1 | Session state in a process-local dict | Any restart loses in-flight consultations; cannot run >1 worker | §4.2 |
| B2 | No database | No cross-session queries, no concurrent-safe writes, no cohort management | §3 |
| B3 | No authentication | Anyone with the URL is any participant; IDs are self-declared | §7 |
| B4 | Keyword matching for topic detection | Every detector error traces here; measurement validity ceiling | §6 |
| B5 | No automated tests or CI | Regressions are found by hand, if at all | §12 |
| B6 | Secrets in `.env`, no deployment config | Not deployable to any host as-is | §9 |
| B7 | Cases hand-authored only | Case library cannot grow without weeks of manual work | §5 |
| B8 | No error tracking or structured logs | A production failure would be invisible | §10 |
| B9 | Case order / assignment not controlled by the system | Confounded the pilot's key-test metric; done manually on paper | §4.5 |

## 1.3 Design properties worth preserving

Three properties of the current system are load-bearing and **must survive any refactor**:

1. **The LLM never marks.** All scoring is deterministic Python. This is what makes results reproducible and made the data-integrity check possible.
2. **Every flag is traceable.** Detectors return `reason` and `evidence` strings citing the student's own questions. Any ML upgrade must preserve this.
3. **The session log is the unit of analysis**, not the rendered page. The durable artefact contains raw actions *and* computed results side by side.

> **Design rule for this document:** no proposed change may break properties 1–3.

---

# 2. Target architecture

## 2.1 System context

```
                        ┌──────────────────────────────┐
   Student  ──────────► │                              │
                        │        VPSim Web App         │
   Educator ──────────► │      (Flask + Jinja/HTMX)    │
                        │                              │
   Admin    ──────────► │                              │
                        └───────┬──────────────┬───────┘
                                │              │
                     ┌──────────▼───┐   ┌──────▼──────────┐
                     │  PostgreSQL  │   │   LLM Provider  │
                     │  + pgvector  │   │  (Groq/OpenAI)  │
                     └──────────────┘   └─────────────────┘
                                │
                     ┌──────────▼───────────┐
                     │    Case Factory      │
                     │  (offline pipeline)  │
                     └──────────┬───────────┘
                                │
                  ┌─────────────▼──────────────┐
                  │  Public medical datasets   │
                  │ DDXPlus · MedQA · PMC ·    │
                  │ Synthea                    │
                  └────────────────────────────┘
```

## 2.2 Runtime components

| Component | Responsibility | Process |
|---|---|---|
| **Web app** | HTTP routing, session orchestration, rendering | Gunicorn + Flask, N workers |
| **Assessment engine** | Topic extraction, bias detection, clinical evaluation | In-process library (pure functions) |
| **LLM gateway** | Provider abstraction, retry, cost accounting, fallback | In-process module |
| **PostgreSQL** | All persistent state: users, cases, sessions, events, results | Managed service |
| **Case Factory** | Dataset ingestion → validated cases | Separate CLI / scheduled job |
| **Analysis service** | Cohort statistics, exports | In-process, read-only |

**Deliberately a modular monolith, not microservices.** See §15.3.

## 2.3 The end-to-end data flow

This is the "full pipeline" view — every stage a piece of data passes through.

```
STAGE 1 — CASE ORIGINATION
  Public dataset  →  fetch  →  candidate filter  →  LLM structured extraction
                                                              │
                                          vocabulary mapping ─┤
                                                              ▼
                                           automated QA gates (schema, grounding,
                                                    LLM-judge, trap self-test)
                                                              │
                                                              ▼
                                              case_versions (status=candidate)
                                                              │
                                                    governed publish
                                                              ▼
                                              case_versions (status=published)

STAGE 2 — CONSULTATION
  Student authenticates  →  assigned a case (arm + order from experiment design)
        │
        ├── types question ──► session_events(type=question)
        │                          └─► topic extraction ──► coverage state
        ├── performs exam   ──► session_events(type=exam)
        ├── orders test     ──► session_events(type=investigation)
        └── submits Dx      ──► session_events(type=diagnosis)

STAGE 3 — ASSESSMENT (synchronous, on submit)
  event log  →  reconstruct session state  →  bias_detector    ─┐
                                           →  clinical_evaluator ├─► session_results
                                           →  feedback_generator ┘
                                                              │
                                                              ▼
                                                     rendered feedback

STAGE 4 — ANALYSIS (offline)
  session_results  →  cohort aggregation  →  paired statistics  →  export (CSV/JSON)
                                                              │
                                                              ▼
                                                    educator dashboard
```

**Key architectural change vs today:** Stage 2 writes an **append-only event log**, and Stage 3 *derives* results from it. Today, results are computed from an in-memory object and the raw actions are a by-product.

## 2.4 Why event sourcing here

This is not architectural fashion — it is justified by something already true in this project.

The pilot's data-integrity check worked by **recomputing every bias flag from the stored questions** and confirming it matched. That is exactly event sourcing: the events are the source of truth, and derived state is reproducible from them.

Making it explicit buys four things:

1. **Recomputation.** Change a threshold, replay every historical session, get new results without re-running participants. This directly enables the threshold-calibration work in §6.4.
2. **Crash resilience.** A consultation interrupted at question 5 is fully recoverable — solving blocker B1's data-loss half.
3. **Auditability.** Any published result traces to an immutable event sequence.
4. **Timing analysis.** Per-event timestamps give think-time between questions — a research signal the current system discards entirely.

**Cost:** one extra table and a reconstruction function. Small, and paid back immediately.

---

# 3. Data architecture

> This section is the core of the document. The user explicitly asked that the database not be glossed over.

## 3.1 Database selection

### The decision: PostgreSQL 16 with the `pgvector` extension.

### Requirements driving the choice

| # | Requirement | Source |
|---|---|---|
| R1 | Relational integrity across users, cohorts, cases, sessions | Multi-tenant SaaS model |
| R2 | Flexible schema for bias results and scorecards, which evolve | Detector output shape changed twice already |
| R3 | Vector similarity search | §6 embeddings; §5 case deduplication |
| R4 | Concurrent writes from multiple workers | B1, deployment with >1 process |
| R5 | Transactional consistency on session finalisation | Results + events must commit atomically |
| R6 | Analytical queries (window functions, aggregation) | Cohort statistics, paired analysis |
| R7 | Free or near-free at pilot scale | Student project, no budget |
| R8 | Straightforward local development | Two developers, laptops |

### Alternatives evaluated

| Option | Verdict | Reasoning |
|---|---|---|
| **PostgreSQL + pgvector** | ✅ **Selected** | Satisfies R1–R8. `JSONB` covers R2 with GIN indexing; `pgvector` covers R3 in the same engine, so no second datastore; mature window functions cover R6. Free managed tiers exist (Neon, Supabase). |
| SQLite | ❌ Rejected | Single-writer lock fails R4. Fine for the current single-user prototype, fatal for concurrent web use. Retained only as the local test-suite backend where the schema is Postgres-compatible. |
| MongoDB | ❌ Rejected | The data is *strongly* relational — a session belongs to a user, a case version, a cohort, an experiment arm. Modelling that in documents means either duplication or client-side joins. R2 is the only argument for Mongo, and `JSONB` answers it without giving up R1/R5. |
| MySQL / MariaDB | ❌ Rejected | Viable but strictly worse here: weaker JSON operators, no first-class vector extension, weaker analytical SQL. No compensating advantage. |
| Firebase / Firestore | ❌ Rejected | NoSQL (fails R1/R6), vendor lock-in, query model unsuited to paired statistical analysis. |
| Postgres + separate vector DB (Pinecone, Qdrant, Weaviate) | ❌ Rejected **for now** | Two datastores, two failure modes, two consistency problems, for a corpus of ~10³–10⁴ vectors. `pgvector` handles this scale comfortably. Revisit only past ~10⁶ vectors. |
| DuckDB | ❌ Rejected as primary | Excellent for the *analysis* layer, not an OLTP store. May be adopted in §8 for heavy cohort analytics reading from Postgres exports. |

### Hosting

| Provider | Recommendation |
|---|---|
| **Neon** | ✅ **Primary recommendation.** Serverless Postgres, generous free tier, database branching (a real advantage — branch the DB per pull request), `pgvector` supported. |
| **Supabase** | ✅ Strong alternative. Postgres + `pgvector` + built-in Auth + storage. Choose this if §7 auth is to be outsourced rather than built. |
| Railway / Render managed Postgres | Acceptable; simpler but no branching. |
| Self-hosted | ❌ Not until there is an ops owner. |

> **Recommended pairing:** Supabase if you want Auth solved for free; Neon if you prefer to own auth and value DB branching in CI. **Default: Supabase**, because §7 auth is otherwise a week of work with real security risk.

## 3.2 Logical data model

Nine core entities.

```
institutions ──< users ──< cohort_members >── cohorts
                   │                             │
                   │                             ├──< case_assignments >── case_versions
                   │                             │                              │
                   └──────────< sessions >───────┘                              │
                                   │  └──────────────────────────────────────────┘
                                   ├──< session_events        (append-only)
                                   ├──── session_results      (1:1, derived)
                                   └──< feedback_texts

cases ──< case_versions ──< case_ingestion_runs (provenance)
topic_lexicon ──< topic_phrases ──< phrase_embeddings
```

## 3.3 Schema (DDL)

### 3.3.1 Tenancy and identity

```sql
CREATE TABLE institutions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE user_role AS ENUM ('student', 'educator', 'researcher', 'admin');

CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id    UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    email             CITEXT NOT NULL,
    display_name      TEXT,
    role              user_role NOT NULL DEFAULT 'student',
    -- Pseudonymous research identifier. Analysis exports use this, never email.
    research_pid      TEXT NOT NULL,
    year_of_study     TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    UNIQUE (institution_id, email),
    UNIQUE (institution_id, research_pid)
);
```

**Why `research_pid` is a column and not a derived value:** the pilot proved that participant identity must be assignable by the system, not typed by the student (a typo silently destroys a pair). It is generated on enrolment and never shown alongside email in any export.

### 3.3.2 Cohorts and assignment

```sql
CREATE TABLE cohorts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id  UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    created_by      UUID NOT NULL REFERENCES users(id),
    -- Experiment configuration, e.g. {"design":"crossover","arms":["feedback","control"]}
    study_config    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cohort_members (
    cohort_id       UUID NOT NULL REFERENCES cohorts(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Assigned at enrolment, never at runtime. Fixes pilot blocker B9.
    study_arm       TEXT NOT NULL DEFAULT 'feedback',
    case_order      UUID[] NOT NULL DEFAULT '{}',
    enrolled_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (cohort_id, user_id)
);
```

**`study_arm` and `case_order` are the direct fix for the pilot's largest methodological weakness.** Counterbalancing and control-group allocation become data, assigned deterministically at enrolment, not a paper list.

### 3.3.3 Cases and versioning

```sql
CREATE TYPE case_status AS ENUM ('draft', 'candidate', 'published', 'retired');
CREATE TYPE case_origin AS ENUM ('hand_authored', 'generated');

CREATE TABLE cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT NOT NULL UNIQUE,
    specialty       TEXT,
    origin          case_origin NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE case_versions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id              UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    version              INT  NOT NULL,
    status               case_status NOT NULL DEFAULT 'draft',

    -- The full case payload: patient_intro, system_prompt, anchor_keywords,
    -- alternative_topics, required_topics, contradictory_clues,
    -- minimum_questions, examination{}, investigations{}, accepted_diagnoses[].
    content              JSONB NOT NULL,

    -- Provenance for generated cases
    ingestion_run_id     UUID REFERENCES case_ingestion_runs(id),
    source_dataset       TEXT,
    source_record_id     TEXT,

    -- QA outcomes (see §5.4)
    qa_report            JSONB,
    trap_selftest_passed BOOLEAN,

    content_hash         TEXT NOT NULL,
    embedding            vector(384),          -- for near-duplicate detection
    published_at         TIMESTAMPTZ,
    retired_at           TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (case_id, version)
);

CREATE INDEX ON case_versions USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON case_versions (status) WHERE status = 'published';
```

**Why versioned and immutable:** a session must record *exactly which* case content the student saw. If a case is edited after data collection, historical results become uninterpretable. Sessions therefore reference `case_version_id`, never `case_id`.

### 3.3.4 Sessions and the event log

```sql
CREATE TYPE session_status AS ENUM ('active', 'completed', 'abandoned', 'expired');

CREATE TABLE sessions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cohort_id         UUID REFERENCES cohorts(id) ON DELETE SET NULL,
    case_version_id   UUID NOT NULL REFERENCES case_versions(id) ON DELETE RESTRICT,

    sequence_index    INT NOT NULL,     -- 1st, 2nd, ... case for this user
    study_arm         TEXT NOT NULL,    -- copied from cohort_members at start
    status            session_status NOT NULL DEFAULT 'active',

    confidence_pre    SMALLINT CHECK (confidence_pre BETWEEN 1 AND 5),
    confidence_post   SMALLINT CHECK (confidence_post BETWEEN 1 AND 5),

    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at          TIMESTAMPTZ,
    last_activity_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, sequence_index)
);

CREATE TYPE event_type AS ENUM
    ('question','patient_reply','examination','investigation',
     'early_diagnosis','diagnosis','feedback_viewed');

CREATE TABLE session_events (
    id              BIGSERIAL PRIMARY KEY,
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    seq             INT  NOT NULL,
    type            event_type NOT NULL,
    payload         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, seq)
);
CREATE INDEX ON session_events (session_id, seq);
```

`session_events` is **append-only**. No `UPDATE`, no `DELETE` outside retention policy. This is enforced by a trigger and by role permissions.

### 3.3.5 Derived results

```sql
CREATE TABLE session_results (
    session_id             UUID PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,

    question_count         INT  NOT NULL,
    coverage_pct           NUMERIC(5,2) NOT NULL,
    topics_hit             TEXT[] NOT NULL,
    topics_missed          TEXT[] NOT NULL,

    diagnosis_submitted    TEXT,
    diagnosis_verdict      TEXT NOT NULL,

    anchoring_detected           BOOLEAN NOT NULL,
    anchoring_score              NUMERIC(4,3) NOT NULL,
    premature_closure_detected   BOOLEAN NOT NULL,
    premature_closure_score      NUMERIC(4,3) NOT NULL,
    confirmation_bias_detected   BOOLEAN NOT NULL,
    confirmation_bias_score      NUMERIC(4,3) NOT NULL,

    bias_detail            JSONB NOT NULL,   -- reason + evidence per detector
    exam_scorecard         JSONB NOT NULL,
    investigation_scorecard JSONB NOT NULL,

    -- Reproducibility: which code produced this row
    engine_version         TEXT NOT NULL,
    computed_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**The scalar columns are duplicated out of `bias_detail` deliberately.** Statistical queries filter and aggregate on them constantly; keeping them as typed columns means indexes and no JSON extraction in analytical SQL. `bias_detail` retains the full traceable reason/evidence payload.

**`engine_version` is essential.** It records which detector build produced a result. The pilot already hit this: five files carried a confirmation-bias score of `0.88` from a superseded 8-clue configuration. With `engine_version`, that is a query, not a forensic exercise.

### 3.3.6 Feedback and lexicon

```sql
CREATE TABLE feedback_texts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    lines         TEXT[] NOT NULL,
    generator     TEXT NOT NULL,     -- 'llm' | 'rule_fallback'
    model         TEXT,
    prompt_tokens INT,
    output_tokens INT,
    cost_usd      NUMERIC(10,6),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE topic_lexicon (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_key     TEXT NOT NULL UNIQUE,     -- e.g. 'meal_relationship'
    display_name  TEXT NOT NULL,
    description   TEXT                      -- canonical sentence, embedded for §6
);

CREATE TABLE topic_phrases (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id      UUID NOT NULL REFERENCES topic_lexicon(id) ON DELETE CASCADE,
    phrase        TEXT NOT NULL,
    embedding     vector(384),
    UNIQUE (topic_id, phrase)
);
CREATE INDEX ON topic_phrases USING hnsw (embedding vector_cosine_ops);
```

Moving the 523-phrase lexicon out of `session_tracker.py` and into the database means it can be edited without a deploy, versioned, and embedded for §6.

### 3.3.7 Provenance and audit

```sql
CREATE TABLE case_ingestion_runs (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_dataset     TEXT NOT NULL,
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at        TIMESTAMPTZ,
    triggered_by       UUID REFERENCES users(id),
    config             JSONB NOT NULL,   -- limits, filters, model, seed
    -- PRISMA-style funnel counts (see §5.6)
    stats              JSONB,
    status             TEXT NOT NULL DEFAULT 'running'
);

CREATE TABLE audit_log (
    id           BIGSERIAL PRIMARY KEY,
    actor_id     UUID REFERENCES users(id),
    action       TEXT NOT NULL,
    entity_type  TEXT NOT NULL,
    entity_id    UUID,
    metadata     JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 3.4 Indexing strategy

| Index | Purpose |
|---|---|
| `sessions (user_id, sequence_index)` | Pairing pre/post sessions — the core analytical join |
| `sessions (cohort_id, status)` | Educator dashboard |
| `session_events (session_id, seq)` | Session reconstruction |
| `session_results (diagnosis_verdict)` | Outcome aggregation |
| Partial: `case_versions (status) WHERE status='published'` | Case selection hot path |
| HNSW on `topic_phrases.embedding` | Semantic topic matching (§6) |
| HNSW on `case_versions.embedding` | Near-duplicate detection (§5.3) |
| GIN on `session_results.bias_detail` | Ad-hoc research queries |

## 3.5 Migrations

**Alembic**, autogenerate disabled for review discipline — migrations are written by hand and reviewed. Every migration must be reversible or explicitly documented as irreversible. Applied automatically on deploy via a release command that runs before the new revision receives traffic.

## 3.6 Migration from JSON files

The 16 pilot sessions must survive. A one-off script:

1. Read each `sessions/*.json`
2. Create an `institutions` row for DAU and `users` rows from `participant_id` (email null, role `student`)
3. Create a `cases` / `case_versions` snapshot from the current `cases.py` content, marked `origin='hand_authored'`, version 1, status `published`
4. Create `sessions` rows with `sequence_index` from `session_sequence`
5. Synthesise `session_events` from `questions_asked`, `exams_performed`, `investigations_ordered`, `diagnosis_submitted` — ordering is partially lost (the JSON does not record interleaving), so events are emitted in that block order with a `provenance: "backfilled"` marker
6. Insert `session_results` verbatim, `engine_version = 'pilot-2026-07'`

**The backfill marker matters.** Backfilled events must never be mistaken for genuine timing data, and any think-time analysis must exclude them.

## 3.7 Retention and privacy

| Data | Retention | Rationale |
|---|---|---|
| `session_events` (raw question text) | 24 months, then anonymised | Free text can contain incidental personal data |
| `session_results` | Indefinite | Anonymous once detached from `users` |
| `users.email` | Until account deletion | Deletion sets `deleted_at`, nulls email, retains `research_pid` |
| `audit_log` | 24 months | |
| LLM prompt/response bodies | **Not stored** | Only token counts and cost. Avoids duplicating student text into a second location. |

**Right to erasure:** deleting a user nulls identifying fields but retains `research_pid`-keyed results, so published analyses remain reproducible. This must be stated in the participant information sheet (§11.3).

---

# 4. Backend services

## 4.1 Application structure

Refactor from flat modules into a package with enforced layering:

```
vpsim/
├── api/                    HTTP layer — routes, request/response schemas
│   ├── consultation.py
│   ├── educator.py
│   └── admin.py
├── domain/                 Pure business logic. No I/O. Fully unit-testable.
│   ├── assessment/
│   │   ├── topics.py           topic extraction (keyword + embedding)
│   │   ├── bias.py             the three detectors
│   │   ├── clinical.py         diagnosis verdict, scorecards
│   │   └── engine.py           orchestration + engine_version
│   ├── session.py          state reconstruction from events
│   └── experiment.py       arm & case-order allocation
├── infra/                  I/O boundaries
│   ├── db/                     SQLAlchemy models, repositories
│   ├── llm/                    provider gateway
│   └── telemetry/
├── factory/                Case Factory (§5)
├── analysis/               statistics, exports
└── web/                    templates, static
```

**The `domain/` layer must not import from `infra/`.** Enforced by an import-linter rule in CI. This is what keeps the assessment engine testable without a database and replayable for recomputation.

## 4.2 Session state — resolving B1

Current: `SESSION_STORE = {}` in process memory.

**Decision: database-backed session state, no Redis.**

| Option | Verdict |
|---|---|
| **Postgres `session_events` + reconstruction** | ✅ **Selected.** One datastore. Survives restart. Enables replay. Reconstruction is O(events) over ~20 rows — sub-millisecond. |
| Redis (Upstash) | ❌ Rejected for now. Adds a second stateful service and a second failure mode to solve a problem Postgres already solves at this scale. Revisit if per-request reconstruction ever shows in profiling. |
| Signed client-side cookie | ❌ Rejected. 4 KB limit; transcripts exceed it; and it would let a student tamper with their own assessment input. |
| Sticky sessions at the load balancer | ❌ Rejected. Preserves the data-loss bug; merely hides it. |

The LLM conversation history is reconstructed from `session_events` of type `question` and `patient_reply`.

## 4.3 The LLM gateway

A single module owning every model call.

```python
class LLMGateway:
    def complete(self, *, messages, system, max_tokens, temperature,
                 purpose: Literal["patient","feedback","extraction","judge"],
                 session_id: UUID | None) -> LLMResult
```

Responsibilities:

- **Provider abstraction.** Groq today; OpenAI, Anthropic, or a local model behind the same interface. Selected per `purpose`, so the cheap fast model plays the patient while a stronger model judges case quality in the Factory.
- **Retry with backoff and jitter.** Current fixed 2 s/4 s becomes exponential with jitter to avoid thundering herds.
- **Circuit breaker.** After N consecutive provider failures, stop calling for a cool-down window and serve the rule-based fallback. Prevents a provider outage from making every consultation hang for 6 seconds before failing.
- **Cost accounting.** Token counts and cost per call written to `feedback_texts` / run stats. Without this, per-student cost is unknown and the platform cannot be budgeted.
- **Prompt versioning.** The patient persona is behaviourally significant; a prompt change alters what information students can extract. Prompts are versioned artefacts recorded on the session.

**Not storing prompt/response bodies** — only metadata. See §3.7.

## 4.4 The assessment engine

Unchanged in logic, restructured for reproducibility:

```python
@dataclass(frozen=True)
class EngineVersion:
    detector_version: str      # semver of the rule set
    lexicon_version: str       # topic lexicon revision
    thresholds: dict           # the actual numeric values used

def assess(session_state, case_content, engine: EngineVersion) -> AssessmentResult
```

**Thresholds become explicit inputs, not constants.** This is what makes §6.4 calibration and §12.4 regression testing possible: you can replay all historical sessions under a candidate threshold set and measure the difference.

## 4.5 Experiment allocation — resolving B9

```python
def allocate(user_id, cohort) -> tuple[arm, case_order]
```

Deterministic from a seeded hash of `(cohort_id, user_id)`, so allocation is reproducible and auditable:

- **Arm:** `feedback` | `control` (control receives outcome-only feedback), block-randomised to keep arms balanced.
- **Case order:** counterbalanced within arm — half receive A→B, half B→A.
- **Case pairing:** cohorts specify a fixed case pair, eliminating the denominator artefact that invalidated the pilot's key-test metric.

Allocation is written to `cohort_members` at enrolment and copied to `sessions.study_arm` at session start, so a mid-study configuration change cannot retroactively alter a completed session's arm.

## 4.6 API surface

REST, JSON, versioned under `/api/v1`. Server-rendered pages remain for the student flow (§8.1).

```
POST   /api/v1/sessions                        start (allocates case)
GET    /api/v1/sessions/{id}                   state
POST   /api/v1/sessions/{id}/questions         ask; returns patient reply
POST   /api/v1/sessions/{id}/examinations
POST   /api/v1/sessions/{id}/investigations
POST   /api/v1/sessions/{id}/diagnosis         finalise; triggers assessment
GET    /api/v1/sessions/{id}/feedback

GET    /api/v1/cohorts/{id}/progress           educator dashboard
GET    /api/v1/cohorts/{id}/results            aggregated, de-identified
POST   /api/v1/cohorts/{id}/export             CSV/JSON job

POST   /api/v1/admin/ingestion-runs            trigger Case Factory
GET    /api/v1/admin/ingestion-runs/{id}
POST   /api/v1/admin/case-versions/{id}/publish
```

**Idempotency:** `POST /diagnosis` accepts an `Idempotency-Key` header. A double-submit must not produce two assessments or two LLM feedback charges.

---

# 5. The Case Factory

> This is the answer to "where do cases come from, when, and how" — the largest single piece of new engineering.

## 5.1 The problem

Each of the five current cases required hand-authoring: patient persona, system prompt, 23–31 anchor keywords, 20–31 alternative keywords, 8 required topics, 6 contradictory-clue sets, examination findings, investigation results with clinical values, and accepted diagnosis phrases. Realistically **several days of work per case**.

A platform serving multiple cohorts needs tens to hundreds of cases, and repeated exposure degrades a trap case's validity — once a student knows Case 1 is reflux, it measures nothing.

## 5.2 Design principle

**A generated case is guilty until proven innocent.** It reaches a student only after passing every automated gate. There is no "probably fine" path.

The pipeline optimises for **precision over recall**: rejecting 95 % of candidates is acceptable; publishing one clinically wrong case is not.

## 5.3 Pipeline stages

```
 1. SOURCE CONNECTOR      dataset → normalised RawRecord
 2. CANDIDATE FILTER      cheap rejects: no clear Dx, too thin, duplicate
 3. EXTRACTION            LLM → strict schema (Pydantic-validated)
 4. VOCABULARY MAPPING    test/exam names → our master lists
 5. GROUNDING CHECK       every clinical fact traceable to source text
 6. LLM JUDGE             independent model scores clinical plausibility
 7. TRAP SELF-TEST        run synthetic transcripts through our own detectors
 8. CASE BANK             persist as status='candidate'
 9. GOVERNED PUBLISH      policy-gated promotion to 'published'
```

### Stage 1 — Source connectors

One adapter per dataset, all emitting a common `RawRecord`.

| Source | Role | Licence posture | Notes |
|---|---|---|---|
| **DDXPlus** | Primary volume | Open (CC) | ~1.3 M synthetic patients with structured evidence and differential. Low hallucination risk. **Start here.** |
| **MedQA (USMLE)** | Trap mining | Open | Exam questions with distractors — the distractors are *literally* pre-identified plausible-but-wrong diagnoses. Excellent trap source. |
| **PMC-Patients** | Narrative realism | Per-article licence — **filter to CC-BY / CC0 only** | Real case-report summaries. Adds authentic phrasing. |
| **Synthea** | Lab-value realism | Open | Synthetic EHR; use to sample realistic reference ranges rather than inventing values. |
| MIMIC-III / IV | Future enrichment | PhysioNet credentialed | Requires training + DUA; **no redistribution**, so derived cases must be checked against the DUA before publishing. Defer. |

> **Known corpus bias:** published case reports over-represent rare diagnoses. Anchoring matters most in *common* presentations. Mitigation: weight generation toward DDXPlus/MedQA, and audit the specialty/prevalence distribution of the case bank (§5.6).

### Stage 2 — Candidate filter

Cheap, deterministic rejects before any LLM spend:

- No unambiguous final diagnosis → reject
- Below a minimum information threshold (history elements, findings) → reject
- Near-duplicate of an existing case: embed the presentation, cosine similarity ≥ 0.92 against `case_versions.embedding` → reject
- Specialty quota for this run already met → defer

### Stage 3 — Structured extraction

Single LLM call per candidate with **schema-forced output**, validated by Pydantic. Not free-text parsing.

```python
class GeneratedCase(BaseModel):
    title: str
    patient_intro: str
    opening_line: str
    correct_diagnosis: str
    accepted_diagnoses: list[str]      = Field(min_length=2)
    partial_diagnoses: list[str]
    anchor_topic: str
    anchor_keywords: list[str]         = Field(min_length=15)
    alternative_topics: list[str]      = Field(min_length=15)
    required_topics: list[TopicKey]    = Field(min_length=6, max_length=10)
    minimum_questions: int             = Field(ge=5, le=12)
    contradictory_clues: list[list[str]] = Field(min_length=4)
    examination: dict[ExamKey, ExamFinding]
    investigations: dict[TestKey, TestResult]
    system_prompt: str
```

`TopicKey`, `ExamKey`, `TestKey` are **enums bound to the existing master lists**. The model physically cannot invent a test key — an unmapped value fails validation.

### Stage 4 — Vocabulary mapping

The model will produce "Chest radiograph" where the master list has `cxr`. Mapping is:

1. Exact key match
2. Alias table lookup (curated, grows over time)
3. Embedding similarity ≥ 0.85 against master-list labels
4. Otherwise → **quarantine**, human review, never auto-added

**Auto-extending the master list is forbidden.** The universal menu's whole purpose is that it is identical across cases; silently adding a test would leak information about the new case.

### Stage 5 — Grounding check

Every clinical assertion must be traceable to the source record. For each generated finding, verify it is supported by the source text (string/entity match, else an LLM entailment check with the source as sole context).

Ungrounded facts are **dropped, not corrected**. If dropping leaves the case below the minimum-information threshold, the whole case is rejected.

This is the primary hallucination control.

### Stage 6 — LLM judge

An **independent model** (different provider or at minimum a different model to reduce correlated error) scores the candidate 1–5 on:

- Clinical plausibility of the presentation
- Internal consistency of findings and lab values
- Whether the trap is genuinely plausible and genuinely wrong
- Whether the case is solvable from the information provided

Any dimension below 4 → reject. The judge sees only the generated case, never the extraction prompt.

### Stage 7 — Trap self-test (the novel gate)

**This is the contribution worth publishing.** Every generated case is unit-tested against the same detectors that grade students.

Synthesise scripted transcripts:

| Synthetic student | Expected detector output |
|---|---|
| Tunnel-vision on the trap | anchoring ✓, confirmation ✓ |
| Thorough, explores alternatives | all three ✗ |
| Rushed (3 questions) | premature closure ✓ |
| Broad but trap-focused | anchoring ✓, premature ✗ |

If the expected pattern does not hold, the trap is not detectable and the case is **rejected** — regardless of clinical quality. A clinically perfect case that cannot discriminate biased from unbiased reasoning is useless to this platform.

This directly reuses `validate_detectors.py` machinery.

### Stage 8 — Case bank

Persist as `case_versions` with `status='candidate'`, full `qa_report`, `trap_selftest_passed`, and provenance (`ingestion_run_id`, `source_dataset`, `source_record_id`).

### Stage 9 — Governed publish

Two policies, admin-selectable per run:

| Mode | Behaviour |
|---|---|
| **Staged** (default) | Candidates wait; an admin reviews the QA report and publishes a batch with one action. Still zero manual *editing*. |
| **Autonomous** | Anything passing all gates auto-publishes, subject to per-run and per-specialty caps. |

Additional governance:

- **Per-run limits** — total and per-specialty, to prevent a cardiology-only bank
- **Retirement** — a case retires after N uses or M months to limit answer-sharing
- **Rollback** — publishing is reversible; `retired_at` is set, sessions referencing the version remain valid

## 5.4 Orchestration and scheduling

| Option | Verdict |
|---|---|
| **Prefect** or **Dagster** | ✅ **Recommended** for the Factory. Retries, per-stage observability, a UI showing exactly where candidates died. Dagster's asset model fits "a case is an asset with lineage" precisely. |
| Celery + Redis beat | ⚠️ Acceptable. More boilerplate, weaker lineage story, and adds Redis. |
| APScheduler in-process | ⚠️ Fine for a nightly job; poor once stages need independent retry. |
| Plain CLI + cron | ✅ **Correct starting point.** Build the pipeline as an idempotent CLI first; add an orchestrator when run volume justifies it. |

**Recommendation: start as a CLI (`python -m vpsim.factory run --source ddxplus --limit 50`), adopt Dagster when ingestion becomes routine.** Do not introduce an orchestrator to run one job once a month.

## 5.5 Cost control

Every candidate costs 2–4 LLM calls. At scale that is the dominant expense.

- Cheap deterministic filters run **before** any LLM call
- Extraction uses a mid-tier model; the judge uses a stronger one only on candidates that survive extraction
- Per-run token budget, hard-stop on breach
- Full cost recorded in `case_ingestion_runs.stats`

## 5.6 Reporting

Each run emits a **PRISMA-style funnel** — directly publishable:

```
Records fetched                    1000
  ├─ rejected: no clear diagnosis  -412
  ├─ rejected: insufficient detail -156
  └─ rejected: near-duplicate       -38
Extraction attempted                394
  ├─ failed schema validation       -47
  └─ failed vocabulary mapping      -23
Grounding check                     324
  └─ rejected: ungrounded facts     -61
LLM judge                           263
  └─ rejected: score < 4            -88
Trap self-test                      175
  └─ rejected: trap undetectable    -52
─────────────────────────────────────────
Published candidates                123   (12.3 % yield)
```

Plus a bank-composition audit: specialty distribution, trap-type distribution, prevalence (common vs rare) — the check against the case-report rarity bias.

---

# 6. Measurement upgrade — embeddings

> Resolves blocker B4, the ceiling on measurement validity, and is the project's genuine ML component.

## 6.1 The problem, precisely

`extract_topics()` does case-insensitive substring matching against 523 phrases. All three detector-validation errors were false positives on transcripts where a **thorough** student used non-standard vocabulary — *"does a rich evening dinner set it off?"* never matches the `meal_relationship` lexicon.

This is not a tuning problem. It is a representational one: lexical matching cannot capture semantic equivalence.

## 6.2 The approach

Replace exact matching with **semantic similarity in embedding space**, retaining keywords as a high-precision fast path.

```
question ──► embed ──► cosine vs topic embeddings ──► max similarity
                                                          │
                                    ≥ τ_high  ────────────┤──► covered
                                    keyword hit ──────────┘
                                    < τ_low   ──────────────► not covered
                                    between   ──────────────► log for review
```

**Hybrid, not replacement.** A keyword hit is strong evidence and cheap; embeddings catch what keywords miss. Union of the two, with the ambiguous band logged to build a labelled set for calibration.

## 6.3 Model selection

| Option | Verdict |
|---|---|
| **`sentence-transformers/all-MiniLM-L6-v2`** (local, 384-dim) | ✅ **Selected.** Runs on CPU, ~80 MB, no per-call cost, no network dependency in the request path, data never leaves the server. Sufficient quality for short-question similarity. |
| `BAAI/bge-small-en-v1.5` (local, 384-dim) | ✅ Strong alternative, usually better on retrieval benchmarks. Benchmark both on your own labelled set and pick empirically. |
| Domain models (BioBERT, PubMedBERT, MedCPT) | ⚠️ **Worth benchmarking.** Clinical-domain pretraining may help on medical vocabulary. But student questions are colloquial, not clinical prose, so the advantage is not guaranteed. Evaluate; do not assume. |
| OpenAI `text-embedding-3-small` (API) | ❌ Rejected for the request path. Adds latency, cost, and an external dependency to every question. Acceptable for offline batch work. |

**Embeddings for topics and phrases are precomputed and stored in `topic_phrases.embedding`.** Only the incoming question is embedded at request time — a single CPU forward pass, ~5–15 ms.

## 6.4 Threshold calibration — closing an acknowledged gap

The report states plainly that thresholds (0.60, 0.60, 0.25) were "sensible but not tuned with data". Two calibration tasks follow:

**(a) Similarity threshold τ.** Requires a labelled set of (question, topic, covered?) pairs. Bootstrap from the existing 523 phrases as positives plus sampled negatives; extend with real pilot questions labelled by hand.

**(b) Detector thresholds.** Now tractable because of event sourcing (§2.4): replay every historical session under candidate threshold values and measure sensitivity/specificity against the labelled transcripts.

> ⚠️ **Methodological warning.** Tuning against the 18-transcript validation set destroys it as a test set. Calibration requires a **separate, larger labelled corpus**, ideally clinician-labelled, with a held-out split. Report both the tuning set and the held-out result. This is exactly the mistake the report currently avoids by *not* tuning.

## 6.5 Interpretability must survive

Non-negotiable: feedback quality depends on `reason` and `evidence` strings.

With embeddings, the evidence becomes: *"'Does a rich evening dinner set it off?' matched topic 'meal relationship' (similarity 0.81)."* Still fully traceable — arguably more informative than "contained the word 'meal'".

**Any change that reduces a flag to an unexplained number is rejected**, per the design rule in §1.3.

## 6.6 Explicitly not doing

**Training a classifier to predict bias from session features.** Tempting, wrong at this stage:

- Requires a large labelled corpus that does not exist
- Destroys traceability — the property that makes the feedback teachable
- The pilot has 16 sessions; anything trained on that is noise

Revisit only with 10³+ labelled sessions, and even then as a *comparator* to the rule engine, not a replacement.

---

# 7. Authentication, roles, multi-tenancy

## 7.1 Decision

**Use Supabase Auth** (or Auth0) rather than building authentication.

| Option | Verdict |
|---|---|
| **Supabase Auth** | ✅ **Recommended.** Email/password + magic link + OAuth, JWT-based, integrates with the Postgres already chosen. Free tier covers pilot scale. Eliminates the highest-risk hand-rolled component. |
| Auth0 / Clerk | ✅ Viable; more polished, free tiers tighter. |
| Flask-Login + hand-rolled password hashing | ❌ **Rejected.** Password reset, session fixation, timing attacks, credential stuffing, email verification — a week of work with real security exposure, in a project with no security reviewer. |
| Institutional SSO (SAML / Shibboleth) | ⏸ Deferred. Required for real university deployment; unnecessary until an institution commits. |

## 7.2 Roles

| Role | Capabilities |
|---|---|
| **Student** | Start assigned cases, view own feedback, view own history |
| **Educator** | Create cohorts, enrol students, assign case pairs, view **aggregated** cohort results |
| **Researcher** | De-identified exports across cohorts; no access to identifying fields |
| **Admin** | Case Factory runs, publishing, lexicon edits, institution management |

**Educators see aggregates and individual progress, not raw transcripts by default.** A student's free-text questions are their work; exposing them by default invites both privacy problems and grade-anxiety effects that would distort the measurement.

## 7.3 Tenant isolation

Every tenant-scoped table carries `institution_id`. Enforcement at two layers:

1. **Application:** a repository base class that requires a tenant context; no query bypasses it
2. **Database:** Postgres **Row-Level Security** policies keyed on a session GUC (`app.current_institution`)

RLS is defence in depth — an application bug then fails closed rather than leaking across institutions.

---

# 8. Frontend and UI/UX

## 8.1 Rendering strategy

**Decision: keep server-rendered Jinja templates; add HTMX for interactivity. Do not adopt a SPA framework.**

| Option | Verdict |
|---|---|
| **Jinja + HTMX + Alpine.js** | ✅ **Selected.** The app is form-and-panel shaped: submit a question, swap in a reply; click a test, swap in a result. HTMX does exactly this with no build step, no bundler, no API duplication. Keeps the two-developer team on one language. |
| React / Next.js SPA | ❌ Rejected **for now.** Would require building and maintaining a full JSON API purely to serve one frontend, plus a build toolchain, plus SSR decisions — for an application with no offline requirement, no complex client state, and no mobile app yet. Reconsider only when a native app or a rich analytics dashboard justifies it. |
| Vue / Svelte | ❌ Same reasoning as React. |
| Current vanilla JS | ⚠️ Works, but `chat.js` will accrete state-management logic as features grow. HTMX replaces most of it declaratively. |

> **Consequence for §9:** because the frontend is server-rendered, **Vercel is the wrong deployment target.** See §9.2.

## 8.2 Information architecture

```
/                          landing / sign-in
/dashboard                 student: assigned cases, history
/consult/{session_id}      the consultation (3 panes)
/feedback/{session_id}     post-consultation report

/educator/cohorts          list, create
/educator/cohorts/{id}     roster, progress, aggregate results
/educator/cohorts/{id}/export

/admin/cases               bank browser, QA reports, publish
/admin/ingestion           runs, funnel, trigger
/admin/lexicon             topic phrase editor
```

## 8.3 Consultation screen

Three-pane layout, preserving the current model:

| Pane | Content |
|---|---|
| **Left** | Patient card — name, age, presenting complaint, vitals if examined |
| **Centre** | Conversation transcript; question input at the bottom |
| **Right** | Tabbed: **Examinations** (27) · **Investigations** (86, grouped by specialty) · **Ordered** (what you have) |

**Deliberate UX constraints that protect the measurement:**

- **No progress indicator, no question counter.** Showing "6/8 topics covered" would coach the student toward the metric and invalidate it. This is a measurement instrument first.
- **No search-ranking of tests by relevance.** The universal menu must appear undifferentiated. Alphabetical / specialty grouping only.
- **No "are you sure?" nudge before submitting.** That is itself an anti-premature-closure intervention and would contaminate the control arm.
- **Results appear inline in the Ordered pane**, not as modals — students should be able to re-read prior results while deciding.

## 8.4 Feedback screen

Progressive disclosure, in this order:

1. **Verdict banner** — colour-coded diagnosis outcome
2. **Process summary** — questions, coverage %, examinations, tests (the numbers)
3. **Socratic feedback** — the LLM-generated reflective questions
4. **History coverage grid** — hit/missed topics
5. **Examination and investigation scorecards** — ✓ key done · ○ key missed · appropriate · ⚠ low value
6. **Reasoning analysis** — the three patterns, with the traceable reason strings

**Retain the current pedagogical choice: the words "bias", "anchoring", "premature closure" never appear in student-facing text.** Labelling a learner is counterproductive; the reflective question is the intervention.

**Control arm sees only stages 1 and 2** — outcome without process feedback. This must be a template-level flag driven by `sessions.study_arm`.

## 8.5 Educator dashboard

- Cohort progress: who has completed which sessions
- Aggregate bias-flag rates, pre vs post, with the paired test
- Coverage distribution
- Most-missed contradictory clues per case — **the most actionable teaching output**, showing exactly what a cohort systematically overlooks
- Export to CSV/JSON

## 8.6 Accessibility and responsiveness

- WCAG 2.1 AA target: keyboard-navigable panels, visible focus, 4.5:1 contrast, ARIA live regions for patient replies
- Colour is never the sole carrier of meaning — scorecard rows carry icon + text, not just red/green
- Responsive down to tablet. **Phone is explicitly out of scope** for the consultation screen: a three-pane clinical interface on a 375 px viewport degrades the task. Feedback and dashboard pages should still work on phone.

## 8.7 Design system

A small token set — colours, type scale, spacing — rather than a component framework. The existing `style.css` (31 KB) should be refactored into tokens + components, not replaced with Tailwind or Bootstrap; adopting a framework now would mean rewriting working, accessible CSS for no functional gain.

---

# 9. Packaging, CI/CD, deployment

## 9.1 Containerisation

**Docker, multi-stage build.** Justified — not cargo cult:

1. The app now needs Postgres, a specific Python version, and (with §6) a downloaded embedding model. "Works on my laptop" stops being reproducible.
2. CI must run the same image that ships.
3. It keeps the deployment target swappable, which matters given §9.2.

```dockerfile
# ---- builder ----
FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Pre-download the embedding model into the image so the first request
# does not pay a cold-start download.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('all-MiniLM-L6-v2')"

# ---- runtime ----
FROM python:3.11-slim
WORKDIR /app
RUN useradd -m -u 1000 vpsim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /root/.cache/huggingface /home/vpsim/.cache/huggingface
COPY --chown=vpsim:vpsim . .
USER vpsim
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/healthz')"
CMD ["gunicorn","--bind","0.0.0.0:8000","--workers","2","--threads","4", \
     "--timeout","120","--access-logfile","-","vpsim.wsgi:app"]
```

`docker-compose.yml` for local development: app + Postgres 16 with `pgvector` + a seed job.

**Worker model:** `--workers 2 --threads 4`. LLM calls are I/O-bound and can block for seconds; threads let a worker serve other requests meanwhile. Do **not** use a single worker — the point of §4.2 was to make multiple workers possible.

## 9.2 Deployment target — the Vercel question

The brief specified Vercel. **I recommend against it, and here is the honest reasoning.**

### Why Vercel is a poor fit

| Issue | Detail |
|---|---|
| Serverless model | Vercel Python runs as serverless functions. Every request may cold-start. Loading a sentence-transformer model per cold start is seconds of latency. |
| Execution time limits | Hobby tier caps function duration (~10 s, ~60 s on Pro). An LLM call with retries can exceed that; the Case Factory certainly does. |
| No persistent process | Fine now that state is in Postgres (§4.2), but connection pooling across ephemeral functions requires a pooler (PgBouncer / Neon pooling) and is a real operational wrinkle. |
| Optimised for a different shape | Vercel is excellent for Next.js/static + edge functions. We chose server-rendered Python (§8.1). Fighting the platform's grain costs more than it saves. |

### Recommendation

| Target | Verdict |
|---|---|
| **Render** | ✅ **Primary recommendation.** Native Docker deploys, persistent web services, managed Postgres, cron jobs (for the Factory), free tier adequate for a pilot, one-file config (`render.yaml`). Simplest correct answer. |
| **Railway** | ✅ Equally good. Slightly nicer DX, usage-based pricing. Choose on preference. |
| **Fly.io** | ✅ Good, more control (regions, volumes), steeper learning curve. |
| **Vercel** | ⚠️ Only if the frontend is later split into Next.js (§8.1 rejected this) with the Python API hosted elsewhere. Then Vercel serves the frontend and calls the API — a sensible split, but it is a *future* architecture, not this one. |
| Cloud Run / ECS / App Engine | ⏸ Correct at scale, unnecessary now, and gated on cloud access the team does not yet have. |

> **Decision: deploy to Render (or Railway) as a Docker web service, with managed Postgres.** Revisit Vercel only if §8.1 is reversed. Migration cost between these providers is low precisely because of §9.1 containerisation — this is the main reason to containerise now.

### Environments

| Environment | Purpose | Data |
|---|---|---|
| `local` | Development | docker-compose Postgres, seeded |
| `preview` | Per-pull-request | Neon/Supabase branch DB, seeded |
| `staging` | Pre-release verification | Anonymised copy |
| `production` | Live cohorts | Real |

## 9.3 CI/CD

**GitHub Actions.**

```
on: pull_request
  ├─ lint          ruff check · ruff format --check
  ├─ typecheck     mypy on vpsim/domain (strict), rest permissive
  ├─ architecture  import-linter: domain/ must not import infra/
  ├─ test          pytest -m "not slow" + coverage gate on domain/
  ├─ validate      python -m vpsim.validate_detectors  ← must stay ≥ 94 %
  ├─ security      pip-audit · gitleaks
  └─ build         docker build (no push)

on: push to main
  └─ all of the above → docker push → deploy staging → smoke test
                                    → manual approval → deploy production
```

**The `validate` step is unusual and important.** The detector-validation harness runs on every pull request, and the build fails if accuracy drops below the published 94 %. **The research claim becomes a CI check.** No refactor can silently degrade the instrument.

## 9.4 Configuration and secrets

- 12-factor: all configuration from environment
- `pydantic-settings` for typed, validated config with fail-fast on boot
- Secrets in the platform's secret store; **never** in the repository
- `.env.example` documents every variable
- `gitleaks` in CI to catch accidental commits

Required variables:

```
DATABASE_URL, LLM_PROVIDER, GROQ_API_KEY, LLM_MODEL_PATIENT, LLM_MODEL_JUDGE,
FLASK_SECRET_KEY, SENTRY_DSN, EMBEDDING_MODEL, ENVIRONMENT, LOG_LEVEL
```

## 9.5 Database operations

- **Backups:** managed provider automated backups; **verify a restore quarterly.** An unverified backup is not a backup.
- **Migrations:** run as a release command before new revisions take traffic
- **Connection pooling:** `pgbouncer` or provider-native pooling; SQLAlchemy pool sized to worker count
- **Zero-downtime schema changes:** expand-migrate-contract. Never drop a column in the same release that stops writing it.

---

# 10. Observability

Blocker B8: a production failure is currently invisible.

## 10.1 Structured logging

JSON to stdout (`structlog`), collected by the platform. Every log line carries `request_id`, `session_id`, `user_id` (pseudonymous), `institution_id`.

**Never log:** raw question text at INFO, email addresses, API keys, LLM prompt bodies.

## 10.2 Error tracking

**Sentry.** Free tier is sufficient. Releases tagged so a regression maps to a deploy. `send_default_pii=False`.

## 10.3 Metrics that matter

| Metric | Why it matters |
|---|---|
| Consultations started / completed / abandoned | Abandonment rate is a UX signal *and* a data-quality signal |
| p50 / p95 latency of `POST /questions` | LLM latency dominates perceived quality |
| LLM error rate, retry rate, circuit-breaker trips | Provider health |
| **LLM cost per completed session** | The unit economic that determines whether this scales |
| Fallback-feedback rate | How often students get rule-based instead of LLM feedback |
| Assessment engine duration | Guard against §6 embeddings regressing the request path |
| Ingestion funnel yield per stage | Case Factory health |

## 10.4 Health endpoints

- `/healthz` — process liveness, no dependency checks
- `/readyz` — database reachable, migrations current, embedding model loaded

## 10.5 Alerting

Keep it small enough to stay meaningful: error rate > 2 % for 5 min · p95 latency > 10 s · LLM circuit breaker open · daily cost above budget · failed migration. Nothing else pages.

---

# 11. Security, privacy, ethics

## 11.1 Threat model

This system holds **educational performance data about identifiable students**. It holds no patient data — every "patient" is synthetic. That materially lowers the regulatory burden (no HIPAA/PHI), but does not make the data non-sensitive: a record showing a student reasoned poorly is reputationally sensitive.

| Threat | Control |
|---|---|
| Cross-tenant data access | Tenant scoping + Postgres RLS (§7.3) |
| Student views another's feedback | Object-level authorisation on every session route |
| Prompt injection via question input | Questions are user turns, never system instructions; system prompt is server-side only |
| Student extracts the diagnosis from the LLM | Persona prompt forbids volunteering; **mitigation is imperfect — see §11.4** |
| Credential compromise | Outsourced to Supabase Auth (§7.1) |
| Secret leakage | gitleaks in CI, platform secret store |
| LLM cost abuse | Per-user and per-session rate limits |
| SQL injection | Parameterised queries via SQLAlchemy only |

## 11.2 Rate limiting

Per user: questions per session (hard cap ~40), sessions per day, ingestion runs per day. Protects both LLM spend and the measurement (a student asking 200 questions is not doing the task).

## 11.3 Research ethics

The pilot ran as an informal prototype test. **A controlled study with a no-feedback control arm is a different proposition** and requires:

- **Institutional ethics review.** A control group that is deliberately denied the educational intervention is exactly what review boards exist to assess. Obtain approval before the study in §13 Phase 4.
- **Informed consent in the product**, versioned, recorded per participant with timestamp
- **Participant information sheet** covering: what is collected, retention (§3.7), the erasure caveat, that results are pseudonymous in analysis, that participation does not affect grades
- **Withdrawal** — a participant can withdraw; their data is excluded from analysis while retaining the aggregate integrity of already-published results

> This is not optional bureaucracy. The report's stated future work — "a proper study with a control group" — cannot ethically proceed without it.

## 11.4 An honest residual risk

The patient persona is enforced by prompt engineering (`"Only reveal information when DIRECTLY asked"`). This is **soft**. A determined student can likely coax information out of the model with a cleverly framed question, and no prompt fully prevents it.

**This directly threatens measurement validity** — if the patient volunteers the NSAID history unprompted, the coverage metric is measuring the model, not the student.

Mitigations to implement:

1. **Leakage detection:** post-hoc check whether a patient reply revealed a required-topic fact that the student's question did not ask for. Flag such sessions for review; exclude from analysis if confirmed.
2. **Adversarial prompt testing** as a CI job — a set of extraction-attempt questions run against each case's persona, asserting no key fact leaks.
3. Report leakage rate as a limitation in any publication.

Currently neither exists. **This is the most under-addressed risk in the project** and deserves to be a named work item (§13, W-14).

---

# 12. Testing strategy

## 12.1 The pyramid, adapted

| Layer | Scope | Tool | Target |
|---|---|---|---|
| **Unit** | `domain/` — detectors, topic extraction, evaluator, allocation | pytest | **≥ 90 % on `domain/`** |
| **Property** | Invariants: `a ≤ q`; scores ∈ [0,1]; detected ⇒ score > 0 | Hypothesis | key functions |
| **Integration** | Repositories, migrations, RLS policies | pytest + testcontainers Postgres | main paths |
| **Contract** | LLM gateway against a recorded-response fake | pytest + VCR-style cassettes | all providers |
| **End-to-end** | Full consultation → feedback | Playwright | 3 happy paths + 2 failure paths |
| **Validation** | The 18 labelled transcripts | existing harness | **≥ 94 %, enforced in CI** |

Coverage is enforced on `domain/` only. Chasing coverage on I/O glue produces tests that assert mocks.

## 12.2 Fixtures and determinism

- LLM calls are **never** live in tests — a fake gateway returns canned replies
- Time is injected, never `datetime.now()` in domain code
- Experiment allocation is seeded, so arm assignment is assertable
- Database tests run in a transaction rolled back per test

## 12.3 Adversarial suites worth building

Two beyond the standard pyramid:

- **Persona leakage suite** (§11.4) — extraction attempts against each case
- **Lexicon disjointness test** — assert no shared substrings between `anchor_keywords` and any `contradictory_clues` entry, per case. **This is the automated test that would have caught the 14 %-sensitivity bug before it shipped.** Write it.

## 12.4 Regression on the research claim

Beyond the 94 % gate: a golden-file test replaying the 16 pilot sessions and asserting the computed results match the stored ones, under the pinned `engine_version`. Any deliberate change to the engine must update the golden file in the same commit, making the change explicit in review.

---

# 13. Roadmap

Ordered by dependency. Effort in developer-days for two developers.

## Phase 0 — Foundation (≈ 8 d)

| ID | Task | Days | Blocks |
|---|---|---|---|
| W-01 | Restructure into `vpsim/` package with `domain`/`infra`/`api` layering | 2 | everything |
| W-02 | pytest + fixtures + fake LLM gateway; unit tests for detectors | 2 | W-03 |
| W-03 | GitHub Actions: lint, typecheck, test, **detector-validation gate** | 1 | all |
| W-04 | Dockerfile + docker-compose (app + Postgres/pgvector) | 1 | W-05 |
| W-05 | `pydantic-settings` config; secrets out of code | 1 | deploy |
| W-06 | **Lexicon disjointness test** (§12.3) | 0.5 | — |
| W-07 | Structured logging + Sentry | 0.5 | — |

**Exit:** every existing behaviour under test, reproducible build, CI enforcing the 94 % claim.

## Phase 1 — Persistence (≈ 12 d)

| ID | Task | Days |
|---|---|---|
| W-08 | SQLAlchemy models + Alembic baseline for §3.3 schema | 3 |
| W-09 | Repository layer + tenant scoping + RLS policies | 2 |
| W-10 | Event-sourced session state; replace `SESSION_STORE` (**B1**) | 3 |
| W-11 | Session reconstruction + assessment from events | 2 |
| W-12 | Backfill script for the 16 pilot sessions (§3.6) | 1 |
| W-13 | Move topic lexicon into `topic_lexicon`/`topic_phrases` | 1 |

**Exit:** no data loss on restart; multiple workers safe; pilot data queryable in SQL.

## Phase 2 — Platform (≈ 14 d)

| ID | Task | Days |
|---|---|---|
| W-14 | **Persona leakage detection + adversarial CI suite** (§11.4) | 2 |
| W-15 | Supabase Auth integration; roles; object-level authorisation | 3 |
| W-16 | Cohort management: create, enrol, assign case pairs | 2 |
| W-17 | Experiment allocation: arms + counterbalanced order (**B9**) | 2 |
| W-18 | Educator dashboard + CSV/JSON export | 3 |
| W-19 | Consent capture and participant information flow (§11.3) | 1 |
| W-20 | Deploy to Render: staging + production, migrations on release | 1 |

**Exit:** an educator can run a properly counterbalanced, consented study without touching a spreadsheet.

## Phase 3 — Measurement (≈ 11 d)

| ID | Task | Days |
|---|---|---|
| W-21 | Embedding pipeline: model, precomputed topic vectors, pgvector | 3 |
| W-22 | Hybrid keyword+embedding topic matcher behind a feature flag | 2 |
| W-23 | Build labelled calibration corpus (separate from the 18) | 3 |
| W-24 | Threshold calibration + sensitivity analysis; publish ROC | 2 |
| W-25 | Replay all historical sessions under both engines; report delta | 1 |

**Exit:** the paraphrase limitation is measured and reduced; thresholds are empirically justified rather than asserted.

## Phase 4 — The real study (≈ 6 d + collection)

| ID | Task | Days |
|---|---|---|
| W-26 | Ethics submission and approval | — (lead time) |
| W-27 | Control-arm feedback variant (outcome-only) | 1 |
| W-28 | Post-study instrument (confidence, perceived usefulness) | 1 |
| W-29 | Analysis: paired tests, arm comparison, multiplicity correction | 2 |
| W-30 | Power analysis to size the study properly | 1 |
| W-31 | Reproducible analysis notebook + anonymised data release | 1 |

## Phase 5 — Case Factory (≈ 20 d)

| ID | Task | Days |
|---|---|---|
| W-32 | `RawRecord` schema + DDXPlus connector | 3 |
| W-33 | Candidate filter incl. embedding deduplication | 2 |
| W-34 | Structured extraction with enum-bound schema | 3 |
| W-35 | Vocabulary mapping + alias table + quarantine | 2 |
| W-36 | Grounding check | 3 |
| W-37 | LLM judge | 2 |
| W-38 | **Trap self-test harness** | 3 |
| W-39 | Admin UI: bank browser, QA reports, governed publish | 2 |

**Exit:** validated cases generated without hand-authoring; the funnel report is publishable.

## Phase 6 — Scale (deferred)

Native mobile, institutional SSO, multi-region, LTI integration with Moodle/Canvas, public API. **All gated on demand that does not yet exist.**

---

# 14. Non-functional requirements

| ID | Requirement | Target | Measured by |
|---|---|---|---|
| NFR-1 | Patient reply latency | p95 < 6 s | Sentry/metrics |
| NFR-2 | Assessment computation | p95 < 500 ms | metric |
| NFR-3 | Page render (non-LLM) | p95 < 400 ms | metric |
| NFR-4 | Availability during a scheduled cohort session | 99.5 % | uptime check |
| NFR-5 | Zero data loss for completed consultations | 100 % | backup restore drill |
| NFR-6 | Concurrent students | 50 without degradation | load test |
| NFR-7 | LLM cost per completed session | < $0.05 | cost metric |
| NFR-8 | Detector accuracy on the validation set | ≥ 94 % | CI gate |
| NFR-9 | Accessibility | WCAG 2.1 AA on student flow | axe audit |
| NFR-10 | Recovery point objective | ≤ 24 h | backup policy |

NFR-6 is deliberately modest: a cohort is a class, not the internet. Designing for 10 000 concurrent users would be speculative.

---

# 15. Decision register

## 15.1 Adopted

| Decision | Choice | Key reason |
|---|---|---|
| Database | PostgreSQL 16 + pgvector | Relational integrity + JSONB flexibility + vectors in one engine |
| DB hosting | Supabase (or Neon) | Free tier, pgvector, Auth included |
| Session state | Event-sourced in Postgres | Fixes B1, enables replay and recomputation |
| Auth | Supabase Auth | Highest-risk component outsourced |
| Web framework | Flask (retained) | Working, well-understood, no migration benefit |
| Frontend | Jinja + HTMX + Alpine | Matches the app's shape; no build step |
| Packaging | Docker multi-stage | Reproducibility + provider portability |
| Deployment | **Render** (or Railway) | Persistent processes, Docker-native, cron for the Factory |
| CI/CD | GitHub Actions | Free, adequate, already where the code lives |
| Migrations | Alembic, hand-written | Reviewable |
| Embeddings | `all-MiniLM-L6-v2` local | No per-call cost or latency; data stays local |
| Factory orchestration | CLI first → Dagster later | Do not add an orchestrator for a monthly job |
| Error tracking | Sentry | Free tier sufficient |
| ORM | SQLAlchemy 2.0 + Alembic | Mature, typed, testable |

## 15.2 Reversed from the brief

| Brief | Recommendation | Reason |
|---|---|---|
| Deploy on **Vercel** | **Render / Railway** | Vercel's serverless model conflicts with a stateful server-rendered Python app, embedding-model load time, and long LLM calls (§9.2). Vercel becomes correct only if the frontend is later split into Next.js. |
| Downloadable app | **Web-first, defer native** | Agreed with the brief's own sequencing. A PWA gives installability without a separate codebase; native only when cloud infrastructure and demand exist. |

## 15.3 Deliberately excluded

Recorded so these are not revisited without new information.

| Excluded | Why |
|---|---|
| **Kubernetes** | Two developers, one service, no autoscaling requirement. Render/Railway provide everything needed. K8s would consume more time than the application. |
| **Microservices** | The Case Factory is already a separate process. Splitting further creates distributed-transaction problems for a system whose entire load fits on one small instance. Modular monolith with enforced layering achieves the same separation without network boundaries. |
| **Kafka / RabbitMQ / SQS** | No high-throughput asynchronous workload. The Factory is a scheduled batch job. Postgres-backed job rows or a cron trigger suffice. |
| **GraphQL** | One frontend, known query shapes. REST is simpler and cacheable. |
| **Separate vector database** | pgvector handles 10³–10⁴ vectors comfortably. Revisit past ~10⁶. |
| **Redis** | Session state is in Postgres (§4.2); no caching hotspot identified. Adding a second stateful service must be justified by a measured problem. |
| **Training a bias classifier** | No labelled corpus; destroys traceability; 16 sessions is noise (§6.6). |
| **Multi-region / CDN for the app** | Users are co-located with the institution. Static assets can use the platform CDN; the app cannot benefit. |
| **Feature-flag SaaS** (LaunchDarkly etc.) | A database table and an environment variable cover current needs. |
| **Data warehouse / dbt** | Postgres answers every current analytical question. Revisit at 10⁵+ sessions. |
| **Native mobile app now** | The consultation UI is poor on a phone (§8.6); a native shell around an unusable layout helps nobody. |

---

# 16. Open decisions

These require a human decision and are **not** assumed by this document.

| # | Question | Options | Recommendation |
|---|---|---|---|
| D-1 | Supabase (Auth included) vs Neon (DB branching)? | Either | **Supabase** — auth is the bigger risk |
| D-2 | Is a no-feedback control arm ethically acceptable to your institution? | — | Ask the ethics committee **before** Phase 4 |
| D-3 | Do educators ever see raw student transcripts? | Never / on request / always | **Never by default**; opt-in per cohort with student notice |
| D-4 | Case retirement policy — after how many uses? | N uses / M months | Start at 50 uses or 6 months, review with data |
| D-5 | Is the platform DAU-only or multi-institution? | — | Build multi-tenant (cheap now, expensive to retrofit) |
| D-6 | Who owns clinical sign-off for generated cases? | — | **Unresolved and important.** Autonomous publishing without any clinician in the loop is defensible for a research instrument, not for a teaching tool used at scale. |
| D-7 | Open-source the platform? | — | Affects licensing of dataset-derived cases (MIMIC DUA in particular) |
| D-8 | LLM provider for production | Groq / OpenAI / Anthropic / local | Keep the gateway abstraction; decide on cost and latency data |

---

# 17. Summary of what is left to do

**Nine engineering blockers**, addressed across six phases, ≈ **71 developer-days** for the platform work plus study-collection time.

The **four highest-value items**, in order:

1. **W-10 — Event-sourced persistence.** Fixes data loss, enables multiple workers, and unlocks replay-based recalibration. Everything else depends on it.
2. **W-14 — Persona leakage detection.** The largest unaddressed threat to measurement validity, and currently invisible.
3. **W-17 — Experiment allocation in the system.** The pilot's methodological weaknesses were all allocation problems solved by two database columns.
4. **W-21/W-24 — Embeddings and calibration.** Converts "thresholds we chose" into "thresholds we justified", and removes the limitation behind every detector error.

The Case Factory (Phase 5) is the largest body of work and the most novel, but it should not start until Phases 0–2 are complete: generating cases into a system that cannot reliably store sessions or allocate them to arms would compound the existing problems rather than relieve them.

---

*End of document. Section §16 requires decisions before Phase 1 begins.*
