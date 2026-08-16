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

## T131 landed — and five things the plan did not say

Done 2026-08-16. `partials/admin_bar.html` is deleted, `partials/owner_menu.html` is new, and the
capsule carries one owner control: a button with an accent dot, opening a panel with the mode
indicator, the mode switch, and «Выйти». Suites afterwards: **277 unit/API**, **88 e2e** (81 before,
`+6` for the menu, `+1` net in `test_a11y.py`), `ruff check` clean.

1. **The clearance is proved by the document's tail, not by `scrollHeight`.** T131's DoD asks for
   "the same content renders to the same document height signed-in as anonymous". Measured against
   the pre-change tree, that comparison is not available: the owner's `/photo` is 869 → 1516 px
   because of the upload zone and «Новый альбом», and even in «Просмотр» after T132 it still will
   be. What the two deleted rules actually created is the empty space *after* the last element —
   **88 px on every page at both 360 px and 1280 px, against a visitor's 0** — and that is what
   `test_the_owners_document_reserves_no_clearance_a_visitors_does_not` compares, together with the
   root's `scroll-padding-bottom` (`88px` → `auto`). Watched failing first, on the stashed tree:
   *"/ at 1280px ends 88px after its footer"*.
2. **Four more tests carried the marker change than the impact map named.** The map named
   `test_authz_sweep.py:121`; the same substitution was owed by `tests/api/test_auth.py` twice (the
   *positive* marker — a signed-in page must contain it, a logged-out one must not),
   `e2e/conftest.py`'s login fixture, `e2e/test_login.py`, and `e2e/test_a11y.py:656` — all four of
   which located the owner by the bar's `role="region"`. **Nothing was relaxed**: each asserts the
   same guarantee against the marker that replaced it, and the sweep's list grew rather than moved.
3. **The capsule now has two dropdowns, and they hang from the same edge.** Below 768 px the links
   panel spans the capsule and the owner's menu overlaps its right half, so whichever opened second
   would be read over the first. `nav.js` opens them one at a time — and skips any disclosure that
   is not live at the current width, or opening the menu on the desktop would empty the navigation
   row. `test_the_two_dropdowns_are_never_open_at_once` is the check.
4. **The first draft anchored the panel to its own wrapper, and it was wrong by 7 px.**
   `position: relative` on `.owner-menu` makes the containing block the 34 px button, which the
   capsule's padding insets — so `inset-inline-end: 0` landed 7 px short of the edge and 2 px *over*
   the capsule. The panel hangs from `.nav__capsule` instead, which declares `position: relative`
   for exactly this reason (F-011), and lands on the same 1 px border offset the links panel does.
5. **Two traps, both cheap next time.** `translate()`'s catalogue is `@lru_cache`d per process, so
   a **new i18n key needs `docker compose restart web`** in development — until then it renders as
   its own dotted name and every role-based selector misses it, which looks exactly like markup that
   did not render. And `--text-faint` on `--surface-raised` measures **4.21:1** in the dark theme:
   the admin contrast sweep caught the mode line before the commit, and it uses `--text-muted`, as
   the bar's own text did.

## T132 landed — the mode is now load-bearing, and seven more tests said so

Done 2026-08-16. The twelve rules across three stylesheets are one class on the root, and the
`@media (hover: none)` branches are gone with them — touch and pointer behave identically for the
first time. Suites afterwards: **277 unit/API**, **88 e2e**, lint and format clean over 115 files,
all exit 0. Watched failing first on the unchanged tree: *«Locator expected to have count '0';
Actual value: 1»* for the footer's edit button in «Просмотр».

1. **`display`, not `opacity`, is the whole change.** «Просмотр» has to leave the control absent
   from the accessibility tree and out of the tab order, and only `display: none` does all three at
   once — a transparent control is still a tab stop, still under the pointer, and still announced.
   It is also what makes the checks meaningful: `get_by_role(…).to_have_count(0)` cannot pass
   against `opacity: 0`, which is why that assertion is the one that was watched failing.
2. **The a11y sweeps' guard had to be rebuilt, not just repointed.** It used to count the nodes it
   forced visible. In «Просмотр» every node is still in the DOM, so a count of nodes would now pass
   while measuring nothing. It counts **rendered boxes** — `getClientRects().length` — after
   clicking the switch, which is strictly stronger than what it replaced: the sweeps measure the
   real «Правка» state instead of simulating it through the CSSOM.
3. **Seven tests outside the impact map owed the same change**, in three files the map never named:
   `test_home_editing.py` (all three), `test_site_links.py` (all three) and `test_album_upload.py`'s
   launch flow. Every one of them clicks an in-place affordance, and every one of them was passing
   only because `opacity: 0` is clickable. This is the second iteration running in which the map
   undercounted by roughly the same margin — **T131 owed four, T132 owed seven**. Each fix is one
   idempotent `switch_mode(page, "edit")` in the file's existing `_open_the_editor` helper, so the
   mode became part of the flow rather than a detail of the test. Nothing was relaxed.
4. **The switch is two buttons, not one toggle.** A single control labelled «Правка» with
   `aria-pressed` would have been «Показать правки» renamed, which is the redundancy the owner
   objected to. Both halves are rendered, the pressed one *is* the mode indicator F61 asks for, and
   `edits.js` writes both from one read of the root's class so they cannot disagree (F-019). The
   group hangs off the panel's `«Режим»` line through `aria-labelledby`, and it is a real flex box
   rather than `display: contents` — which would have put the group's name at the mercy of a known
   accessibility-tree quirk for a saved rule of three lines.
5. **Editing is now impossible in «Просмотр», and that is the design.** Nothing is merely hidden:
   the owner in «Просмотр» gets a page with no way to change anything, which is what makes it
   "the page a visitor reads". The seven adapted flows are the specification of that, written down.
6. **`auth.admin_mode` and `auth.show_edits` are deleted**, replaced by `auth.mode`,
   `auth.mode_view` and `auth.mode_edit`. The class and the `localStorage` key stay `show-edits` —
   they mean exactly what they did, and renaming them would move the owner's remembered choice for
   nothing.
