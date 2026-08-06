# CLAUDE.md

<!-- product-factory:start -->
For greenfield sites/apps, use skill `orchestrate-product`.

- User-facing language: Russian
- Artifacts under `docs/`: English
- No application code until the user approves the plan (`утверждаю`)
- After approval: implement → test → review → handoff
- Prefer subagents: product-planner, architect, implementer, tester, reviewer

## This project

- Resuming work? `docs/STATUS.md` is the handoff — read it first, never summarise a previous chat.
  Trust the tree over the checkboxes in `docs/TASKS.md`, and run the suite before believing "green".
- Code intelligence: **Serena**. Activate by path (names collide on this machine). Explore with
  `get_symbols_overview` → `find_symbol`; edit with `replace_symbol_body` / `replace_content`.
  Whole-file `Read` on source is a last resort.
- Tests: `docker compose run --rm tests` (pytest hangs on the Windows host). Never pipe a test run
  through `tail` — the exit code you get back is the pipe's, and a red suite reads as green.
- Give subagents only their own SPEC/TASKS sections plus `docs/CONVENTIONS.md`, never the full docs.
<!-- product-factory:end -->

