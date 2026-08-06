# Status

phase: implement
approved: true
approved_at: 2026-08-04

## Checklist
- [x] Phase 0 intake
- [x] Phase 1 elicit (DoR met)
- [x] Phase 2 SPEC.md
- [x] Phase 3 PLAN.md + TASKS.md
- [x] GATE user approved
- [ ] Phase 4 implementation
- [ ] Phase 5 tests green
- [ ] Phase 6 review clean (or accepted waivers)
- [ ] Phase 7 handoff

## Test report

Last run: 2026-08-06, `docker compose run --rm tests` (pytest exit 1).

- **137 tests: 120 passed, 17 failed.** All 17 failures are in `tests/api/test_photo.py`.
- Green: auth, authorisation sweep, search, SEO, projects, blog, markdown, photo pipeline units.
- Red: the photo module's API tests — see the blocker note under M3 in `TASKS.md`.
- Not written yet: `e2e/` is empty (T070).

**Blocker.** `app/background.py` defines `_executor` as a module-level `ThreadPoolExecutor`;
`app/main.py` `lifespan` (line 66) calls `background.shutdown()` on exit. Under pytest the first
`TestClient` teardown shuts the executor down permanently, so every subsequent test that uploads a
photo raises `RuntimeError: cannot schedule new futures after shutdown`. The first 52 tests pass,
then `test_photo.py` fails en masse. This is a test-lifecycle defect, not a product defect — the
application itself creates the executor once per process and shuts it down once.
`test_albums_can_be_reordered` fails with a jinja2 template error and may be a genuine second bug.

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
