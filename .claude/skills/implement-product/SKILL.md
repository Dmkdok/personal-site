---
name: implement-product
description: >-
  Implements product work from an approved PLAN.md and TASKS.md using
  subagents, design skills, and official docs research. Use only after user
  plan approval (orchestrate-product gate) or when implementing assigned tasks.
---

# Implement Product

## Preconditions

- `docs/PLAN.md` and `docs/TASKS.md` exist
- User approved the plan (`docs/STATUS.md` shows approval) **or** user explicitly assigned implementation tasks

If gate not approved → stop and return to orchestrate-product.

## Method

1. Read the SPEC section for your area, your TASKS milestone, and `docs/CONVENTIONS.md` — not the
   documents in full. Load skill **`coding-discipline`**. Explore code with Serena
   (`get_symbols_overview` → `find_symbol`), not whole-file reads; edit with
   `replace_symbol_body` / `replace_content`.
2. Establish foundations first: tooling, tokens/layout shell, data layer, auth.
3. Deliver a **vertical slice** early (one real user flow end-to-end).
4. Parallelize only independent path ownership.
5. After each milestone: run relevant checks; update `docs/STATUS.md` and tick `docs/TASKS.md`
   **before starting the next one**. A milestone that is finished but unrecorded is indistinguishable
   from one that was never started, and the next session will redo it.

### Milestone boundaries are session boundaries

A closed milestone is the cheapest place to end a session: STATUS describes the tree completely and
nothing in the chat history is load-bearing. Once STATUS is written, TASKS ticked and the work
committed, decide whether to continue — and judge it by **how much window is left, not by how small
the next task looks**. Past roughly half spent, or with a large milestone next, say so in Russian
and offer a fresh window (`/clear`, then «продолжай по docs/STATUS.md»). Below that, keep going:
priming a new session from `docs/` costs a few thousand tokens, so cutting after a two-task
milestone loses more than it saves.

Starting a milestone with a crowded window is the case to avoid — auto-compaction then lands
somewhere inside it, and a summarised half-milestone is the worst artifact this pipeline can
produce. When the estimate is close, cut.

While the milestone runs, keep the bulk out of this window: failure diagnosis, tree-wide searches
and exploratory reading belong to subagents that return a verdict. Run the suite yourself, though —
a green run is ten lines, and a subagent's "green" is a claim, not a result.

### Verification loop

Prefer TDD when SPEC/PLAN requires tests: failing check → implement → pass. For bugs: repro first.
Do not expand scope past the approved task (surgical diffs).

## Quality bar

- Match SPEC acceptance criteria
- For UI: activate `frontend-design`; avoid generic AI visual defaults
- No secrets in repo; use `.env.example`
- Typed boundaries where the stack supports them
- Accessible interactive elements (labels, focus, keyboard)
- Simplicity: no speculative abstractions

## Research

When unsure about APIs, fetch official documentation. Prefer stable patterns from high-quality open-source references over improvisation.

## Subagent handoffs

Use implementer subagent(s) with English prompts listing owned paths and DoD. Parent merges and keeps the tree coherent.

The `implementer` agent is pinned to Sonnet, which is the right default for a task with owned paths
and a written DoD. Raise it per call with the Task/Agent `model` parameter when the task is one
where a subtle mistake survives the tests — migrations, auth, concurrency, anything the reviewer
would have to reason hard about.
