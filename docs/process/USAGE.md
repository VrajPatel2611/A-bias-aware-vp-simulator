# How to use the build prompt

## Before you paste it

Two things in `AI_BUILD_PROMPT.md` are marked `⟨…⟩`. Replace both. If you leave
them, the AI will invent a project and confidently build the wrong thing.

**`THE PROJECT`** — one paragraph. What, for whom, and the one thing it must do.

> *Example:* "A bias-aware virtual patient simulator. Medical trainees interview
> an LLM-driven patient, order tests, submit a diagnosis, and get feedback on how
> they reasoned rather than just whether they were right. Commercial B2C, web
> first, mobile later. It must never let the language model decide a score."

**`MY SITUATION`** — be honest. This changes how much gets explained to you.

> *Example:* "Final-year CS undergraduate, two of us. Comfortable with Python,
> weak on databases and deployment, have not shipped a product before. The
> research is done and published; the platform is not started. Six months."

That second one matters more than people expect. "I don't know databases" is the
difference between an answer you can act on and an answer you have to look up.

---

## The three ways to use it

### 1 · Starting a new project — paste the whole thing

The AI should come back with questions, not documents. **If it starts writing
code, it did not read the brief — say so and paste it again.**

### 2 · Joining a project that already has code

Paste the whole thing. The "IF YOU ARE JOINING A PROJECT THAT ALREADY HAS CODE"
section takes over. Expect it to spend the first session reading and writing
down decisions that were already made, and no code at all. That is correct — a
codebase whose decisions are undocumented gets those decisions re-argued every
few weeks.

### 3 · Mid-session, when it has drifted

You do not need the whole thing. This is usually enough:

```
Stop. Go back to how we agreed to work:

- one task at a time, then stop and wait for me
- tell me the plan before you write code
- run the acceptance criteria and show me the real output
- write the build log, including where you diverged from the spec
- if something failed, say so — do not report success

Which task are you on, and what have you actually verified?
```

---

## The important part: make it write a CLAUDE.md

**A pasted prompt lasts one conversation. A `CLAUDE.md` lasts forever.**

`CLAUDE.md` at your repository root is loaded automatically at the start of
every session, including new ones after your context runs out. Step A4 of the
prompt exists for this reason, and it is the step to insist on.

Once that file exists, you rarely need the big prompt again. New session, cold
model, no memory of you — it reads `CLAUDE.md` and knows the rules.

Keep it under ~150 lines. A context file nobody can skim is a context file that
gets skimmed badly. The single highest-value thing in ours is this table:

| Task | Read |
|---|---|
| Anything at all | This file, then `docs/spec/README.md` |
| Why was X chosen? | `docs/spec/adr/` — check before re-arguing a decision |
| Building a feature | `BUILD_PLAN.md` → find the task → read only its `Spec` refs |
| A screen | `UX_SPEC.md` — that screen's section only |

Forty thousand words of specification, and a session reads five hundred of them.
That is the difference between running out of context halfway through a task and
finishing it.

---

## What good looks like

You will know it is working when:

- it asks questions **before** writing, not after
- it stops after each task instead of running ahead
- it tells you a test failed rather than telling you the code is correct
- its build logs have a **"where we diverged from the spec"** section with things
  actually in it
- you can read a build log three weeks later and understand what happened

You will know it is not working when:

- documents appear without questions being asked first
- it says "this should work" instead of showing you output
- three tasks get done at once and you cannot tell which change broke what
- the spec and the code have quietly disagreed for a week

---

## What this costs

It is slower at the start. Genuinely — a week of documents before a line of
code, and it will feel like nothing is happening.

What you get back: the AI stops making things up, because everything is written
down. You stop re-explaining, because it reads `CLAUDE.md`. And when the context
window runs out mid-project — which it will — the next session picks up from
documents instead of from your memory of a conversation you had a month ago.

The failure mode this avoids is the expensive one: three weeks of code built on
an assumption nobody wrote down and nobody checked.

---

## Adapt it

This is not scripture. It came out of one project and it carries that project's
habits.

- **Small project?** Drop `UX_SPEC` and `API_CONTRACT`. Keep `BUILD_PLAN`, the
  ADRs, and `CLAUDE.md` — those three do most of the work.
- **No frontend?** Drop `UX_SPEC` entirely.
- **Research code, not a product?** Keep the honesty rules and the ADRs, drop
  most of the rest.

The two parts to keep whatever else you cut: **ADRs are never edited**, and
**stop after each task**. Everything else is negotiable.
