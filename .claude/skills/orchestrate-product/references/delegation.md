# Delegation map

Use Cursor Task tool / Claude subagents. Each subagent gets a **self-contained English prompt**: goal, constraints from `docs/`, file ownership, Definition of Done, what to return.

## Subagents (project)

| Agent file | When | Model hint |
|------------|------|------------|
| `product-planner` | Phases 1–2 | strongest reasoning available / inherit high |
| `architect` | Phase 3 | strongest reasoning |
| `implementer` | Phase 4 | inherit |
| `tester` | Phase 5 | inherit |
| `reviewer` | Phase 6 | inherit; tool-restricted (no Edit/Write/NotebookEdit) |

Fallback if custom agents missing: builtin `Explore` (read-only research) and `general-purpose` agent types + skills.

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
Return: files changed, how to verify, open risks. Summaries only —
never paste file contents back.
```

## Good delegation heuristics

- Keep the parent agent responsible for the big decisions and the final merge.
- Delegate tasks that are well-bounded and can be validated independently.
- Prefer small handoffs over giant implementation prompts.
- If a task needs product judgment, keep it with the planning/parent agent rather than handing it to a subagent.

## Skills to load by phase

| Phase | Skills |
|-------|--------|
| 1 | `elicit-requirements` |
| 2 | `draft-product-spec` |
| 3 | `draft-tech-plan` |
| 4 | `implement-product`, `frontend-design` |
| 5 | `test-product` |
| 6 | `review-product`, `web-design-guidelines` |

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

Subagents return **summaries**: files changed, how to verify, open risks. Never paste file
contents, full diffs or full test logs into the return value — the parent pays for all of it.
For a failing suite, return the counts plus the shortest failing case, not the whole traceback.

## Screenshots

Images are among the most expensive things in a context window. Take one when a visual decision
depends on it, not to confirm each iteration. Prefer a single element screenshot over a full page,
and one representative theme over both unless the change is theme-specific.

## Research

When docs/APIs are unclear, use web search/fetch for official docs. Prefer primary sources (framework docs, GitHub releases) over random blogs.
