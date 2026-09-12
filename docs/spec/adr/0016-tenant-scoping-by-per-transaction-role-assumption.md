# ADR-0016 · Tenant scoping by per-transaction role assumption

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-12 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

Migration 016 enabled Row-Level Security and wrote the policies `DATA_MODEL` §10.1 specifies. T-010 proved they are correctly written, using a purpose-built non-superuser role.

None of that constrains the application, because PostgreSQL exempts two kinds of caller from every policy: **superusers and the table owner**. An application connecting as either gets RLS silently disabled while `pg_policies` still lists all six policies and every schema test still passes. This is not hypothetical: the direct connection string Supabase issues authenticates as `postgres`, a superuser, and is the obvious thing to paste into `DATABASE_URL`.

So the application needs a role that is neither, and the anonymous-trial path needs the opposite — `DATA_MODEL` §10.1 accepts that a trial visitor has no `auth.uid()` and must be served through a connection that bypasses RLS with an explicit `anonymous_id` filter instead.

## Decision

**Two `NOLOGIN` roles created by migration 020, assumed per transaction rather than per connection.**

| Role | RLS | Assumed for |
|---|---|---|
| `nidan_app` | applies | every authenticated request |
| `nidan_service` | bypassed | the anonymous-trial path, jobs, the case editor |

Every transaction opens with two statements, in `infra/db/repositories/base.py`:

```sql
SET LOCAL ROLE nidan_app;
SELECT set_config('request.jwt.claim.sub', :user_id, true);
```

Both are transaction-scoped. The `LOCAL` forms are not a stylistic preference: plain `SET` persists for the life of the *connection*, and a pooled connection is handed to whichever request asks next.

The role is chosen by an `Actor` — three distinct types, never one type with an optional `user_id` — and no connection can be obtained without one.

## Alternatives considered

| Option | Why rejected |
|---|---|
| **A dedicated login user per role** | Two pools, two secrets to rotate, and no protection at all when `DATABASE_URL` names a superuser — which on Supabase is the default. Assuming a role demotes even a superuser connection for the duration of the statement. |
| **Reuse Supabase's `authenticated` / `service_role`** | Managed by GoTrue and PostgREST, carrying grants we do not control, and absent from a plain PostgreSQL. Owning the definition is what makes local and production the same thing. |
| **Application-level scoping only (`WHERE user_id = ?` everywhere)** | One forgotten clause is a breach. It is also untestable as a property: you can only check the queries someone remembered to write. |
| **RLS only, with the app as owner** | The policies never fire. The failure mode is invisible and green. |
| **Extend RLS to cover anonymous sessions via a second session variable** | Genuinely attractive — the safety net would stay on everywhere. Rejected for now because it diverges from `DATA_MODEL` §10.1 and adds a policy whose correctness is load-bearing before T-015 has defined what a trial actually is. Revisit at T-015. |

## Consequences

+ A forgotten `WHERE user_id = ...` returns nothing rather than another learner's consultation
+ Correct even when the connection's credentials are a superuser's
+ One connection pool serves both roles
+ The bypass is confined to one 100-line module, and `ServiceActor` requires a written reason, so every use of it is greppable and self-explaining
− `SET LOCAL ROLE` costs a round trip per transaction (negligible beside the statements that follow)
− The anonymous path is protected by an application filter alone; its four methods and its separate test file are the compensating controls
− Migration 020 grants role membership to `CURRENT_USER` so a local stack works unconfigured; a production deployment should grant it to the application's own login user instead
