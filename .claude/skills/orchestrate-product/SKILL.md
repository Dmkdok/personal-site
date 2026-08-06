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
  version: "1.0.0"
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
- After approval, decompose the work into small, mostly independent tasks and delegate them to subagents.
- Give each subagent a narrow scope, explicit owned paths, and a clear Definition of Done.
- Keep the parent agent responsible for integration, conflict resolution, testing, and final coherence.
- Avoid assigning overlapping file ownership to multiple subagents in the same milestone.

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

Ask in **batches of 5–8 questions**, not one giant dump. Prefer structured choices when possible.

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

On approval, write `docs/STATUS.md` → `phase: implement` and proceed.
On change requests, update docs and re-ask. Never skip the gate.

### Phase 4 — Implement (`implement-product` + subagents)

Delegate via Task / subagents per [references/delegation.md](references/delegation.md).

Parent agent:

- Keeps `docs/STATUS.md` updated **as each milestone lands, not at the end** — an unrecorded
  milestone is lost work when the session runs out of context
- Merges results; resolves conflicts
- Does not dump entire codebase into chat — summarize
- Reads code through Serena's symbol tools, not whole files (see
  [references/delegation.md](references/delegation.md#reading-code-serena))

For UI work, apply `frontend-design`. Prefer distinctive, brief-specific design; avoid generic AI aesthetics.

### Phase 5 — Test (`test-product`)

Run automated checks + Playwright / browser verification. Fix failures before claiming done.

### Phase 6 — Review (`review-product` + `web-design-guidelines`)

Independent verification (verifier mindset). Critical issues must be fixed.

### Phase 7 — Handoff

Russian summary for the user:

- What was built and how to run it
- Test status
- Known limitations
- Suggested next iterations

English `docs/HANDOFF.md` for continuity across tools/sessions.

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
