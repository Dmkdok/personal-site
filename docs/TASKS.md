# Tasks

Derived from `docs/PLAN.md`. Format: `id — title — paths — deps — DoD`.
Agent column marks who executes after the approval gate: **parent** (shared/integration) or a named implementer subagent.

## M0 — Scaffold *(serial, parent)*

- [x] **T001** — repo skeleton, `pyproject.toml` + uv lock, Ruff config — paths: `/`, `pyproject.toml`, `.gitignore`, `.dockerignore` — deps: none — DoD: `uv sync` and `ruff check` succeed on a clean clone.
- [x] **T002** — Dockerfile, `docker-compose.yml` (web + Postgres 18), `.env.example`, `Makefile` — paths: `Dockerfile`, `docker-compose.yml`, `.env.example`, `Makefile` — deps: T001 — DoD: `make up` starts both services, Postgres healthcheck passes, media bind mount `./data/media` present inside the container.
- [x] **T003** — app factory, `pydantic-settings` config, DB engine + session dependency, `/healthz` — paths: `app/main.py`, `app/config.py`, `app/db.py` — deps: T002 — DoD: `GET /healthz` returns 200 and confirms a live DB connection.
- [x] **T004** — Alembic wiring, autogenerate against the models' metadata, migrations run on startup — paths: `alembic.ini`, `migrations/env.py` — deps: T003 — DoD: `make migrate` is idempotent on an empty and on a migrated database.

## M1 — Design system + public shell *(serial, parent + `frontend-design`)*

- [x] **T010** — design tokens and both themes; pre-paint theme script with CSP nonce — paths: `app/static/css/tokens.css`, `app/static/js/theme.js`, `app/templates/base.html` — deps: T003 — DoD: toggling light/dark changes the whole site from one token file, choice survives reload, no flash of the wrong theme, dark background is dark grey not black.
- [x] **T011** — self-hosted variable fonts (Onest, JetBrains Mono) with Cyrillic subsets, OFL licence files, fluid `clamp()` type scale — paths: `app/static/fonts/**`, `app/static/css/base.css` — deps: T010 — DoD: no external font request in the network panel; Cyrillic renders at every weight used; licence files present.
- [x] **T012** — rounded pill navigation containing section links, search field and theme toggle; responsive collapse below 768 px — paths: `app/templates/partials/nav.html`, `app/static/css/components.css` — deps: T010, T011 — DoD: F1 acceptance met, including `aria-current` on the active section and full keyboard operation.
- [x] **T013** — base layout, footer, skip-to-content link, semantic landmarks, CSS `@layer` structure — paths: `app/templates/base.html`, `app/templates/partials/footer.html`, `app/static/css/layout.css` — deps: T012 — DoD: one landmark of each type per page; skip link works by keyboard.
- [x] **T014** — home page: intro, contact/social links, three section entries; draft Russian copy; UI strings via `i18n/ru.json` — paths: `app/templates/pages/home.html`, `app/routers/pages.py`, `app/i18n/ru.json` — deps: T013 — DoD: F2 met; no aggregated feed present; no user-visible string hardcoded in a template.
- [x] **T015** — 404/500 pages, shared card and empty-state partials — paths: `app/templates/pages/404.html`, `app/templates/pages/500.html`, `app/templates/partials/{card,empty_state}.html` — deps: T013 — DoD: F14 met; the card partial exposes no tag, reading-time or counter slot.

## M2 — Auth, schema, admin core *(serial, parent)*

- [x] **T020** — SQLAlchemy models for every table in `SPEC.md` — paths: `app/models/**` — deps: T004 — DoD: models import cleanly; `lang` present on content tables; media paths are relative.
- [x] **T021** — single Alembic migration creating the whole schema, including generated `search_vector` columns with the Russian configuration and GIN indexes — paths: `migrations/versions/**` — deps: T020 — DoD: upgrade and downgrade both run on an empty database; a manual insert is immediately findable via `websearch_to_tsquery`.
- [x] **T022** — security core: Argon2id hashing, session middleware, `session_token` rotation on logout, CSRF token issue/verify, IP rate limiting — paths: `app/security.py`, `app/deps.py` — deps: T020 — DoD: F16, F17, F19, F20 met by unit tests.
- [x] **T023** — `/login` page and `/logout`; login not linked from public navigation — paths: `app/routers/auth.py`, `app/templates/pages/login.html` — deps: T022 — DoD: correct credentials sign in and redirect back; wrong username and wrong password give an identical message.
- [x] **T024** — admin seeding on startup from env; hard failure when `SECRET_KEY`/`ADMIN_*` are absent — paths: `app/main.py` — deps: T022 — DoD: F15 met; the plaintext password appears in no log line and in no table.
- [x] **T025** — admin bar and the reusable inline-edit pattern (htmx swap between view and edit partials), applied to `site_content` on the home page — paths: `app/templates/partials/admin_bar.html`, `app/routers/pages.py`, `app/templates/partials/editable.html` — deps: T023, T014 — DoD: F35, F36, F37 met; anonymous HTML contains no admin markup.
- [x] **T026** — register the photo/blog/dev routers as stubs; background task pool and the startup recovery sweep — paths: `app/main.py`, `app/background.py` — deps: T003 — DoD: the three module agents never need to edit `main.py`; a task submitted to the pool runs and is logged.
- [x] **T027** — authorisation route sweep test — paths: `tests/api/test_authz_sweep.py`, `tests/conftest.py` — deps: T023 — DoD: the test enumerates every registered non-`GET` route except `/login` and asserts 401/403 without a session; it fails if an unprotected route is ever added.

## M3 — Photography *(parallel, agent `photo`)*

Owns `app/routers/photos.py`, `app/services/images.py`, `app/templates/photo/**`, `app/static/js/{lightbox,uploader}.js`, `app/static/css/photo.css`, `tests/**/test_photo*`. Must not touch `main.py`, `models/**`, `migrations/**`, `tokens.css` or shared partials.

> **State (2026-08-06): done, 137/137 green.** The 17 failures were four separate
> defects, not the single one the previous session recorded:
> (a) `app/background.py` held `_executor` as a module-level `ThreadPoolExecutor`, so the
> first `TestClient` teardown ran `background.shutdown()` and killed it process-wide — the
> pool is now built lazily and `shutdown()` drops it, so a later `submit()` gets a fresh one;
> (b) `_form_response` spread the surrounding context *after* `{"form": form}`, and that
> context carries its own empty `form` key, so every rejected save re-rendered a `None` form;
> (c) `photo/_album_card.html` read `loop.first` / `loop.last` inside an `{% include %}`, and
> `photo/_album_form.html` read `form.values.title` — both traps are already written down in
> `docs/CONVENTIONS.md`;
> (d) `admin_client` in `tests/conftest.py` returned the *same* client as `client` after
> logging it in, so the three tests that take both fixtures were asserting the visitor rules
> against an admin session. It is now a separate client with its own cookie jar.

- [x] **T030** — album CRUD inline on `/photo` and on the album page, slug generation, publish toggle — deps: T025 — DoD: F21, F26 met; unpublished albums 404 for anonymous visitors.
- [x] **T031** — upload endpoint: extension + MIME + magic-byte + decode validation, 25 MB cap, 50 files per batch, UUID filenames, path containment assertion — deps: T026 — DoD: F24 met; each rejection case covered by a test; nothing is ever written outside `MEDIA_ROOT`.
- [x] **T032** — Pillow pipeline: 640/1600/2560 px WebP derivatives, aspect ratio preserved, EXIF orientation applied, no upscaling, original kept untouched — deps: T031 — DoD: F23 met by unit tests over portrait, landscape, small and rotated inputs.
- [x] **T033** — background processing with per-photo status, plus the startup sweep that re-processes or fails stuck photos — deps: T032, T026 — DoD: F22, F27 met; a batch of 50 does not block the request; a mid-processing restart leaves no photo stuck in `processing`.
- [x] **T034** — album grid with `srcset`, lazy loading and intrinsic dimensions; admin drag-reorder, cover selection, alt text editing, deletion that also removes files — deps: T033 — DoD: F4, F25 met; deleting a photo leaves no orphan file on the volume.
- [x] **T035** — lightbox: dimmed and softened backdrop, arrow/keyboard navigation, `Esc` and backdrop close, focus trap, focus restored to the originating thumbnail, body scroll lock, `prefers-reduced-motion` respected — deps: T034 — DoD: F5 met, verified by keyboard only.
- [x] **T036** — photo module tests — deps: T035 — DoD: pipeline unit tests, upload API tests and authorisation tests all green.

## M4 — Blog *(parallel, agent `blog`)*

Owns `app/routers/blog.py`, `app/services/markdown.py`, `app/templates/blog/**`, `app/static/js/editor.js`, `app/static/css/blog.css`, `tests/**/test_blog*`. Same prohibitions as M3.

- [x] **T040** — Markdown service: `markdown-it-py` with raw HTML disabled, then `nh3` allow-list sanitising — deps: T020 — DoD: F31 met; `<script>`, `onerror=` and `javascript:` URLs are stripped while ordinary formatting survives.
- [x] **T041** — editor screen: Markdown pane, live preview rendered through the same service via debounced htmx, formatting toolbar, draft autosave — deps: T025, T040 — DoD: F28 met; preview updates within ~500 ms of a typing pause and matches the published rendering exactly.
- [x] **T042** — in-editor image upload (drop or button) reusing the shared upload endpoint, inserting Markdown at the cursor — deps: T041, T031 — DoD: F29 met.
- [x] **T043** — draft/publish lifecycle, `published_at`, un-publishing, drafts 404 for anonymous visitors and marked «черновик» for the admin — deps: T041 — DoD: F30 met.
- [x] **T044** — blog index and article page: cover, title, excerpt, date only; 65–75 character measure; responsive images; wide media scrolls inside its own container — deps: T043 — DoD: F8, F9 met; no tag, reading-time or counter anywhere.
- [x] **T045** — blog module tests — deps: T044 — DoD: sanitisation, lifecycle and authorisation tests green.

## M5 — Development *(parallel, agent `dev`)*

Owns `app/routers/projects.py`, `app/templates/dev/**`, `app/static/css/dev.css`, `tests/**/test_project*`. Same prohibitions as M3.

- [x] **T050** — project card CRUD inline on `/dev`: title, summary, optional Markdown body, repo URL, demo URL, tech stack, optional cover — deps: T025, T040 — DoD: F33 met; created, edited and deleted without leaving `/dev`.
- [x] **T051** — drag ordering and publish toggle — deps: T050 — DoD: F34 met; order and visibility persist for visitors.
- [x] **T052** — `/dev` list and optional `/dev/{slug}` detail page; external links carry `target="_blank" rel="noopener noreferrer"` — deps: T050 — DoD: F6, F7 met; projects without a long description link straight to the repository.
- [x] **T053** — project module tests — deps: T052 — DoD: CRUD, ordering and authorisation tests green.

## M6 — Search + SEO *(serial, parent)*

- [x] **T060** — search service over `search_vector` for posts, projects and albums; grouped results page; short-query and no-result states — paths: `app/services/search.py`, `app/routers/search.py`, `app/templates/pages/search.html` — deps: T036, T045, T053 — DoD: F10 met; drafts and unpublished items never appear for anonymous visitors; a 1-character or whitespace query produces guidance, not an error.
- [x] **T061** — `sitemap.xml`, `robots.txt`, per-page title/description/canonical/OG tags — paths: `app/routers/seo.py`, `app/templates/base.html` — deps: T060 — DoD: F13 met; the sitemap lists exactly the published pages.
- [x] **T062** — search and SEO tests — paths: `tests/api/test_search.py`, `tests/api/test_seo.py` — deps: T061 — DoD: ranking, grouping, visibility filtering and sitemap contents covered.

## M7 — Harden *(serial, tester then reviewer)*

> **State (2026-08-07): M7 complete. `uv run pytest e2e` is 27/27, exit 0.** e2e runs from the
> host against `make up`, **not** inside the `tests` container, which mounts only `tests/`.
> `-m launch_flow` is the six-flow gate (6 passed). Evidence for T071/T072 is committed as JSON
> under `docs/qa/`.

- [x] **T070** — Playwright e2e for the six launch flows: login, album upload, article publish, lightbox by keyboard, theme persistence, search — paths: `e2e/**` — deps: T062 — DoD: all six green against a container started by `make up`.
- [x] **T071** — accessibility pass: keyboard-only sweep, AA contrast in both themes, `prefers-reduced-motion`, alt text, focus visibility — paths: cross-cutting — deps: T070 — DoD: no AA contrast failure; every flow completable without a mouse. *(Both met. The 13 light-theme failures had two roots, both in `tokens.css`: `--on-accent` is now `#14171a` on the accent — 5.03:1, the choice the dark theme already made — and `--text-faint` light is `#646c77`, 4.65:1. Dark theme was clean throughout. Keyboard: login, navigation, search, lightbox, theme toggle and a full admin publish flow all complete without a pointer. The 44 px target-size gap is waived by ADR-010 in favour of WCAG 2.2 AA 2.5.8, which all 54 controls pass; SPEC F12 amended to match.)*
- [x] **T072** — performance check on a 50-photo album: CLS, thumbnail weight, lazy loading, LCP — paths: cross-cutting — deps: T070 — DoD: no layout shift on grid load; thumbnails ≤ ~120 KB; LCP under 2.5 s locally. *(CLS 0.00023, heaviest thumbnail 96.3 KB, LCP 168 ms — `docs/qa/perf-50.json`.)*
- [ ] **T073** — backup command: `pg_dump` plus a media archive into `./data/backups` — paths: `Makefile`, `scripts/backup.sh` — deps: T004 — DoD: a restore from the produced artefacts is documented and tried once. *(Unticked on 2026-08-07: the script and the write-up exist, but the restore had never been run, which is half the DoD. Carried into T086.)*
- [x] **T074** — production override and `Caddyfile`: automatic HTTPS, database port not published, `Secure` cookies under `ENV=production` — paths: `docker-compose.prod.yml`, `Caddyfile` — deps: T002 — DoD: config validates; not deployed in this run.
- [x] **T075** — `docs/HANDOFF.md` and final `docs/STATUS.md` — paths: `docs/**` — deps: T071, T072, T073 — DoD: running, editing, backing up and VPS deployment all documented; the launch checklist in `SPEC.md` fully ticked or its gaps explicitly listed. *(`docs/HANDOFF.md` written: stack, local run, config, the two environment traps, content editing per section, backup **and** restore, VPS deployment with the production overlay, verification status, six known gaps, code map. Launch checklist updated in `SPEC.md` with its two unticked items named.)*

## M8 — Polish *(serial, parent + two implementers)*

> Six defects the owner hit while using the finished site, plus the one launch-checklist
> item M7 left open. Each was **reproduced before it was fixed** — two of the three
> hypotheses that came in with the report turned out to be wrong about the mechanism,
> and one measurement uncovered defects nobody had reported.

- [x] **T080** — lightbox: the open photograph must fit the screen — paths: `app/static/css/photo.css`, `app/static/js/lightbox.js`, `e2e/test_lightbox.py` — DoD: at 360, 1440 and 1920 px, a landscape, a portrait and a panorama at 6000 px all render inside the viewport, and the rendition fetched matches the size drawn. *(The figure was sized by its content, so `max-block-size: 100%` on the image resolved against nothing: a 4000×6000 portrait rendered 1328×1992 in a 900 px viewport, centred, so only its middle showed. Two more defects fell out of the same measurement — `sizes` was a flat `100vw`, and the neighbour preloader fetched the largest rendition and poisoned the cache with it.)*
- [ ] **T081** — image size control inside articles — paths: `app/services/markdown.py`, `app/static/css/prose.css`, `app/static/js/editor.js`, `app/templates/blog/editor*.html`, `app/i18n/ru/blog.json`, `tests/unit/test_markdown.py`, `e2e/test_article_publish.py` — deps: — — DoD: F38 met; a fixed vocabulary of widths, a caption, responsive sources, and every smuggling attempt covered by test.
- [x] **T082** — blog index as a list rather than a tile grid — paths: `app/static/css/blog.css`, `app/templates/blog/index.html`, `app/templates/blog/_post_card.html` — DoD: F8 met; one article per row with the cover on the left, stacking on a phone, the excerpt inside a readable measure, and `.card-grid` itself untouched for photo and dev. *(72 characters a line, measured.)*
- [ ] **T083** — media stored per album and per article, on a volume of its own — paths: `app/services/images.py`, `app/routers/photos.py`, `app/routers/blog.py`, `app/routers/projects.py`, `migrations/**`, `docker-compose*.yml`, `scripts/backup.sh` — DoD: F40 met; existing files **and** the paths recorded in the database migrated together, backup and restore updated to match.
- [ ] **T084** — contact links and copyright editable from the site — paths: `app/routers/pages.py`, `app/templates/partials/footer.html`, `app/templates/pages/home.html`, `app/i18n/ru/common.json`, `tests/api/test_pages.py`, `e2e/test_site_links.py` — DoD: F39 met; one source for both renderings, `http(s)` only, admin-only, covered by the authorisation sweep.
- [x] **T085** — the in-place edit button on the home page — paths: `app/templates/partials/editable.html`, `app/templates/partials/editable_form.html`, `app/i18n/ru/common.json`, `e2e/test_home_editing.py` — DoD: F35 met and covered end to end for the first time. *(The block key carries a dot; `#content-home.intro` parses as «#content-home with class intro», so htmx raised `htmx:targetError` and never sent a request. The five Russian strings those partials hardcoded moved to the catalogue while they were open.)*
- [ ] **T086** — rehearse a restore from `make backup` artefacts — paths: `docs/HANDOFF.md`, `scripts/backup.sh` — deps: T083 — DoD: T073's real DoD, finally met — a dump replayed and a media archive unpacked against a scratch database, with what actually happened written down. *(T073 was ticked in M7 while its DoD — "a restore is documented **and tried once**" — was not met; `SPEC.md` recorded it as open. Corrected here.)*
