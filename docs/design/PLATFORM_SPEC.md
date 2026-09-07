> # ⚠️ SUPERSEDED — DO NOT BUILD FROM THIS DOCUMENT
>
> This is **historical record**. It was replaced in full by
> [`docs/spec/`](../spec/README.md), and it describes decisions the current
> specification has since **reversed** — most importantly the frontend choice,
> which is now Next.js + React Native (`ADR-0006`).
>
> **Build from `docs/spec/TECH_SPEC.md` instead.**
>
> It is kept, rather than deleted, for two reasons: the current specifications
> still cite it 15 times for detail not carried forward, and it is the
> record of how the design evolved — which is what makes the reversal in
> `ADR-0006` legible.

---

# VPSim — Platform Specification v2
## Admin Console, Accounts, and the Path to a Commercial Product

**Supersedes:** parts of `SYSTEM_DESIGN.md` v1 — see §0.3 for exactly which.
**Status:** Draft v2.0 — for review
**Authors:** Vraj Patel (202301408), Yogesh Bagotia (202301114)

---

## Contents

**0. Preface — what changed, and why**

&nbsp;&nbsp;&nbsp;&nbsp;0.1 Two answers that changed the architecture  
&nbsp;&nbsp;&nbsp;&nbsp;0.2 One thing I want to flag before anything else  
&nbsp;&nbsp;&nbsp;&nbsp;0.3 What still stands from v1  
**1. Decisions resolved**

**2. Database and platform — the Supabase / Neon question**

&nbsp;&nbsp;&nbsp;&nbsp;2.1 What Neon actually is  
&nbsp;&nbsp;&nbsp;&nbsp;2.2 What Supabase is  
&nbsp;&nbsp;&nbsp;&nbsp;2.3 The decision  
&nbsp;&nbsp;&nbsp;&nbsp;2.4 Your internship question — why did that company have multiple databases?  
&nbsp;&nbsp;&nbsp;&nbsp;2.5 Revised data model for B2C  
**3. Accounts and authentication**

&nbsp;&nbsp;&nbsp;&nbsp;3.1 Your question: build our own, or use Supabase?  
&nbsp;&nbsp;&nbsp;&nbsp;3.2 What building your own actually requires  
&nbsp;&nbsp;&nbsp;&nbsp;3.3 The App Store constraint  
&nbsp;&nbsp;&nbsp;&nbsp;3.4 Decision  
&nbsp;&nbsp;&nbsp;&nbsp;3.5 Account model  
&nbsp;&nbsp;&nbsp;&nbsp;3.6 Integration shape  
**4. The Admin Console**

&nbsp;&nbsp;&nbsp;&nbsp;4.1 Why this matters more than it sounds  
&nbsp;&nbsp;&nbsp;&nbsp;4.2 Console structure  
&nbsp;&nbsp;&nbsp;&nbsp;4.3 Case management  
&nbsp;&nbsp;&nbsp;&nbsp;4.4 Clinical review workflow  
&nbsp;&nbsp;&nbsp;&nbsp;4.5 AI Operations — "how the AI is responding"  
&nbsp;&nbsp;&nbsp;&nbsp;4.6 Clinical content management  
&nbsp;&nbsp;&nbsp;&nbsp;4.7 Users and support  
&nbsp;&nbsp;&nbsp;&nbsp;4.8 Assessment engine controls  
&nbsp;&nbsp;&nbsp;&nbsp;4.9 Building the admin console — the pragmatic path  
**5. LLM strategy**

&nbsp;&nbsp;&nbsp;&nbsp;5.1 The key insight — there are five different jobs  
&nbsp;&nbsp;&nbsp;&nbsp;5.2 J1 — Patient roleplay  
&nbsp;&nbsp;&nbsp;&nbsp;5.3 J2 — Feedback generation  
&nbsp;&nbsp;&nbsp;&nbsp;5.4 J3 and J4 — the Case Factory  
&nbsp;&nbsp;&nbsp;&nbsp;5.5 J5 and the "is an LLM even necessary?" question  
&nbsp;&nbsp;&nbsp;&nbsp;5.6 Estimated cost per session  
**6. Machine learning strategy**

&nbsp;&nbsp;&nbsp;&nbsp;6.1 Your question — can we build our own model?  
&nbsp;&nbsp;&nbsp;&nbsp;6.2 The three options, honestly  
&nbsp;&nbsp;&nbsp;&nbsp;6.3 Why fine-tuning fits your problem specifically  
&nbsp;&nbsp;&nbsp;&nbsp;6.4 How you would actually do it  
&nbsp;&nbsp;&nbsp;&nbsp;6.5 Recommendation and sequencing  
&nbsp;&nbsp;&nbsp;&nbsp;6.6 The bigger ML opportunity you have not asked about  
**7. Frontend and mobile — reversing the v1 decision**

&nbsp;&nbsp;&nbsp;&nbsp;7.1 Why I am changing the recommendation  
&nbsp;&nbsp;&nbsp;&nbsp;7.2 Your question: how hard is it to switch later?  
&nbsp;&nbsp;&nbsp;&nbsp;7.3 Your other question: how hard is React/Next to maintain?  
&nbsp;&nbsp;&nbsp;&nbsp;7.4 Revised recommendation  
&nbsp;&nbsp;&nbsp;&nbsp;7.5 Flask or FastAPI for the API?  
&nbsp;&nbsp;&nbsp;&nbsp;7.6 Mobile-specific considerations  
&nbsp;&nbsp;&nbsp;&nbsp;7.7 Recommended build order  
**8. Infrastructure, cloud, and cost**

&nbsp;&nbsp;&nbsp;&nbsp;8.1 Your question: AWS, GCP, or Azure?  
&nbsp;&nbsp;&nbsp;&nbsp;8.2 Realistic cost breakdown  
&nbsp;&nbsp;&nbsp;&nbsp;8.3 Domain  
&nbsp;&nbsp;&nbsp;&nbsp;8.4 What you do *not* need yet  
**9. Legal, licensing, and liability**

&nbsp;&nbsp;&nbsp;&nbsp;9.1 Dataset licensing — the constraint most likely to bite you  
&nbsp;&nbsp;&nbsp;&nbsp;9.2 Data protection  
&nbsp;&nbsp;&nbsp;&nbsp;9.3 Medical liability positioning  
&nbsp;&nbsp;&nbsp;&nbsp;9.4 Formalising your clinical reviewers  
**10. Research operations under a commercial product**

&nbsp;&nbsp;&nbsp;&nbsp;10.1 The tension  
&nbsp;&nbsp;&nbsp;&nbsp;10.2 What "no-feedback control arm" means — your question  
&nbsp;&nbsp;&nbsp;&nbsp;10.3 Research mode inside a commercial product  
**11. Revised roadmap**

&nbsp;&nbsp;&nbsp;&nbsp;11.1 What to cut if you need to launch sooner  
**12. Open decisions**

**13. Summary**


---

---

# 0. Preface — what changed, and why

## 0.1 Two answers that changed the architecture

Your answers to §16 of v1 contained two that are not minor preference calls. They change what the product *is*.

**D-5 — "Not institutional. A platform where medical professionals come to practise."**

v1 was designed as institutional B2B SaaS: an institution buys it, an educator creates a cohort, students are enrolled and assigned cases. Every part of the data model assumed that hierarchy.

What you actually described is **B2C**: an individual signs up, pays (or doesn't), and practises on their own. There is no educator. There is no cohort. Nobody assigns anything.

That is a different product with a different data model, a different growth model, and a different revenue model.

**The app-store ambition.**

v1 recommended server-rendered Jinja + HTMX and explicitly rejected React/Next.js. That recommendation rested on one assumption: *there is no mobile app, therefore no API is needed, therefore a SPA is pure overhead.*

You have now said you want native apps. A native app requires an API. Once an API exists, the main argument against a JavaScript frontend disappears.

**I am reversing the v1 frontend recommendation.** §7 explains why, and what it costs.

## 0.2 One thing I want to flag before anything else

You are moving from "student research project" to "commercial product used by medical professionals." Three consequences that are easy to miss and expensive to retrofit:

1. **Dataset licences become a legal constraint, not a formality.** Several public medical datasets are non-commercial or prohibit redistribution. Building a paid product on a CC-BY-NC corpus is a licensing breach. §9.1.
2. **You need an explicit "this is education, not clinical guidance" position** — in the product, the terms, and the app-store listing. §9.3.
3. **Your two clinician friends reviewing cases is the right instinct, but it needs to be a documented process**, not a favour. §4.4 and §9.4.

None of these are blockers. All are cheaper now than later.

## 0.3 What still stands from v1

| v1 section | Status |
|---|---|
| §1 Current state assessment | ✅ Unchanged |
| §2 Target architecture, event sourcing | ✅ Unchanged — event sourcing is *more* important now (§4.5) |
| §3 Data architecture | ⚠️ **Revised** — tenancy model changes (§2.3) |
| §4 Backend services | ✅ Mostly stands; API surface expands (§7.4) |
| §5 Case Factory | ✅ Stands; LLM selection per stage now specified (§5.4) |
| §6 Embeddings | ⚠️ **Extended** — fine-tuning path added (§6) |
| §7 Auth | ⚠️ **Replaced** — see §3 |
| §8 Frontend | ❌ **Reversed** — see §7 |
| §9 Deployment | ⚠️ **Extended** — cloud, cost, domain (§8) |
| §10–12 Observability, security, testing | ✅ Stand |
| §15.3 Exclusions | ✅ Stand, with two additions |

---

# 1. Decisions resolved

Your answers, recorded, with consequences.

| # | Question | Your answer | Consequence |
|---|---|---|---|
| D-1 | Supabase or Neon? | *asked for explanation* | **Supabase only.** Full reasoning §2. |
| D-2 | Control arm ethical? | *asked what it means* | Explained §10.2. Wait-list design recommended. |
| D-3 | Educators see transcripts? | **Never** | Moot under B2C — there are no educators. Support-access policy instead, §4.7. |
| D-4 | Case retirement? | **None — unlimited** | Accepted, with anti-answer-sharing mitigations that don't require retirement, §4.3. |
| D-5 | Institutional or open? | **Not institutional** | Architecture pivots to B2C, §2.3. |
| D-6 | Clinical sign-off owner? | **Admin — two clinician friends** | Formalised as a review workflow, §4.4. |
| D-7 | Open source? | **No — commercial** | Licensing constraints become binding, §9.1. |
| D-8 | LLM provider? | *asked for detail* | Per-job matrix, §5. |

**New decisions raised by this document** are collected in §12.

---

# 2. Database and platform — the Supabase / Neon question

## 2.1 What Neon actually is

You said you didn't know what Neon is. Here it is plainly.

**Neon is PostgreSQL, and nothing else.** It is a hosting company that runs Postgres with an unusual internal design:

- **Storage and compute are separated.** Normal Postgres keeps data on the same machine that runs queries. Neon puts data in cloud object storage and runs the query engine separately.
- **Scale-to-zero.** If nobody queries for 5 minutes, the compute shuts down and you stop paying for it. It wakes on the next connection (a few hundred milliseconds).
- **Database branching.** This is the genuinely distinctive feature. You can create a full copy of your database instantly — not by copying data, but copy-on-write, like a git branch. A 50 GB database branches in about a second and initially costs nothing extra.

Branching is useful for one specific thing: **every pull request gets its own real database with real data shape**, so migrations are tested against something realistic before they touch production.

What Neon does **not** give you: authentication, file storage, APIs, realtime, a dashboard for non-developers. It is a database, full stop.

## 2.2 What Supabase is

**Supabase is PostgreSQL plus a platform built around it.** The database underneath is ordinary Postgres — you can connect with `psql`, run any SQL, use any extension including `pgvector`.

On top, it provides:

| Component | What it gives you | Do you need it? |
|---|---|---|
| **Auth** | Email/password, magic link, Google, Apple, GitHub OAuth; JWT issuance; password reset; email verification | **Yes** — §3 |
| **Storage** | S3-compatible object storage with access policies | **Yes, later** — case images, avatars, exports |
| **Auto REST API** | PostgREST generates REST endpoints from your schema | **No** — you will write your own API. Harmless; ignore it. |
| **Realtime** | Subscribe to database changes over websockets | **No** — not needed |
| **Edge Functions** | Deno serverless functions | **No** — your logic lives in the Python app |
| **Dashboard** | SQL editor, table browser, log viewer, user management | **Yes** — genuinely useful, especially early |

**Critical property:** Supabase Auth stores its users in a normal `auth.users` table **inside your own Postgres database**. Your application tables can reference it with a real foreign key. You are not calling an external identity service and hoping it stays up — the user rows are yours, in your database, and you can `SELECT` them.

That single fact removes most of the lock-in objection to a hosted auth provider.

## 2.3 The decision

### **Use Supabase. Only Supabase. Do not use both.**

The reason is not preference — it is that **using both is actively broken**.

If users lived in Supabase and sessions lived in Neon, they would be in two separate Postgres instances. You could not write:

```sql
SELECT u.research_pid, r.coverage_pct
FROM users u
JOIN sessions s   ON s.user_id = u.id
JOIN session_results r ON r.session_id = s.id
WHERE u.subscription_tier = 'pro';
```

No foreign keys across the boundary. No transactional consistency. Every join done in application code. You would be hand-building the worst parts of a distributed database to gain nothing.

**One database. One provider.**

### Why Supabase over Neon specifically

| Requirement | Supabase | Neon |
|---|---|---|
| Postgres + pgvector | ✅ | ✅ |
| Authentication | ✅ Built in | ❌ Build or buy separately |
| File storage | ✅ Built in | ❌ Separate (S3/R2) |
| Non-developer dashboard | ✅ Good | ⚠️ Basic |
| DB branching for CI | ⚠️ Preview branches (newer, less mature) | ✅ Best in class |
| Scale-to-zero cost | ⚠️ Free tier pauses after inactivity | ✅ Genuine scale-to-zero |
| Free tier | 500 MB DB, 50 000 monthly active auth users | 0.5 GB, generous compute |

You need auth. You will need storage. You do not need branching enough to justify running two providers and building auth yourself. **Supabase wins on the requirements that actually bind.**

> If you later find you need Neon's branching badly, you can migrate — it is Postgres to Postgres, `pg_dump` and restore. Not free, but not a rewrite.

## 2.4 Your internship question — why did that company have multiple databases?

You saw a SaaS system with several databases and a separate data centre for incoming data, and asked whether you need that. **You do not.** Here is when companies actually do that, so you can recognise the moment if it arrives.

| Pattern | Why it exists | When you'd need it |
|---|---|---|
| **Separate OLTP and OLAP** | Analytical queries (`GROUP BY` over millions of rows) lock and slow the tables serving live traffic. Companies keep a transactional Postgres and copy into a warehouse (BigQuery, Snowflake, ClickHouse). | When analytics queries measurably slow the app. **First fix is a read replica, not a warehouse.** Realistically past ~10⁶ sessions. |
| **Database-per-tenant** | Hard isolation for enterprise customers who contractually require their data be physically separate. | Only if you sell to institutions with that clause. You are B2C — never. |
| **Data residency** | GDPR-style rules requiring EU data stay in the EU. | If you get EU users and choose to guarantee residency. A single EU region satisfies this; multiple DBs only if you serve several jurisdictions with conflicting rules. |
| **Separate ingestion store** | High-volume event streams (clickstream, telemetry) written to a store optimised for writes, then batched into the main DB. | Your event volume is ~20 rows per consultation. Postgres handles millions. Not applicable. |
| **Microservice-per-database** | Each service owns its data; no cross-service joins. | You have one service. Not applicable. |

**Your growth path, in order:**

```
1  Single Supabase Postgres                     ← you are here, and will be for a long time
2  + read replica for analytics                  ~10⁵ sessions
3  + object storage for large exports            when exports get big
4  + warehouse (ClickHouse / BigQuery)           ~10⁶ events, or when BI needs it
5  Anything more exotic                          only with a measured problem
```

**Do not build step 4 at step 1.** That is the single most common architectural mistake at this stage, and it is expensive: you pay complexity every day for a scale problem you may never have.

## 2.5 Revised data model for B2C

v1's `institutions → cohorts → students` hierarchy goes away as the primary structure. It is replaced by individual accounts with subscriptions.

```sql
-- Supabase provides auth.users (id, email, encrypted_password, confirmed_at, ...)
-- Our profile table extends it 1:1.

CREATE TYPE subscription_tier AS ENUM ('free', 'pro', 'lifetime');
CREATE TYPE professional_role AS ENUM
    ('medical_student','intern','resident','physician','nurse','pa','other');

CREATE TABLE profiles (
    id                  UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name        TEXT,
    professional_role   professional_role,
    year_of_training    SMALLINT,
    country             TEXT,
    specialty_interest  TEXT[],

    -- Stable pseudonymous id used in all analytics and research exports.
    research_pid        TEXT NOT NULL UNIQUE DEFAULT ('U' || substr(gen_random_uuid()::text,1,8)),

    subscription_tier   subscription_tier NOT NULL DEFAULT 'free',
    subscription_ends   TIMESTAMPTZ,

    onboarded_at        TIMESTAMPTZ,
    last_active_at      TIMESTAMPTZ,
    consent_research    BOOLEAN NOT NULL DEFAULT false,
    consent_version     TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

-- Sessions now belong to a person, not a cohort.
ALTER TABLE sessions
    DROP COLUMN cohort_id,
    ADD COLUMN practice_mode TEXT NOT NULL DEFAULT 'free_practice';
        -- 'free_practice' | 'guided_track' | 'research_study'

-- Optional institutional layer, kept nullable so B2B remains possible later
-- without a migration. Costs one column today; saves weeks if you ever sell
-- to a university.
ALTER TABLE profiles ADD COLUMN institution_id UUID REFERENCES institutions(id);
```

**`institution_id` stays as a nullable column.** You are not building the institutional product, but leaving the hook costs nothing now and avoids a painful retrofit if a medical school ever asks for a cohort licence.

New B2C-specific tables:

```sql
-- Progress and engagement — the retention mechanics of a consumer product
CREATE TABLE user_progress (
    user_id             UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
    sessions_completed  INT NOT NULL DEFAULT 0,
    current_streak_days INT NOT NULL DEFAULT 0,
    longest_streak_days INT NOT NULL DEFAULT 0,
    last_session_date   DATE,
    -- Per-bias trend, e.g. {"anchoring":{"last_10_rate":0.2,"trend":"improving"}}
    bias_trends         JSONB NOT NULL DEFAULT '{}'::jsonb,
    specialty_coverage  JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Which cases a user has seen, so we don't repeat them
CREATE TABLE user_case_history (
    user_id         UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    case_id         UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    times_attempted INT NOT NULL DEFAULT 1,
    first_attempt   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_attempt    TIMESTAMPTZ NOT NULL DEFAULT now(),
    best_verdict    TEXT,
    PRIMARY KEY (user_id, case_id)
);

CREATE TABLE subscriptions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    provider              TEXT NOT NULL,   -- 'stripe' | 'apple' | 'google'
    provider_customer_id  TEXT,
    provider_sub_id       TEXT,
    tier                  subscription_tier NOT NULL,
    status                TEXT NOT NULL,   -- active | past_due | cancelled | expired
    current_period_end    TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

# 3. Accounts and authentication

## 3.1 Your question: build our own, or use Supabase?

You said: *if it is free and nice to have our own authentication, do that; if it takes a lot of effort, follow Supabase.*

**It is not free, and it is a lot of effort.** Here is the honest inventory of what "our own auth" means.

## 3.2 What building your own actually requires

| Component | Effort | Risk if wrong |
|---|---|---|
| Password hashing (Argon2id, correct parameters) | 0.5 d | Password database cracked after a breach |
| Registration + email verification (tokens, expiry, single-use) | 1.5 d | Fake accounts; email enumeration |
| Login with constant-time comparison | 0.5 d | Timing attacks reveal valid emails |
| Password reset flow (secure token, expiry, invalidate on use, no enumeration) | 2 d | **The classic account-takeover vector** |
| Session management (rotation, secure cookies, revocation) | 1 d | Session fixation, hijacking |
| Rate limiting + lockout + backoff | 1 d | Credential stuffing succeeds |
| Google OAuth | 1 d | — |
| **Apple Sign In** | 1.5 d | **App Store rejection** if omitted — see §3.3 |
| Email deliverability (SPF, DKIM, DMARC, provider setup) | 1 d | Verification mails land in spam; users cannot sign up |
| MFA (TOTP) | 2 d | — |
| Account deletion / GDPR export | 1 d | Legal exposure |
| Security review and testing | 2 d | — |
| **Total** | **≈ 15 developer-days** | **Ongoing liability, forever** |

Fifteen days is roughly your entire Phase 0 and Phase 1 combined. And unlike the rest of the system, a mistake here is not a bug — it is a breach of medical professionals' accounts, with your name on it.

## 3.3 The App Store constraint

This is decisive and easy to miss.

**Apple's App Store Review Guideline 4.8** requires that if your app offers *any* third-party login (Google, Facebook), you must **also** offer a login option that limits data collection to name and email and does not track — in practice, **Sign in with Apple**.

You will want Google login (it is what most users expect). Therefore you must implement Sign in with Apple. Implementing Sign in with Apple correctly — including the private-relay email addresses Apple issues, which you must handle as real addresses — is genuinely fiddly.

Supabase implements both. Building both yourself adds days and a rejection risk on your first submission.

## 3.4 Decision

### **Use Supabase Auth.**

| Option | Verdict |
|---|---|
| **Supabase Auth** | ✅ **Selected.** Free to 50 000 monthly active users. Email/password, magic link, Google, Apple, GitHub. Users live in *your* Postgres (`auth.users`), so no data lock-in. ~1 day to integrate versus ~15 to build. |
| Clerk | ⚠️ Better UX components, but a second vendor alongside Supabase-the-database, and a tighter free tier. Only if you were not already on Supabase. |
| Auth0 | ⚠️ Enterprise-grade, priced accordingly. Overkill. |
| **Build our own** | ❌ **Rejected.** 15 days, permanent security liability, App Store risk, and no differentiating value. Nobody has ever chosen a learning app because of its bespoke password reset. |
| Firebase Auth | ❌ Would mean users in Google's system and data in Postgres — the split-brain problem of §2.3. |

**The general principle worth internalising:** build what makes your product different; buy what every product needs. Your bias detection is the product. Your password reset is not.

## 3.5 Account model

| Tier | Capabilities |
|---|---|
| **Anonymous / trial** | One case, no account. Results held in browser storage; converted to an account if they sign up. Removes the single biggest signup drop-off. |
| **Free** | Account required. N cases per month, full feedback, progress tracking. |
| **Pro** | Unlimited cases, all specialties, analytics dashboard, export. |
| **Admin / Clinical reviewer** | §4 |

**Recommendation: let people try one full case before signing up.** Requiring registration before the user has experienced the product is the most common and most costly consumer-funnel mistake.

## 3.6 Integration shape

```
Client                    Your Flask/Next API              Supabase
  │                              │                            │
  ├─ sign in ───────────────────────────────────────────────► │
  │ ◄──────────────────── JWT (access + refresh) ──────────── │
  │                              │                            │
  ├─ API call + Bearer JWT ────► │                            │
  │                              ├─ verify JWT signature      │
  │                              │  (JWKS, cached)            │
  │                              ├─ extract sub → user id     │
  │                              ├─ load profile from DB      │
  │                              └─ authorise + serve         │
```

Your backend never handles passwords. It verifies a signed token and looks up a profile. A `@require_auth` decorator and a `@require_tier('pro')` decorator cover essentially every route.

**Row-Level Security** stays as defence in depth: policies keyed on `auth.uid()` mean that even a bug in application code cannot return another user's sessions.

---

# 4. The Admin Console

> This is the largest new section, and the one you asked for most directly. It is designed as the operational cockpit of a company, not a debug page.

## 4.1 Why this matters more than it sounds

Your instinct is exactly right: **you cannot edit code every time a case needs a comma changed.** But the deeper reason is this —

Right now, `cases.py` is 2 421 lines of Python containing clinical content. That means:

- Only a programmer can change a case
- Your clinician friends cannot review anything without reading Python
- Every content fix is a deploy
- A typo in a keyword list is a production incident
- There is no record of who changed what, or why

A professional content platform separates **content** from **code**. The admin console is how content gets managed by the people qualified to manage it — which, for clinical content, is not you.

## 4.2 Console structure

```
/admin
├── Dashboard                 health, usage, cost, alerts at a glance
├── Cases
│   ├── Bank                  browse, filter, search all cases and versions
│   ├── Editor                structured case editing — no code
│   ├── Playtest              run a case as a student, see detector output live
│   ├── Review queue          clinical sign-off workflow
│   └── Analytics             per-case performance and trap effectiveness
├── Clinical Content
│   ├── Examinations          the 27 — add, edit, group, normal findings
│   ├── Investigations        the 86 — add, edit, group, reference ranges
│   └── Topic Lexicon         40 topics, 523 phrases; live match tester
├── AI Operations
│   ├── Conversations         sample and inspect real patient dialogues
│   ├── Leakage monitor       persona-breach detection queue
│   ├── Prompts               versioned prompt management + A/B tests
│   ├── Usage & cost          tokens, spend, latency, errors by model
│   └── Providers             model routing config, failover, budgets
├── Assessment Engine
│   ├── Thresholds            edit with impact preview before applying
│   ├── Validation            run the 18-transcript suite from the UI
│   └── Replay                recompute historical sessions under a new engine
├── Case Factory
│   ├── Runs                  trigger, monitor, funnel visualisation
│   ├── Candidates            review, approve, reject
│   └── Sources               dataset connector config and licence status
├── Users
│   ├── Directory             search, filter, inspect
│   ├── Subscriptions         billing state, manual grants, refunds
│   └── Support               impersonation-free session inspection
├── Analytics
│   ├── Product               DAU/MAU, retention, funnel
│   ├── Learning              aggregate outcomes, bias trends
│   └── Revenue               MRR, churn, LTV
└── System
    ├── Feature flags
    ├── Audit log
    └── Jobs                  background job status
```

## 4.3 Case management

### Case Bank

A filterable table over `case_versions`:

| Column | Purpose |
|---|---|
| Title, specialty, trap type | Identification |
| Status | draft · candidate · in_review · published · retired |
| Origin | hand-authored · generated |
| Version | with a diff link to the previous |
| Clinical sign-off | reviewer name and date, or "unreviewed" |
| Attempts | how many users have played it |
| Trap rate | % who fell for the trap — **the case's actual difficulty** |
| Detector health | whether the trap self-test still passes |

Bulk actions: publish, retire, assign for review, export.

### Case Editor

The critical piece. A structured form, not a code editor:

| Section | Fields |
|---|---|
| **Patient** | Name, age, sex, presenting complaint, opening line, personality notes |
| **Truth** | Correct diagnosis, accepted diagnosis phrases, partial phrases |
| **The trap** | Anchor topic, anchor keywords (tag input), alternative-hypothesis keywords |
| **History design** | Required topics (multi-select from the lexicon), minimum questions |
| **Contradictory clues** | Grouped keyword sets, each a tag list |
| **Examination** | For each of the 27: is it key? what is the finding? (blank ⇒ normal) |
| **Investigations** | For each of the 86: category (key/reasonable/low-value) and result |
| **Persona prompt** | The system prompt, with a live token counter |

Three things the editor must do that a text editor cannot:

1. **Live validation.** Anchor keywords and contradictory clues must not share vocabulary. The editor blocks saving if they overlap — **this is the bug that cost you 14 % sensitivity, made structurally impossible.**
2. **Completeness checks.** Minimum keyword counts, at least two accepted-diagnosis phrases, at least four clue sets, key investigations actually marked.
3. **Draft isolation.** Editing a published case creates a new draft version. Published content is immutable. Sessions always reference the exact version played.

### Playtest

**The single most valuable admin feature**, and the direct answer to "how are the cases looking, how are they working."

A split screen: the student view on the left, the instrumentation on the right.

```
┌──────────────────────────────┬──────────────────────────────────┐
│  Student view                │  Live instrumentation            │
│                              │                                  │
│  You: Is the pain burning?   │  Topics matched:                 │
│  Patient: Yes, a burning...  │    ✓ pain_character (keyword)    │
│                              │                                  │
│  You: Any painkillers?       │  Counters:  q=2  a=0  m=1        │
│  Patient: I take ibuprofen…  │  Coverage:  2/8 = 25%            │
│                              │                                  │
│                              │  Detectors (live):               │
│                              │    Anchoring        ✗  0.00      │
│                              │    Premature        ✓  0.75      │
│                              │    Confirmation     ✗  0.00      │
│                              │                                  │
│                              │  Clues explored: 2/6             │
│                              │    ✓ burning  ✓ ibuprofen        │
│                              │                                  │
│                              │  ⚠ LEAKAGE: patient revealed     │
│                              │    'ibuprofen' — was it asked?   │
└──────────────────────────────┴──────────────────────────────────┘
```

This lets a non-programmer see **exactly** why a detector fired. It is how your clinician reviewers will judge whether a case works. It also surfaces persona leakage while authoring rather than after data collection.

### Handling unlimited cases without retirement (your D-4 answer)

You said no retirement policy — unlimited growth instead. Accepted. But the risk retirement was solving is real: **once a case is popular, answers get shared.** Mitigations that do not require retirement:

| Mechanism | How it works |
|---|---|
| **Randomised selection** | Users never choose a case; the system serves one from the eligible pool, weighted by what they have not seen. |
| **Bank depth** | With hundreds of cases, the probability two users discuss the same one drops sharply. |
| **Case variants** | Same trap, different patient demographics, different incidental details, shuffled reference values. One authored case yields several variants — high value per unit of authoring effort. |
| **Anomaly detection** | Flag sessions that are near-perfect *and* unusually fast, or that order exactly the key tests with zero exploratory ones. Surfaced in admin, not punished automatically. |
| **Difficulty tracking** | If a case's trap rate collapses over time, that is evidence of leakage. Surface it; you can then retire *that* case by choice rather than by policy. |

**Case variants are the highest-leverage item here.** Recommend building variant generation into the Case Factory from the start.

## 4.4 Clinical review workflow

You have two qualified clinicians willing to review. Make it a process.

```
   candidate ──► assigned to reviewer ──► reviewer opens Playtest
                                                 │
                        ┌────────────────────────┼────────────────────┐
                        ▼                        ▼                    ▼
                    approve              request changes           reject
                        │                        │                    │
                        ▼                        ▼                    ▼
                   published            back to draft           archived
                  (signed, dated)      (comments attached)     (reason logged)
```

Stored on the version:

```sql
CREATE TABLE clinical_reviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_version_id UUID NOT NULL REFERENCES case_versions(id) ON DELETE CASCADE,
    reviewer_id     UUID NOT NULL REFERENCES profiles(id),
    decision        TEXT NOT NULL,        -- approved | changes_requested | rejected
    -- Structured scoring so review quality is consistent between reviewers
    scores          JSONB NOT NULL,       -- plausibility, consistency, trap_validity, solvability
    comments        TEXT,
    reviewed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Rule to enforce in code, not policy: no case reaches a paying user without an approving `clinical_reviews` row.** This is both a quality control and, if a user ever complains that a case is clinically wrong, your evidence of diligence.

Give your reviewers a **structured rubric** rather than a free-text box — plausibility, internal consistency, trap validity, solvability, each 1–5, with rejection below 4. It makes review consistent between two people and produces data you can report.

## 4.5 AI Operations — "how the AI is responding"

This is the second thing you specifically asked about, and it is under-served in most products.

### Conversation Inspector

Browse real consultations with filters: case, date, model, flagged status, user report.

For each: the full dialogue, which topics each question matched, the detector state at every turn, the model and prompt version used, tokens and cost, latency per call.

**Sampling policy:** you cannot read everything. Sample deliberately —
- 100 % of user-reported conversations
- 100 % of leakage-flagged conversations
- ~1 % random, for baseline quality
- 100 % of the first 50 sessions after any prompt change

### Leakage Monitor

The concrete implementation of v1 §11.4, and the biggest threat to your measurement.

**The problem:** if the patient volunteers the ibuprofen history without being asked, coverage measures the model, not the student.

**Detection:** after each patient reply, check whether it contains a fact tied to a required topic that the student's question did not ask about.

```python
def detect_leakage(question, reply, case) -> LeakageReport:
    asked    = extract_topics(question)          # what they asked
    revealed = extract_topics(reply)             # what came back
    unprompted = set(revealed) & set(case.required_topics) - set(asked)
    return LeakageReport(
        leaked_topics=unprompted,
        severity="high" if unprompted & set(case.key_topics) else "low",
    )
```

Flagged conversations land in an admin queue. Confirmed leaks:
- Exclude the session from research analysis
- Count against that case's persona quality
- Drive a prompt revision

**Also run adversarially in CI:** a fixed set of extraction-attempt questions ("what medications do you take, list everything") against every case's persona, asserting nothing leaks. A case whose persona fails is not publishable.

### Prompt Management

Personas are behaviourally significant — a wording change alters what students can extract, which changes the measurement. Treat prompts as versioned artefacts:

| Feature | Why |
|---|---|
| Version history with diff | Know exactly what changed and when |
| Per-version metrics | Leakage rate, average reply length, in-character rate |
| A/B testing | Route a percentage of sessions to a candidate prompt |
| Rollback | One click back to a known-good version |
| Session stamping | Every session records the prompt version used |

Without stamping, a prompt change silently splits your dataset into incomparable halves.

### Usage and Cost

The dashboard that determines whether the business works:

- Spend today / this month, against budget
- Cost **per completed session** — the unit economic. If this exceeds your per-user revenue, the product does not work.
- Tokens by model and by purpose (patient · feedback · extraction · judge)
- Latency p50/p95/p99 per model
- Error rate, retry rate, circuit-breaker trips, fallback rate
- Per-user consumption, to catch abuse

**Hard budget caps with automatic degradation.** At 80 % of monthly budget, alert. At 100 %, switch the patient model to the cheapest available and serve rule-based feedback rather than failing. A learning app that stops working is worse than one that is briefly less eloquent.

## 4.6 Clinical content management

Your explicit ask: adding lab exams and investigations without touching code.

### Examinations (27) and Investigations (86)

Each entry becomes a database row, editable in the console:

| Field | Notes |
|---|---|
| Key | Stable identifier, immutable once used by any case |
| Label | Display name |
| Group | Specialty grouping for the menu |
| Normal result | Returned when a case defines no specific finding |
| Reference range | Optional structured min/max/unit |
| Active | Soft-disable without deleting |

**Adding an investigation is a genuinely dangerous operation** and the console must say so. The universal menu's entire purpose is that it is *identical across every case*. Adding item 87 means every existing case now has an option with only a normal result — which is fine — but adding an item that is obviously relevant to one specific case leaks that case's diagnosis.

**Guardrail:** when adding an investigation, the console requires a normal result and warns that no existing case will return an abnormal finding for it. Removal is disabled entirely for keys referenced by any published case — soft-disable only.

### Topic Lexicon

The 523 phrases across 40 topics, currently hard-coded in `session_tracker.py`.

Editing them in the console needs one feature to be safe: **a live match tester.**

```
Test a question:  ┌──────────────────────────────────────────┐
                  │ does a rich evening dinner set it off?   │
                  └──────────────────────────────────────────┘

  Keyword matches:   (none)
  Embedding matches: meal_relationship  0.81  ✓ above threshold
  Result:            meal_relationship COVERED (semantic)
```

This lets a non-programmer answer "why didn't the system recognise that question?" — and it is how the lexicon gets improved by the people who understand clinical phrasing.

**Also surface dead phrases:** any phrase that has never matched a real question in 90 days is noise. Reviewing those keeps the lexicon honest.

## 4.7 Users and support

Directory with search, filters (tier, role, activity, country), and per-user detail.

**Support access must be bounded.** A user writes in saying "the feedback was wrong on my last case." You need to see that session. You do **not** need standing access to everyone's transcripts.

| Control | Rule |
|---|---|
| Session inspection | Requires a stated reason, logged to `audit_log` |
| Time-boxed | Access expires after 24 hours |
| User-visible | The user can see, in their account, that support accessed a session and why |
| No impersonation | Admins never "log in as" a user; they view read-only data |

This is stricter than most early-stage products, and it is the right default for an app used by professionals whose performance data is sensitive.

## 4.8 Assessment engine controls

**Threshold editing with impact preview.** Changing 0.60 to 0.55 silently changes what every future session means. The console must show the consequence before applying:

```
Anchoring concentration threshold:  0.60  →  0.55

Impact on 1 284 historical sessions:
   would newly flag      +117 sessions  (9.1%)
   would no longer flag     0 sessions

Validation suite under proposed thresholds:
   Anchoring          sens 100%   spec  94%   (was 100/100)
   Premature closure  sens 100%   spec  88%   (unchanged)
   Confirmation bias  sens 100%   spec  82%   (unchanged)
   Overall accuracy   93%  (was 94%)   ▼ 1pt

   [ Cancel ]   [ Apply — creates engine v1.4.0 ]
```

This is only possible because of event sourcing: sessions can be replayed. It converts threshold changes from guesswork into a measured decision — and it is the mechanism that finally closes the "thresholds were not tuned with data" limitation in your report.

Also here: run the 18-transcript validation suite on demand, view engine version history, and trigger a full replay to recompute results under a new engine version.

## 4.9 Building the admin console — the pragmatic path

A console with everything in §4.2 is roughly **25–30 developer-days**. You should not build it all before launch.

| Option | Verdict |
|---|---|
| **Custom, in-app, built incrementally** | ✅ **Selected for core tools.** Case editor, Playtest, and AI Ops are product-specific; no off-the-shelf tool can do Playtest. |
| **Metabase** (self-host or cloud) for analytics | ✅ **Strongly recommended.** Connects straight to Postgres, gives dashboards and ad-hoc SQL with a UI, free. **Saves ~8 days** of building analytics screens you would otherwise hand-roll. |
| Retool / Appsmith / Forest Admin | ⚠️ Genuinely useful for CRUD screens (users, subscriptions). Cost scales per seat. Consider for the boring tables; not for Playtest. |
| Django Admin | ❌ Would require migrating the whole app to Django for one feature. |
| Flask-Admin | ⚠️ Fast for raw CRUD, ugly, poor for anything custom. Acceptable as a stopgap on internal-only tables. |

### Recommended build order

| Priority | What | Days | Why first |
|---|---|---|---|
| **P0** | Case Editor + validation | 5 | Without it, content changes need deploys |
| **P0** | Playtest | 4 | Without it, your clinicians cannot review |
| **P0** | Clinical review queue | 2 | Gates publication; D-6 |
| **P1** | AI usage & cost dashboard | 2 | Without it, you cannot price the product |
| **P1** | Leakage monitor | 3 | Largest measurement risk |
| **P1** | Examinations / Investigations editor | 3 | Your explicit ask |
| **P2** | Topic lexicon + match tester | 3 | Enables non-programmer tuning |
| **P2** | Metabase for all analytics | 1 | Buy, don't build |
| **P2** | User directory + support access | 2 | Needed once you have users |
| **P3** | Threshold impact preview | 3 | High value, not urgent |
| **P3** | Case Factory console | 3 | Only once the Factory exists |

**P0 alone is 11 days and unlocks your clinicians.** That is the milestone that matters.

---

# 5. LLM strategy

> Your question: which LLM, for what, and is an LLM even necessary everywhere?

## 5.1 The key insight — there are five different jobs

"Which LLM should we use" has no single answer, because the system makes model calls for five distinct purposes with **completely different requirements**.

| # | Job | Frequency | Latency matters? | Quality bar | Cost sensitivity |
|---|---|---|---|---|---|
| J1 | **Patient roleplay** | ~8× per session | **Critical** — user waits | Consistent persona, refuses to volunteer | **Highest** — dominates spend |
| J2 | **Feedback generation** | 1× per session | Moderate (2–4 s fine) | Pedagogical quality, follows constraints | Low |
| J3 | **Case extraction** | Batch, offline | Irrelevant | Strict schema adherence + medical knowledge | Low |
| J4 | **Quality judge** | Batch, offline | Irrelevant | Holistic clinical reasoning | Low |
| J5 | **Grounding check** | Batch, offline | Irrelevant | Entailment only | Moderate |

Optimising all five with one model means overpaying on J1 or under-delivering on J3.

## 5.2 J1 — Patient roleplay

The highest-volume, most cost-sensitive, most latency-sensitive call. It also has an unusual quality requirement: **the model must be good at withholding information.** Most model evaluation measures helpfulness; you need controlled unhelpfulness.

| Model | Speed | Cost (rough) | Persona discipline | Verdict |
|---|---|---|---|---|
| **Llama 3.3 70B (Groq)** | Exceptional — Groq's hardware is genuinely much faster | Low | Good | ✅ **Keep for now.** Speed is a real UX advantage. |
| **GPT-4o-mini** | Fast | Very low | **Very good** — strong instruction-following | ✅ **Best value candidate.** Test against Groq. |
| **Claude Haiku** | Fast | Low–moderate | **Excellent** at constraint-following | ✅ **Best persona discipline.** Test if leakage is a problem. |
| **Gemini Flash** | Fast | Very low | Good | ✅ Viable; large free tier |
| Frontier models (GPT-4o, Claude Sonnet, Gemini Pro) | Slower | 10–30× higher | Excellent | ❌ Wasteful here — this is roleplay, not reasoning |
| Self-hosted Llama on your own GPU | Depends | High fixed cost | Same as Llama | ❌ Not until volume justifies a GPU bill |

### Recommendation

**Stay on Groq / Llama 3.3 70B for now.** It is fast, cheap, and working.

**Before commercial launch, run a persona-discipline bake-off** — this is a concrete, measurable experiment you should actually do:

1. Take your adversarial extraction prompts (§4.5)
2. Run them against each candidate model on all five cases
3. Measure: leakage rate, in-character rate, average reply length, p95 latency, cost per session
4. Pick on **leakage rate first**, cost second, latency third

Leakage first because leakage corrupts the measurement, and the measurement is the product.

> **Design note:** the LLM gateway (v1 §4.3) already abstracts the provider. Switching J1 is a config change, not a refactor. Keep it that way.

## 5.3 J2 — Feedback generation

Once per session, so cost per call barely matters. Quality does: this is the text the user actually reads and judges the product by. It must also obey hard constraints — never name a bias, never reveal the diagnosis when the student was wrong.

**Recommendation: use a stronger model here than for J1.** GPT-4o, Claude Sonnet, or Gemini Pro. The cost difference across a whole session is cents; the quality difference is what the user perceives as "this app is good."

This is the clearest case in the system for **model tiering**: cheap fast model for the many calls, strong model for the one that matters.

## 5.4 J3 and J4 — the Case Factory

Batch, offline, low volume, high stakes — a bad case reaches real users.

**J3 Extraction** needs reliable structured output. Recommended: **GPT-4o** or **Claude Sonnet**. Both support strict schema-constrained generation, which matters because your `GeneratedCase` schema has enum-bound fields (§v1 5.3).

**J4 Judge must be a different model from J3.** If the same model both writes and grades, its errors are correlated — it will not catch its own blind spots. If extraction uses GPT-4o, judge with Claude Sonnet, or vice versa. This is not paranoia; it is the same reason you do not mark your own exam.

## 5.5 J5 and the "is an LLM even necessary?" question

**This is your best question in the whole brief, and the answer is: no, not everywhere.**

Roughly half the Case Factory does not need an LLM at all. Using one there is slower, more expensive, and *less* reliable because it introduces non-determinism into steps that should be deterministic.

| Pipeline stage | LLM needed? | Better method |
|---|---|---|
| Source connector | ❌ No | Plain parsing code |
| Candidate filter | ❌ No | Rules — has a diagnosis? enough fields? |
| **Deduplication** | ❌ No | **Embeddings + cosine similarity.** Faster, deterministic, ~free |
| **Vocabulary mapping** | ❌ Mostly no | **Fuzzy string match + embeddings.** LLM only for the residual unmapped tail |
| **Extraction** | ✅ **Yes** | Genuinely requires generation — no alternative |
| **Grounding check** | ⚠️ **Partly** | **NLI model** (see below) — cheaper and more consistent than an LLM |
| Judge | ✅ Yes | Holistic clinical plausibility needs a generative model |
| Trap self-test | ❌ **No** | **Your own detectors.** This gate uses zero AI — it is pure code |
| Publish governance | ❌ No | Policy rules |

### The grounding check deserves special attention

Grounding asks: *is this generated fact supported by the source text?* That is exactly **Natural Language Inference** — a well-established task with small, fast, purpose-built models.

A DeBERTa-class NLI model fine-tuned on MNLI classifies (premise, hypothesis) as entailment / neutral / contradiction. It is ~400 MB, runs on CPU, is deterministic, and costs nothing per call. For "does this source text entail this claim?", it is **more appropriate than an LLM** — narrower task, more consistent, auditable.

**Recommendation: use an NLI model for grounding, escalating to an LLM only for cases the NLI model marks uncertain.** This is a genuine engineering improvement over an all-LLM pipeline, not just a cost saving.

### The principle

> **Use an LLM where you need open-ended generation. Use a smaller specialised model where you need classification. Use plain code where you need a decision rule.**

An all-LLM pipeline is the mark of a prototype. A production pipeline uses the cheapest sufficient tool at each stage. Your **trap self-test** — arguably the most important gate — uses no AI whatsoever, and that is a strength.

## 5.6 Estimated cost per session

Rough working, for budgeting. **Verify current provider pricing before relying on these.**

```
Per consultation (~8 questions):
  system prompt   ~800 tok, resent each turn      →  ~6 400 input tok
  growing history                                 →  ~8 000 input tok
  patient replies ~150 tok × 8                    →  ~1 200 output tok
  feedback call    ~2 000 in / ~450 out

  Total ≈ 16 400 input + 1 650 output tokens
```

| Model for J1 | Approx. cost per session |
|---|---|
| GPT-4o-mini | ~$0.003 |
| Llama 3.3 70B (Groq) | ~$0.010 |
| Claude Haiku | ~$0.020 |
| GPT-4o (if misused for J1) | ~$0.060 |

**At 1 000 sessions/month you are spending single-digit to low-double-digit dollars.** LLM cost is not your constraint at this stage — which is precisely why you should optimise for *quality and leakage resistance* on J1, not for the last fraction of a cent.

**One optimisation worth doing early:** prompt caching. Providers increasingly support caching a static prefix (your persona prompt) across turns, cutting input cost substantially. Check availability on whichever provider you settle on.

---

# 6. Machine learning strategy

## 6.1 Your question — can we build our own model?

You asked whether it is possible to make your own embedding model, and whether professionals use prebuilt ones.

**Short answer:** In 2026, "making your own model" almost never means training from scratch. It means **fine-tuning an existing one**. That *is* what professionals do, and it is very achievable for you.

## 6.2 The three options, honestly

| Option | Feasibility | Cost | When it makes sense |
|---|---|---|---|
| **Train from scratch** | ❌ Not viable | Millions of text pairs, multi-GPU weeks, ~$10⁴+ | Never, for a two-person team. Even large labs rarely do this for embeddings now. |
| **Fine-tune a pretrained model** | ✅ **Very viable** | ~1 000–5 000 labelled pairs, <1 hour on a free Colab GPU | **This is your path.** Once you have data. |
| **Use prebuilt as-is** | ✅ Viable today | Zero | **Start here.** Ship it, collect data, then fine-tune. |

## 6.3 Why fine-tuning fits your problem specifically

General embedding models are trained on web text. Your task is narrow and peculiar: matching **colloquial clinical questions** to **canonical topic categories**.

Consider:

```
"does a rich evening dinner set it off?"      →  meal_relationship
"has your chest been hurting after supper?"   →  meal_relationship  +  pain_character
"do you get the burning after you eat?"       →  meal_relationship  +  pain_character
```

A general model gets these roughly right. A model fine-tuned on *your* pairs learns that "sets it off", "brings it on", and "triggers it" are all your `relieving_factors` / trigger construction — vocabulary a general model has no reason to specialise in.

Realistic expectation: **5–15 percentage points** improvement on your matching task. That is meaningful when your current detector errors all stem from matching failures.

## 6.4 How you would actually do it

**Step 1 — Collect labelled pairs.** You already have the seed: 523 phrases mapped to 40 topics are 523 positive pairs. Extend with real questions from sessions, labelled in the admin console (a "was this topic match correct?" review queue writes training data as a by-product of normal operation).

**Step 2 — Build training triplets.** Contrastive learning needs (anchor, positive, negative):

```python
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

model = SentenceTransformer("all-MiniLM-L6-v2")     # start from pretrained

train = [
    InputExample(texts=["does a rich dinner set it off?",
                        "questions about meals, food and eating",   # positive
                        "questions about family medical history"]), # negative
    # ... a few thousand of these
]
loader = DataLoader(train, shuffle=True, batch_size=32)
loss   = losses.TripletLoss(model)                  # or MultipleNegativesRankingLoss

model.fit(train_objectives=[(loader, loss)], epochs=3, warmup_steps=100)
model.save("vpsim-topic-encoder-v1")
```

**Step 3 — Evaluate honestly.** Hold out a test set. Compare fine-tuned against baseline on the *same* held-out data. Only ship if it wins.

**Step 4 — Version it.** The model becomes part of `engine_version`. Changing the encoder changes every coverage score, so historical sessions must be replayed or explicitly marked as computed under a different encoder.

## 6.5 Recommendation and sequencing

```
Now         →  prebuilt all-MiniLM-L6-v2, hybrid with keywords   (v1 §6)
~2k pairs   →  fine-tune, evaluate against held-out set
If it wins  →  ship as vpsim-topic-encoder-v1, bump engine_version, replay
Ongoing     →  admin review queue continuously grows the training set
```

**Do not fine-tune before you have data.** A model fine-tuned on 200 hand-made pairs will overfit and perform worse than the baseline, while feeling like progress.

## 6.6 The bigger ML opportunity you have not asked about

Once you have thousands of sessions, a genuinely novel research direction opens: **predicting bias from partial sessions.**

If, after four questions, a model can predict that a student is heading toward premature closure, the system could intervene *during* the consultation rather than after — a real-time metacognitive prompt.

This is a legitimate contribution and a natural second paper. But it needs:
- 10³+ labelled sessions (you have 16)
- A careful design so the intervention does not simply teach students to game the metric
- An answer to the interpretability problem, since a predictive model loses the traceability that makes your feedback teachable

**Note it as a research direction. Do not build it now.**

---

# 7. Frontend and mobile — reversing the v1 decision

## 7.1 Why I am changing the recommendation

v1 recommended Jinja + HTMX and rejected React/Next.js. That rested on: *no mobile app → no API needed → a SPA is pure overhead.*

You have now said you want native apps. That breaks the premise:

- A native app **requires** a JSON API
- Once the API exists, the duplication argument against a JS frontend disappears
- React and React Native share concepts, patterns, and some code
- Jinja templates share **nothing** with a mobile app — they would be thrown away

**Under the new requirements, Jinja + HTMX means writing the frontend twice.**

## 7.2 Your question: how hard is it to switch later?

Honestly: **it is close to a full frontend rewrite.**

| Work item | Effort |
|---|---|
| Build the JSON API (currently HTML routes) | 5–7 d |
| Rewrite all templates as React components | 8–12 d |
| Rewrite `chat.js` interactions | 3–4 d |
| Auth flow for token-based API | 2–3 d |
| Testing, styling parity | 4–5 d |
| **Total migration** | **≈ 22–31 developer-days** |

Versus starting with Next.js: roughly **+8–10 days** of extra initial effort compared to Jinja.

**Building it twice costs about three times more than building it once, correctly, now.**

## 7.3 Your other question: how hard is React/Next to maintain?

You noted that you have AI assistance, and that changes the calculus — correctly.

The historical arguments against a SPA for a small team were: build tooling complexity, boilerplate, dependency churn, and needing frontend specialists. In 2026:

| Old objection | Status |
|---|---|
| Complex build setup | Largely solved — `create-next-app` and Vercel/Next defaults work |
| Lots of boilerplate | This is exactly what AI assistance is best at |
| Need a frontend specialist | Much less true for standard patterns |
| Dependency churn | **Still real.** Mitigate: minimal dependencies, pin versions, upgrade deliberately |
| State management complexity | Avoidable — server state via TanStack Query, minimal client state |

**Residual honest risk:** JavaScript ecosystem churn is real and does not go away. Discipline matters — resist adding libraries. A Next.js app with five dependencies is maintainable by two people. One with fifty is not.

## 7.4 Revised recommendation

### Split the stack by audience.

| Surface | Technology | Reasoning |
|---|---|---|
| **Student web app** | **Next.js (React) + TypeScript** | Shares patterns with the future mobile app; needs the API anyway; better interaction model for the consultation UI |
| **Mobile apps** | **React Native + Expo** | Reuses React knowledge, API client, and business logic. Expo makes app-store builds genuinely manageable for a small team. One codebase → iOS + Android |
| **Admin console** | **Jinja + HTMX** *(keep it simple)* | Internal, low traffic, form-heavy, no mobile requirement. This is where server rendering genuinely wins — and it means the admin console does **not** block the API work |
| **Backend API** | **Flask (existing) or FastAPI** | See §7.5 |
| **Analytics dashboards** | **Metabase** | Buy, don't build (§4.9) |

This is not a compromise — each surface uses the tool that fits it. The admin console has entirely different constraints from the consumer app, and pretending otherwise costs you.

## 7.5 Flask or FastAPI for the API?

| Option | Verdict |
|---|---|
| **Keep Flask** | ✅ **Recommended.** Your code works, your team knows it, and Flask serves JSON perfectly well. Add `flask-pydantic` or `apiflask` for typed request/response schemas and automatic OpenAPI docs. Migration cost: near zero. |
| **Migrate to FastAPI** | ⚠️ Better async support (useful for concurrent LLM calls), automatic OpenAPI, native Pydantic. But it is a rewrite of `app.py` for benefits you can mostly get by adding a library to Flask. |

**Recommendation: stay on Flask, add typed schemas.** Revisit FastAPI only if async LLM concurrency becomes a measured bottleneck. Do not rewrite a working backend while simultaneously rewriting the frontend and adding a database — that is three destabilising changes at once.

## 7.6 Mobile-specific considerations

Things that only appear once you target app stores:

| Concern | Detail |
|---|---|
| **Apple in-app purchase** | Apple requires IAP for digital subscriptions and takes 15–30 %. You cannot link out to a cheaper web checkout inside the app (rules vary by jurisdiction and are shifting — check current guidance). **Model this into pricing.** |
| **Sign in with Apple** | Mandatory if you offer any other social login (§3.3) |
| **Review latency** | Each release waits on review (typically 1–3 days). Plan releases; do not promise same-day fixes. |
| **Offline** | Consultations need the LLM, so offline play is not possible. But *reviewing past feedback* offline is valuable and easy — cache it. |
| **Push notifications** | The main retention lever for a consumer learning app ("your streak is at risk"). Use sparingly; medical professionals will uninstall over noise. |
| **App size** | Do **not** bundle the embedding model in the app. It runs server-side. |

## 7.7 Recommended build order

```
Phase A   Backend API (Flask + typed schemas)          ← needed by everything
Phase B   Next.js student web app
Phase C   Admin console (Jinja + HTMX, in parallel — different developer)
Phase D   React Native app, reusing the API client
```

Web first is right. It validates the product, is faster to iterate, needs no review cycle, and is where your first users will come from anyway.

---

# 8. Infrastructure, cloud, and cost

## 8.1 Your question: AWS, GCP, or Azure?

**Direct answer: none of them, not yet.**

This is the most common way early products waste money and time. AWS/GCP/Azure are infrastructure *construction kits*. You do not need a construction kit; you need a place to run one container and one database.

| Stage | Platform | Why |
|---|---|---|
| **Now → ~10 000 users** | **Render or Railway + Supabase** | Deploy from a Dockerfile in minutes. No VPC, no IAM, no load balancer config. |
| **~10 000 → 100 000** | Same, scaled up | Add instances, add a read replica. Still no cloud-provider complexity. |
| **Beyond that, or a specific need** | AWS / GCP | Move when you have a concrete reason: cost crossover, a service only they offer, or compliance |

**The signals that mean "now move to a hyperscaler":** your PaaS bill exceeds roughly $500/month, or you need something structural the PaaS cannot do (VPC peering, private networking, GPU inference, strict data residency).

### If you must choose one eventually

| Provider | Strengths | Weaknesses | Startup credits |
|---|---|---|---|
| **AWS** | Widest service range, deepest docs, most hireable skill | Steepest learning curve, easiest to overspend | Activate: often $1k–$100k via accelerators |
| **GCP** | Best developer experience of the three; Cloud Run is genuinely excellent for containers; strong BigQuery | Smaller ecosystem; some services deprecated | Google for Startups: commonly $2k–$200k |
| **Azure** | Best if you land education/enterprise deals; strong compliance story | Least pleasant DX of the three for this workload | Microsoft for Startups: often $5k–$150k |

**If forced today: GCP Cloud Run.** It is the closest hyperscaler product to the Render/Railway model — deploy a container, it scales to zero, you pay per request. The migration from Render to Cloud Run is small precisely because you containerised.

> **Apply for startup credits early.** All three programmes are open to pre-revenue companies and the credits typically cover your first year or two entirely. This is free money that most student projects never claim.

## 8.2 Realistic cost breakdown

### Development / pre-launch

| Item | Cost |
|---|---|
| Render free tier | $0 (sleeps when idle) |
| Supabase free tier | $0 (500 MB DB, 50k MAU) |
| Domain (.com) | **$10–15 / year** |
| LLM (development usage) | ~$5–20 / month |
| GitHub | $0 |
| Sentry free tier | $0 |
| **Total** | **≈ $10–25 / month** |

### Early launch (~500 active users, ~2 000 sessions/month)

| Item | Cost / month |
|---|---|
| Render Standard (no cold starts) | ~$25 |
| Supabase Pro (8 GB, daily backups) | ~$25 |
| LLM (2 000 sessions) | ~$20–40 |
| Domain (amortised) | ~$1 |
| Email (Resend/Postmark, transactional) | $0–15 |
| Sentry | $0–26 |
| **Total** | **≈ $70–130 / month** |

### App store one-offs

| Item | Cost |
|---|---|
| Apple Developer Program | **$99 / year** |
| Google Play Developer | **$25 once** |
| Company registration (if you incorporate) | Varies by jurisdiction |

**The reassuring conclusion: you can run this properly for under $100/month until you have real traction.** Infrastructure is not your constraint. Your constraint is engineering time.

## 8.3 Domain

**Yes, you need one** — before app-store submission, and before any real user sees the product.

| Consideration | Guidance |
|---|---|
| Cost | `.com` $10–15/yr · `.app` ~$15/yr (HTTPS enforced, which is a small plus) · `.ai` $70–100/yr · `.health` premium |
| Registrar | Cloudflare or Namecheap. **Avoid registrars that upsell aggressively.** Cloudflare sells at wholesale cost. |
| Privacy | WHOIS privacy — usually free, take it |
| Recommendation | Get the `.com` if available. Secondary TLDs are fine but `.com` remains what users type. |
| Subdomains | `app.` for the product · `api.` · `admin.` · `docs.` — plan these now, they are free |

**Register it early.** Domain squatting on a name you have started using publicly is a real and annoying problem.

## 8.4 What you do *not* need yet

| Not needed | Why |
|---|---|
| Kubernetes | One service. Render handles it. |
| CDN (beyond what the platform gives) | Your assets are small; platform CDNs suffice |
| Multi-region | Latency to a single region is fine globally for this workload |
| Dedicated GPU | Embedding inference runs fine on CPU |
| Load balancer configuration | Included in the PaaS |
| Terraform / IaC | Genuinely useful later; premature with two services and one environment |

---

# 9. Legal, licensing, and liability

> This section exists because D-7 (commercial, not open source) turns several things from academic notes into binding constraints.

## 9.1 Dataset licensing — the constraint most likely to bite you

v1 assumed research use. **Commercial use is a different licence question**, and some of the datasets in the Case Factory plan may not permit it.

| Dataset | What to verify **before** building on it |
|---|---|
| **DDXPlus** | Confirm the licence permits commercial derivative works |
| **MedQA** | Confirm commercial use; check whether USMLE-derived content carries additional restriction |
| **PMC-Patients** | ⚠️ **Highest risk.** Derived from PubMed Central Open Access, which is a *mix* of licences — some articles are **CC-BY-NC (non-commercial)**. You must filter per-article, not per-dataset. |
| **Synthea** | Apache-2.0 in general — commercial-friendly. Verify. |
| **MIMIC-III / IV** | ⚠️ PhysioNet credentialed access with a Data Use Agreement that restricts redistribution. **Treat as unusable for a commercial product** unless you have specific written clarity. |

**I am not asserting the current licence of any of these — verify each yourself, and keep a record.** Licences change, and "I read it on a forum" is not a defence.

**Concrete recommendations:**
1. Add a `licence` and `commercial_use_permitted` field to the source-connector configuration
2. Make the Case Factory **refuse** to publish a case derived from a source not marked commercial-safe
3. Store `source_dataset` and `source_record_id` on every generated case (already in the v1 schema) — this is your audit trail if a licence question arises
4. Start with the most permissive source only

## 9.2 Data protection

You will hold identifiable data about medical professionals, potentially across jurisdictions.

| Obligation | What it means practically |
|---|---|
| Privacy policy | Required by both app stores. Must be specific about the LLM: **user-typed questions are sent to a third-party model provider.** Users must be told. |
| Data processing terms with providers | Check whether your LLM provider trains on API data by default. Use the no-training tier. |
| Right to access / delete | Build export and delete now — retrofitting is painful. §v1 3.7 |
| Data residency | If you take EU users and want to keep it simple, host in an EU region from the start |
| Age | Users are professionals — set a minimum age of 18 in the terms and avoid the entire minors regime |

**The LLM disclosure is the one most often missed.** Sending user text to a third party is a processing activity that must be disclosed.

## 9.3 Medical liability positioning

This matters and is cheap to get right.

**What VPSim is:** an educational simulator using synthetic patients, for training clinical reasoning.

**What VPSim is not:** a diagnostic aid, a clinical decision support tool, or a source of medical guidance.

That distinction is what keeps you outside medical-device regulation. Protect it:

| Do | Do not |
|---|---|
| Say "educational simulation" everywhere | Claim to improve real-world diagnostic accuracy without evidence |
| State clearly that cases are synthetic | Let users enter real patient details — actively discourage it |
| Disclaimer at signup and in the app footer | Imply the feedback is clinically authoritative |
| Keep the clinical review record (§4.4) | Publish cases without clinician sign-off |

**Add an input guardrail:** detect and block anything that looks like real patient data being pasted into the question box. Users will try. A short warning plus refusal is enough, and it materially reduces your exposure.

## 9.4 Formalising your clinical reviewers

Your two clinician friends are an asset. Make the arrangement explicit — even informally, in writing:

- What they are agreeing to review, and to what standard (the rubric in §4.4)
- That they are reviewing **educational content**, not providing clinical advice to patients
- Whether they are credited publicly, and how
- That the company, not they, carries responsibility for the product

This protects them as much as you, and it costs one email. If the product becomes commercial and they are contributing regularly, consider a small equity or payment arrangement — unpaid indefinite obligations between friends reliably go wrong.

---

# 10. Research operations under a commercial product

## 10.1 The tension

You now have two goals that pull against each other:

- **Product:** every user should get the best possible experience
- **Research:** to prove the feedback works, some users must receive *less*

You cannot fully satisfy both. But you can handle it well.

## 10.2 What "no-feedback control arm" means — your question

You asked what this means. Plainly:

**The problem.** Your pilot showed history coverage rising from 45.3 % to 79.7 % after feedback. But every participant received feedback. So you cannot distinguish:

- (a) the feedback taught them something, or
- (b) they simply got better at the task the second time — practice, familiarity with the interface, knowing what to expect

Both explanations fit your data equally well. This is why your report honestly states you cannot claim causation.

**The fix.** Split participants into two groups:

| Group | Case 1 | Between | Case 2 |
|---|---|---|---|
| **Treatment** | Full consultation | **Full reasoning feedback** | Full consultation |
| **Control** | Full consultation | **Outcome only** — "your diagnosis was correct/incorrect" | Full consultation |

If both groups improve equally → the improvement was practice, and your feedback adds nothing.
If only treatment improves → **the feedback caused it.** That is a causal claim you could defend.

**The ethical issue.** You are deliberately withholding an educational benefit from the control group. That is precisely what ethics committees exist to weigh.

**The standard resolution: a wait-list design.** The control group receives their full reasoning feedback **immediately after** the study concludes. Nobody is permanently denied anything; the withholding is temporary and disclosed in advance. Ethics committees are familiar with this and it usually resolves the objection.

**Recommendation:** wait-list design, disclosed at consent, feedback released automatically when the study window closes.

## 10.3 Research mode inside a commercial product

Since you are B2C, the research study becomes an **opt-in mode**, not the default experience.

```sql
-- profiles.consent_research already exists in §2.5
CREATE TABLE study_enrolments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    study_id      UUID NOT NULL REFERENCES studies(id),
    arm           TEXT NOT NULL,
    case_order    UUID[] NOT NULL,
    enrolled_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ,
    withdrawn_at  TIMESTAMPTZ,
    consent_version TEXT NOT NULL
);
```

Design rules:
- **Opt-in, never default.** A paying user must not be silently placed in a control arm.
- **Incentivise participation** — free Pro time is appropriate and normal.
- **Withdrawal is honoured** — excluded from analysis, and the wait-list feedback is released immediately.
- **Ordinary users are unaffected.** Everyone not enrolled gets the full product.

This also solves a business problem: it gives you a legitimate, ethical route to keep publishing research from a commercial product, which is genuinely valuable for credibility in medical education.

---

# 11. Revised roadmap

Reordered for a commercial B2C product. Effort in developer-days for two developers plus AI assistance.

## Phase 0 — Foundation (≈ 8 d) — *unchanged from v1*

Package restructure, tests, CI with the detector-validation gate, Docker, config, structured logging, the lexicon disjointness test.

## Phase 1 — Persistence and accounts (≈ 16 d)

| ID | Task | Days |
|---|---|---|
| P1-1 | Supabase project; Postgres schema §2.5 with Alembic | 3 |
| P1-2 | Supabase Auth integration; JWT verification; profile creation | 2 |
| P1-3 | Row-Level Security policies | 1 |
| P1-4 | Event-sourced session state; retire `SESSION_STORE` | 3 |
| P1-5 | Session reconstruction + assessment from events | 2 |
| P1-6 | Backfill the 16 pilot sessions | 1 |
| P1-7 | Move cases from `cases.py` into the database | 2 |
| P1-8 | Move topic lexicon into the database | 1 |
| P1-9 | Account settings, data export, account deletion | 1 |

## Phase 2 — Admin console P0 (≈ 11 d)

| ID | Task | Days |
|---|---|---|
| P2-1 | Case bank browser | 2 |
| P2-2 | **Case editor with overlap validation** | 5 |
| P2-3 | **Playtest with live instrumentation** | 4 |

**This unlocks your clinician reviewers. It is the milestone that matters most.**

## Phase 3 — API and web app (≈ 22 d)

| ID | Task | Days |
|---|---|---|
| P3-1 | JSON API with typed schemas + OpenAPI | 6 |
| P3-2 | Next.js scaffold, auth flow, API client | 4 |
| P3-3 | Consultation screen | 6 |
| P3-4 | Feedback screen | 3 |
| P3-5 | Dashboard, progress, history | 3 |

## Phase 4 — Commercial readiness (≈ 17 d)

| ID | Task | Days |
|---|---|---|
| P4-1 | Stripe subscriptions, webhooks, tier gating | 4 |
| P4-2 | Clinical review queue + rubric | 2 |
| P4-3 | **Leakage monitor + adversarial CI suite** | 3 |
| P4-4 | AI usage & cost dashboard | 2 |
| P4-5 | Examinations / investigations editor | 3 |
| P4-6 | Metabase for analytics | 1 |
| P4-7 | Privacy policy, terms, disclaimers, consent flows | 2 |

## Phase 5 — Measurement upgrade (≈ 11 d) — *v1 Phase 3*

Embeddings, hybrid matcher, calibration corpus, threshold calibration, replay.

## Phase 6 — Mobile (≈ 20 d)

| ID | Task | Days |
|---|---|---|
| P6-1 | React Native + Expo scaffold, shared API client | 4 |
| P6-2 | Consultation + feedback screens | 8 |
| P6-3 | Apple/Google in-app purchase | 4 |
| P6-4 | Push notifications | 2 |
| P6-5 | Store listings, screenshots, review submission | 2 |

## Phase 7 — Case Factory (≈ 22 d) — *v1 Phase 5, plus*

All v1 stages, plus: NLI-based grounding (§5.5), licence gating (§9.1), and **case variant generation** (§4.3).

## Phase 8 — The controlled study

Ethics approval, wait-list control arm, post-study instrument, powered analysis.

---

**Rough total to a launchable commercial web product (Phases 0–4): ≈ 74 developer-days.**
Mobile adds ~20. The Case Factory adds ~22 and should come after launch, not before.

## 11.1 What to cut if you need to launch sooner

An honest minimum viable path:

| Keep | Defer |
|---|---|
| Phase 0, 1 (foundation, accounts) | Case Factory entirely — 5 cases is enough to launch |
| Phase 2 P0 admin (editor + playtest) | Threshold impact preview |
| Phase 3 API + web | Mobile — web-only launch is completely respectable |
| Stripe + legal (P4-1, P4-7) | Embeddings — keywords work today |
| Leakage monitor (P4-3) | Metabase — SQL by hand at first |

**That is roughly 45 days to a paid web product with five cases.** More cases matter more than more features — but content, not engineering, is then your constraint.

---

# 12. Open decisions

| # | Question | Why it matters | My recommendation |
|---|---|---|---|
| E-1 | Free tier limits — how many cases per month? | Determines conversion and LLM cost | 3–5/month. Enough to form a habit, not enough to satisfy |
| E-2 | Pricing? | — | Benchmark against medical education apps in your market; consider regional pricing — a resident in India and one in the US have very different willingness to pay |
| E-3 | Launch geography? | Affects data residency, pricing, and licensing | Start with one market you understand |
| E-4 | Incorporate now or later? | App-store payouts and Stripe need a legal entity | Before taking money, not before building |
| E-5 | Who owns the IP? | You, your friend, and possibly the university | **Resolve this early.** University IP policies sometimes claim work done under supervision. Ask now, in writing. |
| E-6 | Do the clinician reviewers get equity or payment? | Sustainability of the arrangement | Discuss before they have done 50 reviews for free |
| E-7 | Keep publishing research? | Credibility in medical education is largely earned through publication | Yes — §10.3 makes it compatible with a commercial product |
| E-8 | Specialty focus at launch? | A narrow, excellent bank beats a broad, shallow one | Pick one or two specialties and go deep |

---

# 13. Summary

**What changed:** the product moved from institutional B2B to consumer B2C, and gained an app-store target. That reverses the v1 frontend decision and adds accounts, subscriptions, an admin console, and commercial legal obligations.

**The decisions you asked about:**

| Question | Answer |
|---|---|
| Supabase or Neon? | **Supabase, only.** Neon is Postgres-only with excellent branching; Supabase is Postgres plus the auth and storage you need. Using both splits your data across two databases and breaks joins. |
| Build our own auth? | **No.** ~15 days, permanent security liability, App Store complications. Supabase Auth keeps users in *your* Postgres, so there is no lock-in. |
| Multiple databases like that internship? | **No.** One Postgres until ~10⁵ sessions, then a read replica, then a warehouse. Do not build step 4 at step 1. |
| Which LLM? | **Five different jobs, three different models.** Fast/cheap for the patient (test Groq vs GPT-4o-mini vs Haiku on *leakage rate*), strong for feedback, strong + *different* models for Factory extraction and judging. |
| Is an LLM necessary everywhere? | **No — about half the Factory needs none.** Embeddings for dedup and vocabulary mapping, an NLI model for grounding, and your own detectors for the trap self-test. |
| Can we build our own model? | **Yes — fine-tune, don't pretrain.** Start prebuilt, collect 2 000+ pairs via the admin review queue, then fine-tune. That *is* what professionals do. |
| Jinja/HTMX or React/Next? | **Reversed: Next.js for the consumer app**, because a native app needs an API anyway and React Native shares the model. **Keep Jinja/HTMX for the admin console** — different constraints, and it does not block the API work. |
| Which cloud, and cost? | **None yet.** Render/Railway + Supabase, ~$70–130/month at early launch, ~$10–25/month before. Move to GCP Cloud Run only on a measured reason. Apply for startup credits now. |
| Domain? | **Yes, ~$10–15/year.** Register early, Cloudflare or Namecheap, prefer `.com`. |

**The three things I would do first:**

1. **Phase 2 P0 — the case editor and Playtest.** Until your clinicians can review cases without reading Python, your content pipeline is one person wide.
2. **The leakage monitor.** It is the largest threat to the thing that makes your product different, and it is currently invisible.
3. **Verify dataset licences (§9.1)** before writing a line of Case Factory code. Building on a non-commercial corpus is the one mistake here that is genuinely expensive to undo.

---

*End of document. §12 requires decisions before Phase 1.*
