---
name: test-product
description: >-
  Verifies product quality with automated tests and browser/Playwright checks.
  Use after implementation milestones, before claiming delivery complete, or
  when debugging UI behavior. Adapted from Anthropic webapp-testing patterns.
---

# Test Product

## Goal

Prove the product works against SPEC acceptance criteria. Skeptical by default.

## Preferred toolkit

1. Project test runner (vitest/jest/pytest/etc.) — unit/integration
2. **Playwright** for e2e (Chromium, headless)
3. In Cursor: browser MCP tools for exploratory QA / screenshots when useful

Patterns inspired by [anthropics/skills webapp-testing](https://github.com/anthropics/skills) (see `vendor/anthropics/webapp-testing`). Full upstream skill may include helper scripts; this pack works without them.

## Workflow

```text
1. Read docs/SPEC.md acceptance criteria → checklist
2. Ensure app boots (note URL/port)
3. Run unit/integration tests
4. Write/run Playwright flows for critical paths
5. Capture failures with screenshots + console logs
6. Fix or file blockers; re-run until green or waived in DECISIONS.md
```

## Playwright baseline

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:3000")
    page.wait_for_load_state("networkidle")
    page.screenshot(path="docs/qa/home.png", full_page=True)
    browser.close()
```

Or TypeScript `@playwright/test` if the repo is JS/TS-first — match the stack.

## Rules

- Always wait for network idle / explicit selectors on dynamic apps
- Prefer role/text selectors over brittle CSS chains
- Do not claim "done" if critical acceptance criteria lack evidence
- Record results in `docs/STATUS.md` under `## Test report`

## Reading the run correctly

- **Never pipe a test command through `head`/`tail`.** The shell reports the *last* command's exit
  code, so a red suite behind `| tail -60` returns 0 and reads as green. Redirect to a file and
  check the runner's own exit code, or let the runner print its summary.
- Start compact (`pytest -q --tb=no`, `vitest --reporter=dot`); pull a full traceback only for the
  case you are diagnosing. A full-traceback run of a broadly failing suite can cost tens of
  thousands of tokens and tells you the same thing as the summary.
- When many tests fail at once, look for one shared cause before reading each failure. Process-wide
  state torn down by the first test — a closed pool, a shut-down executor, a cached singleton — is
  the usual culprit, and fixing it turns the whole block green at once.
- Screenshots are expensive. One per visual claim, scoped to the element, one theme unless the
  behaviour is theme-specific.

## Reading code under test

Use Serena rather than opening source files whole: `get_symbols_overview` for a module's shape,
`find_symbol include_body=true` for the function under test, `find_referencing_symbols` to find
everything that touches a suspect symbol.
