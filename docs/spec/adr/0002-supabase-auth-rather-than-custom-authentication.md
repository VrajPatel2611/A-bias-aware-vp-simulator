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
