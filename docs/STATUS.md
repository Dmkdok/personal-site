# Status

phase: review
approved: true
approved_at: 2026-08-04

## Resume here

**M0–M7 are complete. Everything that can be verified here is green.**

| Gate | Command | Result |
|---|---|---|
| Unit + API | `docker compose run --rm tests` | 137 passed, exit 0 |
| End-to-end | `uv run pytest e2e` | 27 passed, exit 0 |
| Six launch flows | `uv run pytest e2e -m launch_flow` | 6 passed, exit 0 |
| Lint | `uv run ruff check .` | clean |
| Format | `uv run ruff format --check .` | clean |

`docs/HANDOFF.md` is the document to read next — running, editing, backup/restore, VPS deployment,
and the known gaps. This file is the session log.

**The two things nobody has done yet**, both on the launch checklist in `SPEC.md`:

1. **Rehearse a restore.** `make backup` works; replaying its artefacts has never been tried.
   Procedure is in `HANDOFF.md` §5. This is T073's DoD and the highest-value next action.
2. **Deploy the production stack.** `docker-compose.prod.yml` and the `Caddyfile` are written and
   validate, but have never been brought up on a real server (T074).

Then Phase 6: an independent review pass (`reviewer` / `review-product`) before calling it done.

**Git state — read this before committing.** Work sits on branch
`session/2026-08-06-m3-fixes-and-e2e`, not on `main`, and there is no remote. As of this writing
the branch holds five commits off `4bfc65b`; the last of them and part of the docs were written by
an out-of-band `/pause` run that fired while a subagent was still working, so its snapshot of the
e2e results was captured mid-run and has been corrected here. Merging into `main` is the owner's
call; nothing depends on it.

## Checklist
- [x] Phase 0 intake
- [x] Phase 1 elicit (DoR met)
- [x] Phase 2 SPEC.md
- [x] Phase 3 PLAN.md + TASKS.md
- [x] GATE user approved
- [x] Phase 4 implementation (M0–M7 done)
- [x] Phase 5 tests green (unit/API 137/137; e2e 27/27; lint and format clean)
- [ ] Phase 6 review clean (or accepted waivers)
- [x] Phase 7 handoff (`docs/HANDOFF.md`; two launch-checklist items remain open by name)

## Test report

**Unit + API** — last run 2026-08-06 end of session, `docker compose run --rm tests`, exit 0.

- **137 tests: 137 passed, 0 failed.** Re-run after the day's edits, not carried over from an
  earlier note.
- Green: auth, authorisation sweep, search, SEO, projects, blog, markdown, photo pipeline units
  and the full photo API surface.

**End-to-end** — last run 2026-08-07 on the host, `uv run pytest e2e` (Playwright, Chromium).

- **27 tests: 27 passed, 0 failed.** The six launch flows of T070 — login, album upload, article
  publish, lightbox by keyboard, theme persistence, search — are the `launch_flow` marker and pass
  as their own gate (6 passed).
- Machine-readable a11y and performance evidence is in `docs/qa/`.

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
- 2026-08-06 — T071 was left red at the end of the paused session with three e2e failures recorded. Two of the three turned out to be defects in the tester's own new test code, not in the site, and were fixed by the tester after that snapshot was taken; only the contrast finding was real. Superseded by the 2026-08-07 entries below.
- 2026-08-06 — Session paused mid-flight by an out-of-band `/pause` run **while the tester subagent was still working**. It branched the previously-uncommitted tree to `session/2026-08-06-m3-fixes-and-e2e` (`76e3f60` M3's defect fixes, `66c8f41` the e2e suite, `c425fae` the QA evidence and docs, plus two more) and wrote a handoff from a mid-run snapshot of the e2e suite. Corrected in "Resume here" above rather than left to mislead the next session. No remote exists; nothing was pushed.
- **2026-08-07 — T071 (accessibility) closed. Both halves of the DoD met.** Contrast had 13 light-theme samples under 4.5:1 with two roots, both in `tokens.css`: white `--on-accent` on the amber accent measured 3.58:1 (active nav link, primary button, cover flag), and `--text-faint` #767f8b measured 3.55:1 on `--bg` (eyebrow labels, field labels, stack chips). Fixed as `--on-accent: #14171a` (5.03:1, brand amber untouched — and the choice the dark theme had already made) and `--text-faint: #646c77` (4.65:1, still lighter than `--text-muted` at 5.95:1, so the hierarchy holds). Dark theme measured clean at 0/75 throughout. Keyboard: login, navigation, search, lightbox, theme toggle and a full admin publish flow all complete without a pointer.
- **2026-08-07 — ADR-010: touch targets held to WCAG 2.2 AA 2.5.8 (24 px) rather than SPEC F12's 44 px.** 54 controls at 360 px sit between the two bars; none breach the standard. Owner chose the waiver over enlarging the navigation capsule and footer. F12's wording amended to match.
- 2026-08-07 — **An e2e flake was found and fixed that the tester's own three runs had not surfaced**, caught by re-running the suite independently rather than taking the report at face value: `test_an_article_can_be_written_and_published_without_a_mouse` failed roughly one run in three, ending at `/blog?title=…` — the browser's native GET. htmx makes the swapped «Новая статья» form visible and focused before it finishes settling, and only a settled form has its submit intercepted; synthetic keystrokes fit inside that ~20 ms window, a human cannot. The test now waits for htmx's `htmx:afterSettle` instead of racing it; five consecutive runs green. Worth remembering as a pattern: **any e2e step that types into htmx-swapped markup and submits immediately has this race.**
- 2026-08-07 — `uv run ruff format --check .` is clean now too. The hand-grouped `ALLOWED_TAGS` set in `services/markdown.py` is fenced with `# fmt: off` so the formatter cannot explode it into 30 one-per-line entries; the other seven files were reformatted normally.
- **2026-08-07 — T075 done. `docs/HANDOFF.md` written**: stack, local run and the two environment traps, configuration, content editing for all three sections, backup *and* restore, VPS deployment with the production overlay, verification status, six known gaps, and a code map. The launch checklist in `SPEC.md` is now ticked except for two items named explicitly there — the owner's own unaided pass through the publishing flows, and a rehearsed restore.
