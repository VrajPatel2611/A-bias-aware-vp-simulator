# Nidan — Build Specification

Six documents forming the build contract. Written to minimise rework: decisions
settled here rather than mid-implementation.

| Doc | Purpose | Changes when | Status |
|---|---|---|---|
| [PRD.md](PRD.md) | What & why — requirements, acceptance criteria, scope | Scope changes | ✅ Draft |
| [UX_SPEC.md](UX_SPEC.md) | Screen-by-screen specification | Screens change | ✅ Draft |
| [DATA_MODEL.md](DATA_MODEL.md) | Schema bible — every table, column, index | **Any migration, same PR** | ✅ Draft |
| [API_CONTRACT.md](API_CONTRACT.md) | Endpoints + `openapi.yaml` | **Any endpoint change, same PR** | ✅ Draft |
| [BUILD_PLAN.md](BUILD_PLAN.md) | Sequenced tasks with done-definitions | Continuously | ✅ Draft |
| [TECH_SPEC.md](TECH_SPEC.md) | Architecture (consolidates the two design docs) | Architecture changes | ✅ Draft |
| [adr/](adr/) | One decision per file, never edited | New decision | ✅ 15 seeded |
| [TEST_STRATEGY.md](TEST_STRATEGY.md) | What we test, what each kind of test cannot catch, what is missing | A testing task lands | ✅ Living |
| [SECURITY_SPEC.md](SECURITY_SPEC.md) | Threat model, the security model, incident response, pre-launch checklist | A security decision changes | ✅ Draft |

## What was actually built

`docs/spec/` is the contract, written before the code. [`docs/build-log/`](../build-log/) is the record of what was built, one document per
BUILD_PLAN task — including where the work diverged from this specification and why.
Read the build log when you want to know what happened; read the spec when you want
to know what was promised.

## Rules

1. **DATA_MODEL and API_CONTRACT change in the same commit as the code.** If they can drift, they will.
2. **ADRs are never edited** — supersede with a new one.
3. **Decisions marked ⟨DECIDE⟩ in the PRD block downstream docs.** Resolve before finalising the schema.

## Earlier exploratory work

`../design/` holds the original `SYSTEM_DESIGN.md` and `PLATFORM_SPEC.md`.
These will be consolidated into `TECH_SPEC.md`; until then, `PLATFORM_SPEC.md` supersedes `SYSTEM_DESIGN.md` where they conflict.
