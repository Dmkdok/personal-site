# I4 — The editing mode, and a place of the owner's own

Cut from `main` at `a0d1ecf` (the I3 close, merged and deployed) onto
`iteration/I4-editing-mode`. Source: an owner request, not an audit — the editing mode "works but
is a little ugly", the «Выйти» button in the middle of the screen covers part of the site, and
«Показать правки» feels redundant while still being necessary.

Everything here is visible only to the signed-in owner. A visitor's HTML, CSS payload and rendered
page are unchanged by this iteration, and that is an exit criterion rather than an expectation.

## Baseline

Recorded 2026-08-16 on `iteration/I4-editing-mode`, cut from `main` at `a0d1ecf`. Every command was
run in this session, on this tree.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **277 passed**, exit 0 |
| e2e | `uv run pytest e2e` | **81 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | **1 file would be reformatted**, exit 1 |

**Two inherited findings, neither caused by this iteration.**

1. **`.env` was unparseable and every `docker compose` command failed** — `line 17: key cannot
   contain a space`, which is a failure of the file's *parse*, so `up`, `logs` and `test` were all
   dead, not only the suite. The owner had edited the file and fixed it on being shown the error.
   Nothing in the repository changed. Recorded because a session that hits this again should look
   at `.env` before it looks at Docker.

2. **`ruff format --check` is red on `docs/iterations/I3-operations.md`.** I3's own baseline
   recorded *"clean, 127 files"*; the count is 128 now, and the extra file is the I3 iteration page
   itself — written during I3, after the last format check ran, and never checked. Ruff formats the
   fenced `python` blocks inside Markdown, and the block it wants to rewrite is the illustrative
   excerpt of the T125 dedup race, whose aligned trailing comments (`# ← the row is now in-flight`)
   are the point of the excerpt. **ADR-030** takes `docs/` out of ruff's file discovery rather than
   letting a prose artefact be reformatted by a code formatter.

## Intake

**Source.** Owner request, 2026-08-16, in session. Three parts, all accepted; the owner chose the
combined scope over either smaller cut.

### In

| | Change | Acceptance — what the owner will look at |
|---|---|---|
| **A** | The fixed admin bar at the bottom centre is retired. The mode indicator, the mode switch, a link to the cabinet and «Выйти» move into a menu on the navigation capsule. | Nothing floats over the bottom of the page any more, and the signed-in page is the same length as the visitor's. «Выйти» is reachable in two deliberate actions, not one stray click. |
| **B** | Hover-reveal is replaced by a real mode. **Просмотр** shows no affordance at all, even on hover; **Правка** shows every affordance permanently. | On «Просмотр» the site is indistinguishable from what a visitor sees. On «Правка» every editable thing is marked without hunting for it. The choice survives a reload, as it does today. |
| **C** | A private summary page — the cabinet — listing what needs the owner's attention, and linking back to the pages where the editing happens. | Drafts, unpublished albums and projects, failed photographs with their retry, and photographs with no description are all visible from one screen, in one visit, without opening four sections. |

### Out, with reasons

- **The image version / `sha` line on the cabinet.** The application does not know its own build
  today — nothing in `app/` reads a version, and `static_url` versions assets off their mtime
  (`app/templating.py:71`). Showing it means a build arg through the Dockerfile, an environment
  variable through both compose files and the Portainer stack, and a change to the publish
  workflow. Deferred by **ADR-031**; the cabinet ships with the data the database already holds.
- **Changing the password from the cabinet.** The environment is the source of truth and
  `ensure_admin_user` (`app/security.py:196-201`) rewrites the hash from `ADMIN_PASSWORD` on every
  start, so a password set through the UI would silently revert at the next restart. Recorded in
  **ADR-029**; the cabinet states where the password lives instead of pretending to own it.
- **A full admin panel at `/admin`.** Contradicts the non-goal at `SPEC.md:265` and doubles the
  interface for no gain; in-place editing stays the primary surface. See **ADR-029**.

### Budget

One milestone, four tasks. The three product changes plus the lint chore the baseline turned up.

### Non-negotiables

1. **A visitor's HTML is byte-identical in what matters.** No owner markup, no owner stylesheet, no
   owner script. `F36` and `test_anonymous_html_contains_no_admin_markup` remain the guard.
2. **The published page and the editing page stay the same page.** ADR-001's model is not being
   traded for an editing surface that lives somewhere else.
3. **Every mutating route keeps its `CurrentAdmin`.** The cabinet adds a read, not a new way in;
   `test_authz_sweep.py` is extended, never relaxed, and nothing joins its allow-list.
4. **Keyboard operation and the focus contract survive.** F-002's rule — an action leaves the caret
   on a control — applies to the new menu and the cabinet exactly as to everything else.

## Impact map

| | Change | Touched | SPEC | Tests that cover today's behaviour | Blast radius | What proves no regression |
|---|---|---|---|---|---|---|
| **A** | Bar → capsule menu | `partials/admin_bar.html` (deleted), `partials/nav.html`, `base.html`, `static/css/admin.css:28-34,112-165`, `static/js/nav.js`, `static/js/edits.js` | **F36** reworded, **F61** new | `test_authz_sweep.py:118-122` (marker `admin-bar`), `e2e/test_nav_dropdown.py`, `e2e/test_a11y.py` focus sweep | **Shared primitive** — `base.html` and the one component on every page | Visitor HTML still carries no owner marker; focus sweep still finds every stop; the page no longer reserves bottom clearance |
| **B** | Mode replaces hover | `static/css/admin.css:167-235`, `static/css/components.css:748-788`, `static/css/photo.css:451-529`, `static/js/edits.js`, `base.html` pre-paint script | **F55** reformulated | `e2e/test_show_edits.py` (all 4), `e2e/test_a11y.py:111-122` `REVEAL_ADMIN_AFFORDANCES`, `e2e/test_admin_keyboard.py:30-47` (docstring asserts the `opacity: 0` resting state) | **Wide but shallow** — three selector families, twelve rules, one class | On «Просмотр» the three families are absent from the accessibility tree, not merely transparent; on «Правка» all three are visible without hover |
| **C** | The cabinet at `/me` | `app/routers/` (new module), `app/main.py` (registration), `app/templates/pages/`, `app/i18n/ru/` (new area), `app/routers/seo.py:34-36` (`Disallow`), `e2e/conftest.py:224-239` | **F62** new | `e2e/test_a11y.py` admin sweeps via `admin_surfaces` | **Additive** — one new read-only route, no model change, no migration | Anonymous gets 404; the page appears in both admin sweeps; every existing suite unchanged |
| **D** | `docs/` out of ruff | `pyproject.toml` | — | — | **Isolated** | `ruff format --check .` exits 0 and the I3 excerpt is untouched |

### Ordering

**A lands first and alone.** It rewrites `base.html` and the navigation capsule — the one component
on every page — and both B and C hang off the menu it creates: B's switch lives in it, C's link
lives in it. B and C are independent of each other and may be parallel once A is in. D is isolated
and may land at any point.

### Tests whose expectations change

Each of these asserts today's behaviour correctly. Changing one is a behaviour change, and every
one below is covered by an ADR taken in the same breath as the feature.

| Test | Asserts today | After | ADR |
|---|---|---|---|
| `tests/api/test_authz_sweep.py:121` | the string `admin-bar` never reaches a visitor | the marker becomes the owner menu's class; the *guarantee* is unchanged and the list keeps growing, never shrinking | ADR-027 |
| `e2e/test_show_edits.py` — all four | resting `opacity` is `0`; the toggle reveals; a visitor gets neither control nor script | «Просмотр» has no affordance in the tree; «Правка» has all of them; a visitor still gets neither | ADR-028 |
| `e2e/test_a11y.py:111-122` | the sweeps force `opacity: 1` through the CSSOM to measure hidden controls | the sweeps switch the page into «Правка» — measuring the real state instead of simulating it | ADR-028 |
| `e2e/test_admin_keyboard.py:30-47` | docstring: controls "rest at `opacity: 0` until their tile is hovered" | the helper enters «Правка» first; the focus-by-id mechanism it actually tests is untouched | ADR-028 |

`e2e/conftest.py:224-239` (`admin_surfaces`) is **extended, not changed** — the cabinet is added to
a list that already exists.

`tests/api/test_authz_sweep.py:98-105` is deliberately **left alone**. Its parametrized cases assert
that an admin read answers `303/401/403` — redirect-to-login semantics — and the cabinet answers
`404` by decision (ADR-029). Adding it there would either fail or force `404` into a list that
exists to describe a different guarantee. The cabinet gets its own test asserting exactly `404` for
an anonymous request and `200` for a signed-in one.

## Exit criteria

1. Baseline suites at their baseline counts or better: unit/API ≥ 277, e2e ≥ 81, both exit 0.
2. `ruff check` and `ruff format --check` both exit 0 over the whole tree.
3. Each of A, B and C has at least one check that fails without the change, watched failing first.
4. A visitor's `/`, `/dev`, `/photo`, `/blog` carry no owner markup, no `admin.css` and no
   `edits.js` — the existing guard, still passing, plus the cabinet's own path answering 404.
5. The signed-in page reserves no bottom clearance: `:root:has(body.is-admin)` and
   `body.is-admin .page` no longer set it, and nothing replaces it.
6. Both accessibility sweeps run over the cabinet as well as the four existing signed-in screens,
   in both themes, and pass.
7. The owner performs one full publishing flow — write, illustrate, publish — using only the new
   menu and the new mode, and reports it. No test stands in for this.
