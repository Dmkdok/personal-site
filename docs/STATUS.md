# Status

phase: implement
approved: true
approved_at: 2026-08-04
paused_at: 2026-08-06 (end of session — see "Resume here")

## Resume here

Working tree is **clean**, on branch `session/2026-08-06-m3-fixes-and-e2e` (three commits ahead of
`main`, not merged and not pushed — there is no remote). Merging into `main` is an open decision for
the owner; nothing depends on it.

Where the work stands: M0–M6 done, `tests/` green at 137/137. M7 is in progress — **T070 and T072
are met and ticked; T071 (accessibility) is the only red thing in the project**, with three failing
e2e tests and evidence already collected under `docs/qa/`.

Next three actions, in order:

1. **Fix T071.** Three failures, each with its report:
   - AA contrast in light theme — 13 samples under 4.5:1 (`docs/qa/contrast-light.json`). Dark
     theme is clean. Worst offender is `a.nav__link` on the active capsule (white on `#C0762A`,
     3.58:1); the rest is the `.label` grey `#767F8B` on `#EEF0F3` (3.55:1) and the primary button.
     A darker accent and a darker `--text-muted` in the light palette fix most of them at once —
     both live in `app/static/css/tokens.css`, and the change must be re-checked in dark theme.
   - Focus order — every one of the 69 focus stops *does* have a visible indicator
     (`docs/qa/focus-sweep.json` lists none without), so the assertion that fails is the ordering
     half of `test_every_focus_stop_is_visible_and_ordered`. Read the test before touching CSS.
   - Touch targets — 54 controls under the 44 px that SPEC F12 asks for
     (`docs/qa/target-size-360px.json`), though **zero** fail WCAG 2.5.8 (24 px). Mostly the 34 px
     icon buttons (menu, theme) and 36 px footer links. This is a spec-vs-reality call for the
     owner: raise the controls, or relax F12 to the WCAG floor and record the waiver.
2. Then T073/T074 verification (both written 2026-08-04, neither deployed) and T075 handoff docs.
3. `uv run ruff format --check .` is still red on 7 files — see the last note of 2026-08-06.

To re-verify before believing any of this: `docker compose run --rm tests` for the unit/API suite,
and the host-side `uv run pytest e2e/` (Playwright, needs `make up`; the `tests` container does not
mount `e2e/`).

## Checklist
- [x] Phase 0 intake
- [x] Phase 1 elicit (DoR met)
- [x] Phase 2 SPEC.md
- [x] Phase 3 PLAN.md + TASKS.md
- [x] GATE user approved
- [x] Phase 4 implementation (M0–M6 done; M7 hardening in progress)
- [ ] Phase 5 tests green (unit/API 137/137; e2e 23/26 — T071 a11y red)
- [ ] Phase 6 review clean (or accepted waivers)
- [ ] Phase 7 handoff

## Test report

**Unit + API** — last run 2026-08-06 end of session, `docker compose run --rm tests`, exit 0.

- **137 tests: 137 passed, 0 failed.** Re-run after the day's edits, not carried over from an
  earlier note.
- Green: auth, authorisation sweep, search, SEO, projects, blog, markdown, photo pipeline units
  and the full photo API surface.

**End-to-end** — last run 2026-08-06 23:54 on the host, `pytest e2e/` (Playwright, Chromium).

- **26 tests: 23 passed, 3 failed.** All three failures are in `e2e/test_a11y.py`:
  `test_text_meets_aa_contrast_in_both_themes[chromium-light]`,
  `test_every_focus_stop_is_visible_and_ordered[chromium]`,
  `test_interactive_targets_are_at_least_44px_on_a_phone[chromium]`.
- The six launch flows of T070 — login, album upload, article publish, lightbox by keyboard,
  theme persistence, search — are **all green**.
- Machine-readable evidence for the three failures is in `docs/qa/`; see "Resume here".

**Lint** — `uv run ruff check .` green. `uv run ruff format --check .` red on 7 files (not part of
T001's DoD, but `make lint` runs it).

## Notes
- 2026-08-04 — Intake: personal multi-section portfolio site (Главная / Разработка / Фото / Блог) for Dmitriy Bogdanov. Classified as marketing/portfolio site with an authenticated authoring surface.
- 2026-08-04 — Elicitation complete in three batches. Definition of Ready met; no blocking open questions. Three assumptions accepted by the owner (draft copy, design direction, originals stored but not downloadable).
- 2026-08-04 — SPEC.md written: 37 functional requirements (F1–F37), 12 edge cases, 8 risks/assumptions, launch checklist.
- 2026-08-04 — PLAN.md written. Stack: FastAPI 0.141 + Jinja2 + htmx 2.0 + PostgreSQL 18 + Pillow 12.3, hand-written CSS, no Node build. Library versions verified against current releases (Aug 2026).
- 2026-08-04 — TASKS.md written: 8 milestones, T001–T075. M3/M4/M5 designed for three parallel implementer subagents with disjoint file ownership; schema, migrations and shared partials deliberately serialised into M2 first.
- 2026-08-04 — DECISIONS.md: ADR-001..007 proposed.
- **2026-08-04 — GATE PASSED. Owner approved with «Утверждаю». ADR-001..007 move to accepted. Implementation started.**
- 2026-08-04 — M0 done (T001–T004). `/healthz` returns ok; Alembic runs on startup; Postgres healthy.
- **2026-08-04 — INCIDENT.** The Compose project was initially named `portfolio`, colliding with a pre-existing project of the same name on this machine (`C:\Users\dmkdok\AI\Portfolio\compose.prod.yaml`). The first `up` recreated that project's `web` and `db` containers, which were then removed. No volumes were deleted — `portfolio_media` and `portfolio_postgres_data` are intact, and `portfolio-nginx-1` kept running. Fixed by renaming this project to `dmkdok-portfolio`. Owner informed; restoring the other stack is their call (`docker compose -f "C:\Users\dmkdok\AI\Portfolio\compose.prod.yaml" up -d`).
- 2026-08-04 — Fixed: Postgres 18+ requires the volume mounted at `/var/lib/postgresql`, not `/var/lib/postgresql/data`; the older path makes the container refuse to start.
- 2026-08-04 — M1 done (T010–T015). Tokens with `light-dark()`, self-hosted Onest + JetBrains Mono (~103 KB, no external requests), navigation capsule, home page, error pages. Design reviewed by screenshot in both themes; dark background lightened to #1C1F23 after review because #16181B read as black.
- 2026-08-04 — M2 done (T020–T027). Full schema + single migration; Russian FTS verified (`эльбрусе` matches «Эльбрус»); Argon2id auth, session-token rotation on logout, middleware-level CSRF, IP throttling; admin bar and the in-place editing pattern. 12 tests green.
- 2026-08-04 — Bugs found and fixed during M2: (a) `nh3` rejects `rel` in the attribute allow-list when `link_rel` is set; (b) Alembic's `fileConfig` was resetting the root logger on startup, silencing every application log including tracebacks; (c) HTTP header values are latin-1, so Russian toast text is percent-encoded; (d) since the FastAPI 0.141 router refactor `include_router` leaves an `_IncludedRouter` wrapper in `app.routes`, so the authorisation sweep needed a recursive walk — a flat scan passed while checking nothing.
- 2026-08-04 — Tests run in a container (`docker compose run --rm tests`): Starlette's TestClient hangs on the Windows host before collection. This is also the environment the VPS uses.
- 2026-08-04 — Shared infrastructure added before parallel work: `services/images.py`, `services/markdown.py`, `services/slugs.py`, `/media` mount, per-area i18n files under `app/i18n/ru/`, and `docs/CONVENTIONS.md`. Ownership of `services/markdown.py` and `services/images.py` moved from the feature modules to the parent, because all three modules need them.
- 2026-08-04 — M3/M4/M5 dispatched to three implementer subagents in parallel.
- 2026-08-04 — M6 done by the parent while the modules were being built (T060–T062): Postgres FTS across posts/projects/albums with grouped results, drafts and unpublished items filtered out for anonymous visitors, `robots.txt`, `sitemap.xml`, per-page canonical/OG tags. Russian stemming covered by test.
- 2026-08-04 — T073 backup script and T074 production overlay (Caddy, automatic HTTPS, no published ports, Secure cookies) written. Not deployed.
- 2026-08-04 — 17 tests green at this point (auth, authorisation sweep, search, SEO).
- **2026-08-06 — Session resumed after the previous chat ran out of context. Audited the tree against `TASKS.md`, which had gone stale: M3 and M4 were left unticked although both subagents had in fact written their modules.**
- 2026-08-06 — M4 (blog) verified done and ticked: T040–T045. `app/routers/blog.py`, `app/services/markdown.py`, 8 templates under `app/templates/blog/`, `editor.js` (11.5 KB), `blog.css` (9 KB), `tests/api/test_blog.py` (19 KB) and `tests/unit/test_markdown.py` — all green.
- 2026-08-06 — M3 (photo) is code-complete but stays unticked: `photos.py` (866 lines), `images.py`, 9 templates, `lightbox.js`, `uploader.js`, `photo.css` (16 KB) and both test files exist, yet 17 tests fail. See the Test report above for the root cause. **This is the first thing to fix on resume.**
- 2026-08-06 — Removed the duplicate skill packs: `.agents/` and `.cursor/` were byte-identical mirrors of `.claude/`, and `.cursor/rules/product-factory.mdc` duplicated the CLAUDE.md preamble. `.claude/` is now the single source.
- 2026-08-06 — Serena (LSP code intelligence) activated for this project; `.serena/` holds the config and cache. Skills and agent definitions updated to read code through Serena's symbol tools and to load only their own SPEC/TASKS sections, to stop future sessions from burning context on whole-file reads.
- **2026-08-06 — M3 (photo) green. T030–T036 ticked; suite is 137/137, exit 0.** The 17 failures were four defects, not one. The recorded blocker was real but only accounted for 12 of them: `app/background.py` held its `ThreadPoolExecutor` at module level, so the first `TestClient` teardown shut it down for the whole process. The pool is now created on first use and `shutdown()` drops it, which also makes shutdown idempotent; production still builds one pool and stops it once. The other three: (a) `_form_response` in `photos.py` built its context as `{"form": form, **context}`, and `_index_context`/`_album_context` each carry their own `form` key defaulting to `None`, so the later spread won and every rejected save re-rendered an empty form; (b) two of the Jinja traps already listed in `CONVENTIONS.md` were live in the photo templates — `loop.first`/`loop.last` read inside an `{% include %}` in `_album_card.html`, and `form.values.title` (the dict-method shadow) in `_album_form.html`; (c) `tests/conftest.py` `admin_client` logged in and returned **the same** `TestClient` as `client`, so the three tests taking both fixtures checked the visitor rules against an admin session — `test_a_visitor_only_sees_ready_photos` passed a `/photo/admin/` leak it was written to catch. `admin_client` is now an independent client.
- 2026-08-06 — Two further test-harness corrections that the above uncovered: the `db` fixture now uses `expire_on_commit=True` (with the app default, `False`, a fixture's own `commit()` left its objects unexpired and `db.rollback()` is a pass-through when no transaction is open, so `db.get(...)` returned stale rows and two assertions were testing nothing); and the deletion tests ask the database directly via a `row_gone` helper, because `Session.get` on a deleted instance it still holds raises `ObjectDeletedError` rather than returning `None`.
- 2026-08-06 — The lightbox close label was «Закрыть просмотр»; `test_no_tags_reading_time_or_counters_anywhere` bans the substring «просмотр» to keep view counters out. Renamed to «Закрыть галерею» rather than weakening the sweep.
- 2026-08-06 — **`uv run ruff check .` had been red (38 errors) since before this session, so T001's DoD («`ruff check` succeeds on a clean clone») was not actually met. Now green.** 30 findings were RUF001/002/003 «ambiguous unicode» on Cyrillic literals — unavoidable noise in a Russian-language project, and they were burying the rest, so they are now in `ignore` with the reason written down. The other eight were fixed properly: unsorted imports in `services/slugs.py`, three lines over 100 chars, one `SIM102` in the CSRF middleware, and two `UP042` — `PhotoStatus` and `PostStatus` moved from `(str, enum.Enum)` to `enum.StrEnum`. That last one changes what `str(status)` returns, so it was checked first: every consumer goes through `.value` (templates included) or compares by identity, and the suite is 137/137 after the change.
- 2026-08-06 — Still open: `uv run ruff format --check .` is red on 7 files. It is not part of T001's DoD but `make lint` runs it. One of them, `services/markdown.py`, holds a hand-grouped `ALLOWED_TAGS` set that the formatter would explode into 30 one-per-line entries; that block wants `# fmt: off` rather than a blind reformat.
- **2026-08-06 — M7 started. T070 done and ticked: `e2e/` now holds 26 Playwright tests over the six launch flows plus a11y and performance, driven from the host against `make up` (the `tests` container mounts only `tests/`, so e2e cannot run inside it).** Shared fixtures and page helpers are in `e2e/conftest.py` and `e2e/helpers.py`; the flow tests are green.
- 2026-08-06 — T072 done and ticked. `docs/qa/perf-50.json`: on a 50-photo album at 1440×900, CLS 0.00023 (budget 0.02), LCP 168 ms (budget 2500), heaviest thumbnail 96.3 KB (budget 120). All 50 images carry `loading="lazy"`, intrinsic dimensions, `srcset` and alt text; 39 load on first paint and the rest on scroll. The single recorded shift is the nav capsule, three orders of magnitude under budget.
- **2026-08-06 — T071 (accessibility) is RED and is the only red thing left in the project.** Three e2e failures, each with a JSON report under `docs/qa/`: 13 light-theme contrast samples below 4.5:1 (dark theme clean), the ordering half of the focus sweep (indicator visibility itself is clean — 0 of 69 stops lack one), and 54 controls below SPEC F12's 44 px, none of which actually breach WCAG 2.5.8's 24 px. The last one needs an owner decision rather than a fix: raise the controls or relax F12 to the WCAG floor with a recorded waiver. Details and the suggested token-level fix are in "Resume here" at the top of this file.
- **2026-08-06 — Session paused for the night. The tree had been entirely uncommitted (one commit in the whole repo); it is now committed on branch `session/2026-08-06-m3-fixes-and-e2e` as three commits off `4bfc65b`: `76e3f60` M3's four defect fixes, `66c8f41` the e2e suite, `c425fae` the QA evidence and these docs.** Not merged into `main`, not pushed — the repo has no remote. Merge or rebase is the owner's call on resume.
