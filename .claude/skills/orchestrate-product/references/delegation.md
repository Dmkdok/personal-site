# Delegation map

Use Cursor Task tool / Claude subagents. Each subagent gets a **self-contained English prompt**: goal, constraints from `docs/`, file ownership, Definition of Done, what to return.

## Subagents (project)

| Agent file | When | Model |
|------------|------|-------|
| `product-planner` | Phases 1–2 | inherit — run these phases on the strongest model available |
| `architect` | Phase 3 | inherit — same |
| `implementer` | Phase 4 | `sonnet` (pinned) |
| `tester` | Phase 5 | `sonnet` (pinned) |
| `reviewer` | Phase 6 | `opus` (pinned); tool-restricted (no Edit/Write/NotebookEdit) |

Fallback if custom agents missing: builtin `Explore` (read-only research) and `general-purpose` agent types + skills.

## Model tier

Two different costs are in play. Everything else on this page cuts the **number** of tokens; this
section cuts the **price** of each one. Both are worth doing, and neither substitutes for the other.

The rule: pay for reasoning where a wrong answer is expensive and hard to notice; use a cheaper tier
where the task is bounded and something else checks the result.

- **Decisive work — keep it strong.** Product framing, spec, architecture, and review. A weak model
  here does not fail loudly; it produces a plausible plan with a hole in it, or returns "looks good"
  on code that isn't. Review especially: the whole point of the phase is catching what the
  implementer missed, so it is the last place to save money.
- **Executing work — Sonnet.** An implementer with owned paths and a written DoD, or a tester
  running an existing suite. The scope is narrow, and tests and the reviewer catch the misses.
- **Fan-out reading — Haiku.** Sweeping the tree for "where is X" via `Explore`.

The pinned tiers above are defaults, not a ceiling. Override per call with the Task/Agent `model`
parameter (`sonnet`, `opus`, `haiku`), which beats the agent's frontmatter — send the same
`implementer` to Sonnet for a routine task and to Opus for a migration or a concurrency bug.

Note what the pins buy over `model: inherit`: `inherit` couples every subagent to whatever the
parent happens to be running, so a session started on a cheap model silently gets a cheap reviewer.
Pinning decides the tier per role instead of per session.

## What the parent must not hold

The parent's window is the one that cannot be replaced: it carries the conversation with the user
and every decision made in it. A subagent's window is disposable — it is discarded the moment the
agent returns. So the question for any noisy operation is not "can the parent do this?" but "who
should be paying for the output afterwards?"

Delegate on output volume, not on difficulty. Anything that reliably prints more than ~100 lines
goes to a subagent even when the parent could do it in one tool call:

| Operation | Why it must not land in the parent |
|-----------|-------------------------------------|
| Diagnosing a failure | The read-fix-rerun loop deposits a traceback per round |
| Tree-wide search | Dozens of hits, of which two mattered |
| Reading a module to learn its shape | Exploratory reading is open-ended by nature |
| A review pass | Reviewer output is long by design |
| Screenshots | The single most expensive thing that can enter a context window |

What the parent keeps: the user conversation, product decisions, subagent summaries, its own
`docs/STATUS.md` and `docs/TASKS.md` edits, targeted reads that settle a specific integration
question, and **running the suite at gate points** — see below. If the parent finds itself three
rounds into a debug loop, that loop was delegated wrong: stop, hand the whole loop to one agent,
take the verdict.

### The suite is the exception — the parent still runs it

Delegating the *run* would save nothing and cost the thing the whole pipeline rests on. A green run
with compact output is about ten lines; it is a red one that is expensive. And this project has
twice been burned by believing a report instead of the runner: an e2e flake that the tester's own
three consecutive runs never surfaced, and a milestone recorded from a subagent's self-report while
the tree said otherwise. **A subagent's "tests green" is a claim, not a result.**

So: the parent runs the suite itself before closing a milestone, before a gate, and at pause —
compact output, never piped. If it comes back red, the parent does not read the tracebacks; it hands
the whole diagnosis to one agent and waits for a verdict, then **re-runs the suite itself** to
confirm the fix. Two cheap runs by the parent beat one expensive one plus trust.

## Debug loops belong to one agent

Never ping-pong a failure through the parent: run in the subagent, read the failure in the parent,
send a fix back down. Every round deposits another traceback upstairs and re-explains the same
context downstairs.

Hand the entire loop to a single agent instead: *reproduce → diagnose → fix → re-run → repeat, up to
4 rounds; if it is still red, stop and return the diagnosis rather than another attempt.* The bound
matters — an unbounded agent will keep trying variations long past the point where the parent should
have made a call. What comes back is the final state: fixed and green, or red with a named root
cause and what was ruled out.

## Context budget for a subagent

A subagent that reads `SPEC.md` + `PLAN.md` + `TASKS.md` in full burns ~15k tokens before writing a
line, and most of it belongs to somebody else's module. Both documents are sectioned by area
(`### Admin — photography`, `## M3 — Photography`), so hand each agent **its own sections only**.

Name the exact sections in the prompt. The agent reads:

- its own `SPEC.md` requirement section + `## Non-functional` (always)
- its own `## M<n>` block in `TASKS.md`
- `docs/CONVENTIONS.md` (always — this is what keeps parallel modules coherent)
- from `PLAN.md`: only `## Architecture` and `## Repository map` unless the task is architectural

Everything else is available on request, not by default.

## Prompt template for Task

```text
You are the <role> for this product delivery.

Read exactly these, nothing more:
- docs/SPEC.md → sections "<your area>" and "Non-functional"
- docs/TASKS.md → section "<your milestone>"
- docs/CONVENTIONS.md (whole file)
- docs/PLAN.md → sections "Architecture" and "Repository map"
Ask before reading anything else from docs/.

Owned paths: <globs>
Do not modify: <globs>

Goal: <one paragraph>
Constraints: <stack, a11y, etc.>
DoD:
- [ ] ...
Return, in 250 words or fewer:
  Status / Files / Verify / Risks / DoD
Never paste file contents, diffs or logs. Anything longer than that
goes into a file and you return the path.
```

## Good delegation heuristics

- Keep the parent agent responsible for the big decisions and the final merge.
- Delegate tasks that are well-bounded and can be validated independently.
- Prefer small handoffs over giant implementation prompts.
- If a task needs product judgment, keep it with the planning/parent agent rather than handing it to a subagent.
- Never paste the entire `docs/` tree into a subagent prompt.
- Parent keeps `docs/STATUS.md` current; on resume, STATUS is the source of truth for phase — not chat memory.

## Skills to load by phase

| Phase | Skills |
|-------|--------|
| 1 | `elicit-requirements` |
| 2 | `draft-product-spec` |
| 3 | `draft-tech-plan` |
| 4 | `implement-product`, `coding-discipline`, `frontend-design` |
| 5 | `test-product` |
| 6 | `review-product`, `web-design-guidelines`, `secure-review` |
| any | `concise-mode` when user asks кратко / экономь токены |
| optional | `ui-quality-audit` — **only** on explicit UI/UX deep-audit request; not default Phase 6 |

## Reading code (Serena)

This project has Serena, an LSP-backed symbol index. Reading source files whole is what exhausted a
previous session's context — the tree is ~450 KB, about 115k tokens if read end to end.

Give every code-touching agent this protocol:

- **Locate** with `get_symbols_overview <file>` — names only, ~200 tokens for an 866-line module.
- **Read** only the symbol you need: `find_symbol <name> include_body=true`.
- **Trace** with `find_referencing_symbols` rather than grepping and opening every hit.
- **Edit** with `replace_symbol_body` / `insert_before_symbol` / `insert_after_symbol` /
  `replace_content`. Use `rename_symbol` and `safe_delete_symbol` for renames and deletions —
  they are reference-aware, and re-verifying them afterwards is wasted work.
- `Read` on a whole source file is a last resort. `Glob`/`Grep` are fine for finding *where*
  something is; the follow-up read goes through Serena.

Serena must be activated by path (`activate_project "<abs path>"`), not by name — project names
collide across a machine.

## Reporting back

"Summaries only" without a number produces two-thousand-token summaries. The budget is **250 words,
in this shape:**

```text
Status: done | blocked | red
Files: <paths, one line>
Verify: <the exact command or URL>
Risks: <one line each, or "none">
DoD: <which boxes are met, which are not>
```

Nothing else crosses the boundary. No file contents, no diffs, no test logs, no reasoning about how
the agent got there. Detail that genuinely needs to survive gets **written to a file** — evidence to
`docs/qa/`, a root cause worth an hour to the next session to `docs/STATUS.md` `## Notes` — and the
report names the path. A path costs five tokens; the content it points at costs thousands, and the
parent usually never needs to read it.

For a failing suite: counts, the name of the shortest failing case, and the root cause in one
sentence. Not the traceback.

## Screenshots

Images are among the most expensive things in a context window. Take one when a visual decision
depends on it, not to confirm each iteration. Prefer a single element screenshot over a full page,
and one representative theme over both unless the change is theme-specific.

## Research

When docs/APIs are unclear, use web search/fetch for official docs. Prefer primary sources (framework docs, GitHub releases) over random blogs.
