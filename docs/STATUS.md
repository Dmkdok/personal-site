# Status

phase: review
approved: true
approved_at: 2026-08-04

## Resume here

**Branch `session/2026-08-06-m3-fixes-and-e2e`, tree clean, nothing running.** No remote; merging
into `main` is the owner's call.

M0–M8 are complete. All six defects the owner reported are fixed and verified in a browser, and
the one launch-checklist item M7 left open (a rehearsed restore) is closed. Every gate is green —
see the Test report below.

**Phase 6 — the independent review — has still not been run.** That is the only thing between here
and calling this done, and it is the next action.

### Next three actions, in order

1. **Run Phase 6.** `review-product` / the `reviewer` subagent against `docs/SPEC.md`: correctness,
   security, UX, completeness. Put the UI through `web-design-guidelines`. Findings get fixed or
   waived with an ADR. Only then tick Phase 6 in the checklist below.
2. **Fix the in-article picture CLS.** Measured this session and left deliberately unfixed because
   the session ended: an article page with two pictures scores **CLS 0.119** against the project's
   0.02 budget, on a 400 kB/s cold load at 1440×900. The pictures are `loading="lazy"` and carry no
   `width`/`height`, so nothing reserves their height and the text below them jumps. The renderer
   in `app/services/markdown.py` already stats each rendition in `_srcset`; reading the dimensions
   there and emitting them as attributes is the fix. Re-measure, do not assume.
3. **Deploy the production stack** (T074). `docker-compose.prod.yml` and the `Caddyfile` validate
   but have never been brought up on a real server. Note `MEDIA_HOST_DIR` is new — point it outside
   the checkout there.

**Waiting on the owner:** nothing blocking. Two judgement calls are theirs if they want them
revisited — the `{.wide}` / `{.full}` vocabulary (ADR-011) and keeping media on a bind mount rather
than a named volume (ADR-012).

## Checklist
- [x] Phase 0 intake
- [x] Phase 1 elicit (DoR met)
- [x] Phase 2 SPEC.md
- [x] Phase 3 PLAN.md + TASKS.md
- [x] GATE user approved
- [x] Phase 4 implementation (M0–M8 done)
- [x] Phase 5 tests green (unit/API 193/193; e2e 36/36; lint and format clean)
- [ ] Phase 6 review clean (or accepted waivers)
- [x] Phase 7 handoff (`docs/HANDOFF.md`; one launch-checklist item remains open — the production deploy)

## Test report

All five gates run at the end of the 2026-08-07 session, on the tree as committed.

| Gate | Command | Result |
|---|---|---|
| Unit + API | `docker compose run --rm tests` | **193 passed**, exit 0 |
| End-to-end | `uv run pytest e2e` | **36 passed**, exit 0 |
| Six launch flows | `uv run pytest e2e -m launch_flow` | **6 passed**, exit 0 |
| Lint | `uv run ruff check .` | clean, exit 0 |
| Format | `uv run ruff format --check .` | clean, exit 0 |

No failing tests. The suite grew from 137 to 193 unit/API tests and from 27 to 36 e2e over this
session — the picture vocabulary, the media layout, the editable links, the home-page editing flow
and the lightbox's size assertions all arrived with their own coverage.

`-q` is set twice, so a passing run prints dots and no summary line. **Read the exit code.** Never
pipe a test run through `tail` or `grep`: you get the pipe's status and a red suite reads as green.

**Not covered by any gate, and known bad:** in-article picture CLS, 0.119 against a 0.02 budget.
Measured by hand (see "Resume here", action 2). `docs/qa/perf-50.json` covers the album grid only.

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
- **2026-08-07 (session 2) — M8: the six defects the owner hit while using the finished site. Every one was reproduced before it was touched, and two of the three hypotheses that came with the report were wrong about the mechanism.** That is the lesson worth carrying: read-the-code hypotheses were right that something was broken and wrong about why.
- 2026-08-07 — **T085, the dead «Править» button.** The block key is `home.intro`, the partial built `id="content-home.intro"`, and htmx read the target `#content-home.intro` as «#content-home with class intro». Nothing matched, so htmx logged `htmx:targetError` and never sent a request — a button that looked broken but was in fact aimed at nothing. **Any key that becomes part of a DOM id must have its dots normalised out**, in the id *and* in every `hx-target` that names it. F35 had no e2e coverage at all until now.
- 2026-08-07 — **T080, the lightbox. The hypothesis (grid min-content blowing out the width) was wrong; the width was fine.** `.lightbox__figure` was sized by its content, so `max-block-size: 100%` on the image resolved against nothing and the picture kept its full aspect height: a 4000×6000 portrait measured 1328×1992 inside a 900 px viewport, top at −566, which is why only the middle was ever visible. The figure is now a grid with a definite height. **Small test photographs hid this for the whole project** — the defect needs a 6000 px source, which is what `e2e/test_lightbox.py` now uploads.
- 2026-08-07 — Two more defects fell out of that one measurement, neither reported: `sizes` was a flat `100vw`, up to three times the truth for a portrait; and the neighbour preloader fetched `data-src`, always the largest rendition, after which the browser is entitled to reuse that cached candidate rather than fetch the right one. A 360 px phone was downloading 2560 px files. **When a browser picks a surprisingly large candidate, suspect the cache before the descriptors.**
- 2026-08-07 — T082, the blog index. `--measure` is `68ch`, and `ch` resolves against *the element's own font*: put on a wrapper it inherits the larger body font, and the excerpt ran to 115 characters a line. Moved onto the text at `52ch` it measures 72. **A measure cap belongs on the text, never on its container.**
- 2026-08-07 — **T083, media layout.** Files were filed by year, so one album's photographs sat among every other album's. Now `<originals|derived>/<kind>/<id>-<slug>/`. The originals-vs-derived split deliberately stays *above* the grouping: it is what makes the single `/media` mount over `derived/` keep an original unreachable by URL structurally rather than by rule (ADR-012). The migration has to move three things together — files, path columns, and the `/media/…` URLs inside article bodies in **both** `body_md` and `body_html`; miss the last and published articles lose their pictures silently.
- 2026-08-07 — T081. **The in-article image feature was never broken.** All three insertion routes — toolbar, drop, paste — worked end to end when driven in a browser. What was missing was any way to discover it or to size the result. Before rewriting a feature the owner says they do not use, drive it first.
- 2026-08-07 — **T086 closed the hole in T073.** T073 was ticked in M7 while half its DoD — "documented *and* tried once" — was not met, and `SPEC.md` recorded it as open at the same time. `make restore-check` now replays a dump into a scratch database and checks every restored path against the media archive; that last check is the point, because a dump that replays cleanly still leaves a broken site if the two artefacts came from different runs.
- 2026-08-07 — Traps confirmed again this session, for whoever is next: **the i18n catalogue is cached at import**, so editing `app/i18n/ru/*.json` needs `docker compose restart web` even though `--reload` is on. **The fixed admin bar swallows taps on the footer at ≤640 px** — anything added down there needs clearance. The `tests` container drops and recreates its **own** database, so it cannot hurt the dev data; the e2e suite, which drives the live site, writes into the dev database and its fixtures clean up after themselves.
