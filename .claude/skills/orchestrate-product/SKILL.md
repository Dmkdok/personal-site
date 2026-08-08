---
name: orchestrate-product
description: >-
  End-to-end product delivery orchestrator for websites and software.
  Runs discovery interrogation, product spec, technical plan, gated approval,
  then delegates implementation, testing, and review to subagents.
  Use when the user wants to build a site/app from scratch, ship a polished
  product, run a full delivery pipeline, or invokes /orchestrate-product.
compatibility: Cursor Agent, Claude Code; Plan Mode recommended for Phase 1–3
metadata:
  author: product-factory
  version: "1.1.0"
  lang_user: ru
  lang_internal: en
---

# Orchestrate Product

Coordinate a full delivery pipeline. **Do not invent product decisions** — interrogate the user until the brief is sharp enough that a senior team could build without guessing.

## Resuming an in-flight delivery

If `docs/STATUS.md` exists, this is a resume, not a new start. Do this and nothing else:

1. Read `docs/STATUS.md` — it names the current phase and carries the running log.
2. Read only the `## M<n>` blocks in `docs/TASKS.md` that are still open.
3. **Trust the tree over the checkboxes.** A session that dies mid-milestone leaves finished code
   with unticked tasks. Before working on any task, confirm its state with
   `get_symbols_overview` on the files it owns, and run the suite before believing "tests green".
4. Skip every phase already ticked. Do not re-read `BRIEF.md`, and read `SPEC.md`/`PLAN.md` only
   in the sections the open tasks touch.

Never resume by summarising the previous chat. `docs/STATUS.md` is the handoff artifact; it is
cheaper and more accurate than any conversation summary, and keeping it current is what makes a
session disposable.

## Language policy

- Speak to the user in **Russian**.
- Keep artifacts, checklists, task prompts, and subagent handoffs in **English** (token efficiency).
- Russian only in chat UX and in `docs/BRIEF.ru.md` summary if the user wants a readable brief.

## Hard quality gate (non-negotiable)

**No implementation code until the user explicitly approves the plan.**

Allowed before approval: research, questions, docs under `docs/`, scaffolding folders empty of app code.
Forbidden before approval: app source, dependencies install for the product, UI code, migrations.

If the user says «просто сделай» / «fast» — still run a compressed discovery (minimum question set below), write a short plan, and ask for one-line approval (`утверждаю` / `approve`).

## Delegation policy

- Use the strongest available reasoning model for discovery, product framing, spec, planning, and the approval gate.
- Match the model tier to the phase: strongest for the decisive phases above and for review, Sonnet
  for the executing ones (implement, test), Haiku for read-only fan-out. Details and per-call
  overrides in [references/delegation.md](references/delegation.md#model-tier).
- After approval, decompose the work into small, mostly independent tasks and delegate them to subagents.
- Give each subagent a narrow scope, explicit owned paths, and a clear Definition of Done.
- Keep the parent agent responsible for integration, conflict resolution, testing, and final coherence.
- Avoid assigning overlapping file ownership to multiple subagents in the same milestone.

## Context checkpoints

A delivery does not fit in one context window, and auto-compaction is the worst way to discover
that: it fires at an arbitrary point, keeps an arbitrary half, and the loss stays invisible until an
agent contradicts a decision made an hour earlier. `docs/STATUS.md` exists precisely so a session
can be discarded without losing anything — so discard sessions **deliberately, at points you pick**.

**Milestone boundaries are the only place a cut is free** — STATUS is current, the tree is
committed, nothing in the chat is load-bearing. Cutting elsewhere means writing a handoff for a
half-finished task, so at a boundary the question is *whether* to cut, never *where*. Mid-task is
the exception you take only when the alternative is auto-compaction, which is worse.

Cut at:

- **the GATE**, always, once the plan is approved. Everything the build needs is now in `docs/`; the
  discovery dialogue behind you is dead weight.
- **a milestone boundary, when the window is meaningfully spent** — roughly half gone, or the next
  milestone is large. A fresh window costs a few thousand tokens to prime from `docs/`, so cutting
  after a two-task milestone that barely dented the context is a net loss.
- **any point where context is running low**, boundary or not. Do not open one more task hoping it
  fits: a summarised half-milestone is the worst artifact this pipeline can produce.

At a cut point, in this order: finish or revert the edit in flight → run the suite → update
`docs/STATUS.md` and tick `docs/TASKS.md` → commit → tell the user in Russian that the milestone is
closed and the next one wants a fresh session (`/clear`, then «продолжай по docs/STATUS.md»). The
`pause` skill is this same sequence and can be invoked directly.

Between cuts, keep the parent's window cheap. The parent holds the conversation, the decisions,
subagent summaries, its own STATUS edits, and the suite runs that gate a milestone. Anything else
that prints in bulk — diagnosing a red run, a tree-wide search, exploratory reading, a review pass —
goes to a subagent **even when the parent could do it in a single call**: the parent pays for that
output for the rest of the session, a subagent pays for it once.

The suite itself is deliberately not on that list. A green run is ten lines, and delegating it would
mean closing milestones on a subagent's word — the one mistake this project has already made twice.
See [references/delegation.md](references/delegation.md#what-the-parent-must-not-hold).

## Pipeline

```
0 Intake → 1 Elicit → 2 Spec → 3 Tech plan → GATE → 4 Implement → 5 Test → 6 Review → 7 Handoff
```

Read phase details on demand:

- [references/pipeline.md](references/pipeline.md)
- [references/question-banks.md](references/question-banks.md)
- [references/delegation.md](references/delegation.md)
- Templates in `templates/product-factory/` (installed projects) or `templates/` (inside the product-factory pack root itself)

### Phase 0 — Intake

Classify product type:

| Type | Default path |
|------|----------------|
| Marketing / landing site | Web-first, design-heavy |
| Web app / SaaS | Full stack + auth + tests |
| API / backend | Spec + contract tests |
| Other (CLI, mobile, desktop) | Adapt phases; keep gate |

Create workspace docs (English filenames):

```text
docs/
  BRIEF.md
  SPEC.md
  PLAN.md
  TASKS.md
  DECISIONS.md
  STATUS.md
```

Copy structure from `templates/product-factory/` when present, else `templates/` (pack root case).

### Phase 1 — Elicit (read skill `elicit-requirements`)

Grill until shared understanding: batches of 5–8, **recommended answers** on each question, skip
what the repo already answers. Prefer structured choices when possible.

Stop eliciting only when [Definition of Ready](references/pipeline.md#definition-of-ready) is met.

Use the strongest available reasoning model for this phase (Plan Mode in Cursor when available).

### Phase 2 — Spec (`draft-product-spec`)

Produce `docs/SPEC.md`: problem, users, scope, non-goals, UX flows, acceptance criteria, risks.

### Phase 3 — Tech plan (`draft-tech-plan`)

Produce `docs/PLAN.md` + `docs/TASKS.md`: stack, architecture, file map, milestones, parallel workstreams, test strategy, Definition of Done.

Web research is allowed for current docs/libraries (mid-2026+). Prefer boring, proven defaults unless the user constrained otherwise.

### GATE — User approval

Present in Russian:

1. Short summary of what will be built
2. Stack and major trade-offs
3. Out of scope
4. Risks / assumptions
5. Ask: **«Утверждаете план? Напишите: утверждаю»**

On approval, write `docs/STATUS.md` → `phase: implement`, commit the docs, and **cut the session**
before Phase 4 — see [Context checkpoints](#context-checkpoints). Implementation starts in a fresh
window reading `docs/`, never in the window that ran the interview.
On change requests, update docs and re-ask. Never skip the gate.

### Phase 4 — Implement (`implement-product` + `coding-discipline` + subagents)

Delegate via Task / subagents per [references/delegation.md](references/delegation.md).

Parent agent:

- Keeps `docs/STATUS.md` updated **as each milestone lands, not at the end** — an unrecorded
  milestone is lost work when the session runs out of context
- Merges results; resolves conflicts
- Verifies each milestone before starting the next by **running the suite itself** with compact
  output — a subagent's "green" is a claim, not a result, and this project has been burned by the
  difference twice. What it delegates is the *diagnosis* of a red run, then re-runs to confirm
- Treats each milestone boundary as a session cut point: STATUS, tick, commit, offer a fresh window
- Does not dump entire codebase into chat — summarize (or activate `concise-mode` if the user asked)
- Reads code through Serena's symbol tools, not whole files (see
  [references/delegation.md](references/delegation.md#reading-code-serena))

For UI work, apply `frontend-design`. Prefer distinctive, brief-specific design; avoid generic AI aesthetics.

### Phase 5 — Test (`test-product`)

Run automated checks + Playwright / browser verification. Fix failures before claiming done.

### Phase 6 — Review (`review-product` + `web-design-guidelines` + `secure-review`)

Independent verification (verifier mindset). Critical functional **or** security issues must be fixed.

The reviewer writes `docs/REVIEW.md` and returns a verdict plus counts, not the review. **Read that
file before closing the phase** — Mediums never travel in a summary, and an unread Medium is one
that never becomes a task.

### Phase 7 — Handoff

Russian summary for the user:

- What was built and how to run it
- Test status
- Known limitations
- Suggested next iterations

English `docs/HANDOFF.md` **and** an up-to-date `docs/STATUS.md` for continuity across
tools/sessions. A later agent must be able to resume from STATUS alone without the prior chat.

## Progress checklist

Copy into `docs/STATUS.md` and tick:

```text
- [ ] Phase 0 intake
- [ ] Phase 1 elicit (DoR met)
- [ ] Phase 2 SPEC.md
- [ ] Phase 3 PLAN.md + TASKS.md
- [ ] GATE user approved
- [ ] Phase 4 implementation
- [ ] Phase 5 tests green
- [ ] Phase 6 review clean (or accepted waivers)
- [ ] Phase 7 handoff
```

## Anti-patterns

- Coding from a vague one-liner without interrogation
- Skipping tests to “finish faster”
- Parallel agents editing the same files without ownership
- Inventing brand/voice when the user already stated them
- Closing with “should work” without running verification
- Drive-by refactors and speculative architecture (violates `coding-discipline`)
- Auto-running `ui-quality-audit` on every delivery (optional skill — only on explicit request)
- Claiming tests green from TASKS checkboxes or chat memory without running the suite
- Dumping all of `docs/` into every subagent prompt
- Letting auto-compaction decide where the session ends instead of cutting at a milestone
- Running a debug loop or a tree-wide search in the parent's window when a subagent could return
  the verdict (the suite run itself stays with the parent — see delegation.md)
