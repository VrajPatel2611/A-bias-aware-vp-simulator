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
