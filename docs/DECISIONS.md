# Decisions

ADR-lite. All proposed on 2026-08-04, pending the approval gate.

## Index

- **ADR-001** — FastAPI with server-rendered Jinja2 + htmx, not an SPA
- **ADR-002** — PostgreSQL, with its full-text search as the site search
- **ADR-003** — Media on a host bind mount, database on a named volume
- **ADR-004** — In-process background image processing, not a task queue
- **ADR-005** — Hand-written CSS with design tokens, no CSS framework
- **ADR-006** — Authorisation verified by a structural test, not by review
- **ADR-008** — The test suite runs in a container, not on the host
- **ADR-009** — Strict CSP kept, htmx adapted to it
- **ADR-007** — `lang` columns and externalised UI strings from day one
- **ADR-010** — Touch targets held to WCAG 2.5.8's 24 px, not SPEC F12's 44 px
- **ADR-011** — Picture width in an article is a closed vocabulary on the figure
- **ADR-012** — Media grouped per album/article, still split originals vs derived
- **ADR-013** — Deletion asks the database who still uses a file; there is no reference table
- **ADR-014** — "Best view" is a native-width rendition, not the original file
- **ADR-015** — The copyright line is stored whole, and stops knowing the year
- **ADR-016** — Reorder controls stay enabled at the ends of a list and answer instead of greying out
- **ADR-017** — The UI audit's P2 and P3 findings are deferred to a later iteration
- **ADR-018** — The site is deployed from a registry onto TrueNAS Scale, with the router holding TLS
- **ADR-019** — HEIC is accepted on input; AVIF is not produced on output
- **ADR-020** — F-016 is closed as "not a defect"; only its useful half is built
- **ADR-021** — The blog gets pagination, not an archive by year
- **ADR-022** — `/photo` is paginated for the visitor and whole for the owner
- **ADR-023** — ZFS snapshots are the backup; the repository ships only the command the appliance cannot supply
- **ADR-024** — R-01's engineered form waits for the move off the NAS
- **ADR-025** — R-03 puts the log on disk instead of building a notifier
- **ADR-026** — R-15 waits for R-02 rather than riding along with it
- **ADR-027** — The admin bar is retired into the navigation capsule
- **ADR-028** — Edit affordances become a mode, not a hover reveal
- **ADR-029** — The cabinet is a summary, not an admin panel
- **ADR-030** — `docs/` is prose, and ruff does not format prose
- **ADR-031** — The cabinet ships without a version line
- **ADR-032** — «Просмотр» is the visitor's page, carried by one marker class
- **ADR-033** — The search page's owner-only hits stay visible in both modes
- **ADR-034** — Prefix search is unioned into the existing query, not substituted for it
- **ADR-035** — Video is a facade the reader opts into, and `iframe` never enters the allow-list — **superseded by ADR-041**
- **ADR-036** — The cabinet becomes rooms with their own addresses; the undescribed list leaves it
- **ADR-037** — The orphan scan runs on request, and the script and the page share one implementation
- **ADR-038** — A video's own label stays out of the excerpt only in the next iteration — **its fix is dead code as of ADR-041; the control it was about no longer exists**
- **ADR-039** — The home page's copy blocks render prose without the prose assets
- **ADR-040** — A video's caption is fetched once, at edit time, from YouTube's or Rutube's own oEmbed — never from VK's
- **ADR-041** — Video embeds directly; the click facade is retired and `iframe` re-enters the allow-list
- **ADR-042** — Private articles are shared by a secret token link, not a multi-user account system, and the token is read-only
- **ADR-043** — No rate limiter on the shared-article token route
- **ADR-044** — The shared-article editor gets the blog editor's formatting toolbar, not its image pipeline

Read one entry, not the file: `Select-String -Path docs/DECISIONS.md -Pattern '^## ADR-029' -Context 0,12`.

## ADR-001 — FastAPI with server-rendered Jinja2 + htmx, not an SPA

- Date: 2026-08-04
- Status: proposed
- Context: The owner requires a Python backend, in-place editing on public pages, good first-impression performance for clients arriving from a link, and explicitly no over-engineering. He maintains the result himself and works professionally in Django/FastAPI, not in frontend frameworks.
- Decision: One FastAPI service rendering Jinja2 templates, with htmx for partial updates and a few small vanilla JS modules (theme, lightbox, uploader, editor) plus SortableJS for drag ordering. No Node build step.
- Consequences: Single container, working SEO and Open Graph for free, and one template serving the public view, the edit form and the Markdown preview — so preview cannot diverge from published output. Rich client-side interaction beyond the lightbox and editor would be harder later; acceptable given the non-goals. Alternative (Next.js + FastAPI) rejected as two services and a frontend outside the owner's stack.

## ADR-002 — PostgreSQL, with its full-text search as the site search

- Date: 2026-08-04
- Status: proposed
- Context: Search must span articles, projects and albums. The alternative was SQLite (fewer moving parts) or a dedicated search engine (better Russian ranking).
- Decision: PostgreSQL 18. Generated `tsvector` columns with the `russian` configuration, weighted by field, GIN-indexed, queried with `websearch_to_tsquery` and `ts_rank`.
- Consequences: Site-wide search with no extra container to run, monitor or back up. Russian stemming is good but not best-in-class — accepted for v1. Postgres is also what the owner deploys professionally. Cost: one extra compose service versus SQLite.

## ADR-003 — Media on a host bind mount, database on a named volume

- Date: 2026-08-04
- Status: proposed
- Context: The owner explicitly asked that photo and file directories sit on the hard disk in an external volume so they cannot be lost. However, bind-mounting a PostgreSQL data directory on Docker Desktop for Windows is a well-known source of permission failures, and local review happens on Windows.
- Decision: `./data/media` is a bind mount to the host (photos, the irreplaceable data). PostgreSQL uses a named Docker volume. Database durability comes from `make backup`, which writes `pg_dump` output into `./data/backups` — itself on the host disk.
- Consequences: The owner's actual requirement (photographs survive any container operation, including `docker compose down -v`) is met, while avoiding a Windows-specific failure mode. Database recovery is a restore-from-dump rather than a directory copy, so the backup command is part of the Definition of Done rather than a nice-to-have.

## ADR-004 — In-process background image processing, not a task queue

- Date: 2026-08-04
- Status: proposed
- Context: A batch of 50 camera JPEGs (5–15 MB each) needs three WebP derivatives per photo. Blocking the request is unacceptable; adding Celery/Redis means two more containers on a personal site.
- Decision: Process in a background thread pool inside the web container, with a per-photo status column and a startup sweep that recovers photos left `pending`/`processing`. The app runs a single Uvicorn worker so this state stays coherent.
- Consequences: Matches the real load (one person, one album at a time) with zero added infrastructure. Scaling to multiple workers or concurrent uploaders would require moving to a real queue — recorded here as the known upgrade path rather than built now.

## ADR-005 — Hand-written CSS with design tokens, no CSS framework

- Date: 2026-08-04
- Status: proposed
- Context: The design must feel distinctive ("простое, но очень стильное") and must not look templated. Tailwind would speed up layout work but requires a Node stage in the Dockerfile.
- Decision: Hand-written modern CSS organised with `@layer`, with all colours defined once in `tokens.css`, both themes driven by `data-theme` on `<html>`. Self-hosted variable fonts (Onest, JetBrains Mono — both SIL OFL, both with Cyrillic coverage).
- Consequences: The Docker image stays Python-only and the site makes no third-party network requests, which also makes a strict `default-src 'self'` CSP achievable. Design changes are centralised in the token file. Trade-off: layout work is slower than with a utility framework, and consistency depends on discipline rather than tooling — mitigated by building the design system in M1 before any feature work.

## ADR-006 — Authorisation verified by a structural test, not by review

- Date: 2026-08-04
- Status: proposed
- Context: In-place editing puts admin endpoints on the same URL surface as public pages, so a forgotten dependency silently exposes a mutation. This is the single highest-consequence risk in the build.
- Decision: A test enumerates every route registered on the app and asserts that each non-`GET` route except `/login` rejects anonymous requests. It ships in M2, before the feature modules are written.
- Consequences: An unprotected endpoint added at any later point fails the suite rather than reaching production. Slight friction when intentionally adding a public POST route — it must be added to an explicit allow-list, which is the desired behaviour.

## ADR-008 — The test suite runs in a container, not on the host

- Date: 2026-08-04
- Status: accepted
- Context: On the Windows host, `pytest` hangs before collection — Starlette's test client with the installed httpx never returns. The schema also depends on PostgreSQL-specific features (generated `tsvector` columns, the `russian` text-search configuration), so a substitute database would not exercise what ships.
- Decision: A `tests` service in `docker-compose.yml` (profile `test`, built with `INSTALL_DEV=true`) runs the suite against the real Postgres. `make test` / `.\run.ps1 test` wrap it.
- Consequences: Tests run in the same Linux environment as production, and the Windows-only failure disappears. Cost: a test run needs Docker up, and the first run builds an extra image layer with the dev dependencies.

## ADR-009 — Strict CSP kept, htmx adapted to it

- Date: 2026-08-04
- Status: accepted
- Context: `default-src 'self'` with no `unsafe-inline` is achievable because every asset is self-hosted. htmx breaks it by injecting a `<style>` element for its indicator classes, which produced a console error on every page.
- Decision: Disable that injection with `<meta name="htmx-config" content='{"includeIndicatorStyles": false}'>` and define the indicator rules in `components.css`. The one inline script — the pre-paint theme switch — carries a per-request nonce.
- Consequences: The policy stays strict with no `unsafe-inline` anywhere. Any future need for a per-element inline style has to become a class instead; that constraint is documented in `docs/CONVENTIONS.md`.

## ADR-007 — `lang` columns and externalised UI strings from day one

- Date: 2026-08-04
- Status: proposed
- Context: The owner wants Russian now and possibly English later, without a rewrite.
- Decision: Content tables carry a `lang` column defaulting to `'ru'`; UI strings live in `app/i18n/ru.json` and are resolved through a template helper instead of being written into templates. No language switcher is built in v1.
- Consequences: Adding English later means a second JSON file and a language filter on content queries, not a schema migration or a template sweep. Cost now is small and paid once.

## ADR-010 — Touch targets held to WCAG 2.5.8's 24 px, not SPEC F12's 44 px

- Date: 2026-08-07
- Status: accepted
- Context: F12 as written asks for 44×44 px interactive targets. The T071 sweep at 360 px width found 54 controls under that bar — the menu and theme icon buttons at 34×34, footer social links as small as 17×17, and every `.button` at 36 px tall — while **zero** of them breach WCAG 2.2 AA success criterion 2.5.8, which asks for 24×24 with inline and spacing exceptions (`docs/qa/target-size-360px.json`). 44×44 is Apple's and Google's guidance, not the conformance line the rest of this project is measured against.
- Decision: The accessibility bar for target size is WCAG 2.2 AA 2.5.8. F12's wording is amended from 44×44 to that criterion. No CSS changes; the owner chose this over enlarging the controls, which would have visibly reshaped the navigation capsule and footer on phones.
- Consequences: T071 can close on a standard rather than on a stricter house rule. The capsule and footer keep their intended proportions. If the site later gains genuinely finger-driven surfaces — a mobile-first gallery editor, say — this should be revisited for those controls specifically rather than reopened globally.

## ADR-011 — Picture width in an article is a closed vocabulary on the figure

- Date: 2026-08-07
- Status: accepted
- Context: F38 asks the owner to control how wide a picture sits in an article without touching HTML. Raw HTML is disabled at the parser and stripped by nh3, so the size has to be expressible in Markdown. Three candidates: Pandoc-style dimensions `![alt](url =600x)`, free attributes `{width=60%}`, and named classes `![alt](url){.wide}`.
- Decision: named classes from a closed vocabulary — `{.wide}` and `{.full}`, nothing else, with the default being the text measure. `mdit-py-plugins`' `attrs_plugin` parses `{...}`, restricted to images and to the single attribute `class`; the renderer then reduces that class to the words in `WIDTH_WORDS` and drops everything else. A paragraph holding nothing but an image becomes a `<figure>`, the Markdown title becomes its `<figcaption>`, and the width class lands on the **figure**, not the image — the width is a property of the block the picture occupies. That also keeps `class` off `<img>` in the nh3 allow-list entirely.
- Alternatives rejected: pixel dimensions make the author pick a number that is wrong at some viewport and defeat the responsive sources; `{width=60%}` and friends are open-ended, and nh3 filters attribute *names*, never values, so an open attribute would have to be re-validated by hand anyway — at which point it is a vocabulary with extra steps and a wider hole. `style=` was never a candidate: the CSP forbids it.
- Consequences: the vocabulary is enforced in exactly one place, before the sanitiser, and anything outside it disappears silently rather than half-working. `srcset` is derived from the renditions actually present on disk, so a hand-written or foreign URL renders as a plain `<img>` instead of promising files nobody generated. Adding a third width means a word in `WIDTH_WORDS` and a rule in `prose.css`. The editor carries a disclosure showing the three forms, because the previous insertion feature worked perfectly and went unused for want of a signpost.

## ADR-012 — Media grouped per album/article, still split originals vs derived

- Date: 2026-08-07
- Status: accepted
- Context: files were stored as `originals/<kind>/<yyyy>/<uuid>.<ext>` and `derived/<kind>/<yyyy>/<uuid>_<width>.webp`. The year buys nothing — one album's photographs sat among every other album's, so finding, copying or restoring the files of a single album meant picking them out of a shared directory by matching UUIDs against the database. The owner asked for each album's and each article's files to live together, inside a common logical parent, on storage that survives trouble with the site (F40).
- Decision: the path becomes `<originals|derived>/<kind>/<group>/<name>`, where `kind` is `photos`, `posts` or `projects` and `group` is `<id>-<slug>` — the id because it is unique for the life of the row, the slug because the point of grouping is that a human can find the right directory without opening psql. A later rename leaves the directory name stale but never ambiguous. The **`originals/` vs `derived/` split stays above the grouping**, so that the single `/media` mount over `derived/` continues to make an original unreachable by URL *structurally* rather than by rule. Media stays on a host bind mount rather than a named volume, but the host path moves behind `MEDIA_HOST_DIR` so a server can point it outside the checkout.
- Alternatives rejected: `photos/<album>/{originals,derived}/…` reads better — one directory per album, not two — but it would require serving `/media` through an application route or a rule-based Caddy matcher rather than a mount over a directory that contains nothing private. Trading a structural guarantee for tidiness is the wrong way round on the one property that must not fail. A named Docker volume was rejected too: `docker compose down -v` deletes it, inspecting it means finding `/var/lib/docker/volumes/...`, and backing it up needs a helper container — all worse for "if something goes wrong, nothing is lost".
- Consequences: `scripts/migrate_media.py` moves existing files **and** rewrites `photo`, `post` and `project` paths together with the `/media/...` URLs embedded in article bodies, in both the Markdown and the stored HTML — miss the last of those and published articles lose their pictures silently. `store_original` and `store_and_process` take a `group`; `generate_derivatives` lost its `kind`, which never affected the path it wrote. Every group name goes through `safe_group`, so a crafted value cannot climb out of its parent. Each album is now one `tar` away from being archived on its own, and `scripts/backup.sh` follows `MEDIA_HOST_DIR`.

## ADR-013 — Deletion asks the database who still uses a file; there is no reference table

- Date: 2026-08-08
- Status: accepted
- Context: two of the owner's M9 requests collide. Deletion has to become complete — empty directories survive today, `_delete_cover_files` *guesses* rendition names with a regex that only works while `IMAGE_WIDTHS` happens to be `(640, 1600)`, and a picture removed from an article's text is never deleted at all. Deduplication (F42) has to make one file serve two places. Put together carelessly, they turn "the owner deleted an article" into "the owner broke another article's cover".
- Decision: one new table, `media_asset`, keyed by the SHA-256 of the uploaded bytes and holding the original's path, the derived stem, the dimensions and the size. That is the whole of the dedup mechanism: an upload whose hash is already there reuses the stored paths and writes nothing. Deletion does **not** get a reference table. Instead `release(stem)` asks the database directly whether any row still points at that stem — `photo.original_path` and its three rendition columns, `post.cover_path`, `project.cover_path`, and the `/media/…` URLs inside `body_md`/`body_html` and `value_md`/`value_html` — and deletes the original, every `<stem>_*.webp` found by **globbing** rather than guessing, the `media_asset` row and any directory the removal emptied, only when the answer is nobody.
- Alternatives rejected: a `media_reference` table with a count. It has to be written correctly at every site that touches a path, and there is no way to notice when it drifts: too many references leaks files, which is harmless, and too few deletes a file that is still on a page, which is the exact failure this ADR exists to prevent. A scan cannot drift — it reads the same rows the site renders from.
- Consequences: the check is a handful of `LIKE '%stem%'` queries, i.e. sequential scans, which is nothing across the tens of rows a personal site holds. **The threshold worth remembering: if `post` and `project` together pass a few thousand rows, this wants an index or the reference table after all.** Saving an article becomes "release every asset that was in the old body and is not in the new one", which falls out of the same predicate. `IMAGE_WIDTHS`, `COVER_WIDTHS` and `settings.derivative_widths` stop being three separate answers to "what did we generate?" — the glob does not care.
- Consequence found while implementing it (2026-08-08): deduplication is keyed on the bytes alone, so a hit hands back **whatever ladder the first upload asked for**. The same frame used as a cover (`COVER`, 640/1600) and then dropped into the text serves at most 1600 px there rather than 1920. That is deliberate — T090's DoD requires a known hash to skip derivative generation entirely — and the rung nobody can see is not worth a second copy of the file. It also means the *directory* a file sits in reflects its first use, which is the paragraph below.
- Consequence for ADR-012 that has to be said out loud: a deduplicated file lives in the directory of whatever uploaded it *first*. A frame shared by two articles physically sits under one of them. So `tar` of one article's directory may carry a file another article uses, and hand-deleting a group directory can break a page elsewhere. The application never removes a file something still references; the guarantee does not extend to editing the tree by hand. `make media-orphans` reports shared files so the owner can see which ones they are.

## ADR-014 — "Best view" is a native-width rendition, not the original file

- Date: 2026-08-08
- Status: accepted
- Context: the owner is a photographer who prepares his own frames, and says the current pipeline spoils them — `WEBP_QUALITY = 82` at a 2560 px ceiling. He wants the photography section shown at its best, article pictures capped around FullHD, and confirmed that "blog" and "articles" mean the same thing. The obvious reading, "serve the original as it was uploaded", breaks the one structural invariant this project has: `/media` is mounted over `derived/` **only**, which is what makes an original unreachable by URL as a matter of shape rather than of vigilance (ADR-012).
- Decision: the mount does not move and the originals stay unreachable. "Best" is delivered as a rendition at the original's **own width**, generated only when it is not already in the ladder, at quality 92 — visually indistinguishable from the source and still a file we produced, in the directory the web server is allowed to see. The scattered width tuples become three named profiles in `app.services.images`: `PHOTO` (640, 1600, 2560, native — quality 92), `PROSE` (640, 1280, 1920 — quality 85) and `COVER` (640, 1600 — quality 85). Nothing is ever upscaled. `MAX_UPLOAD_MB` goes to 50, the size the owner says he actually exports.
- Alternatives rejected: copying the original into `derived/` as a "full" rendition — that *is* publishing the original, with a rename to make it feel different. Serving `/media` through an application route or a rule-based Caddy matcher so `originals/` could be exposed selectively — trading a structural guarantee for a configuration one, on the single property that must not fail. A global quality bump without profiles — it would put a 92-quality 2560 px file behind every thumbnail in the grid for nothing.
- Amended while implementing it (2026-08-08): "quality 92" applies **above 640 px only**. Written literally, at every rung, it put the grid's 640 thumbnails at 134 KB against this project's 120 KB budget — a 40% heavier album page for a difference invisible at the ~300 CSS px a tile is drawn at. `images.THUMBNAIL_QUALITY` (82, the old global) governs the 640 rung for every profile; the measurement is back to 97.6 KB. This keeps the decision's stated consequence — "the grid is unaffected" — which the literal wording did not.
- Consequences: the grid is unaffected, because `sizes` keeps it on the 640 rendition — the ≤120 KB thumbnail budget stands and is re-measured to prove it. The lightbox on a large display will now fetch a much bigger file, which is the point of the request; on a phone `sizes` still selects ~1600. A 6000 px upload produces a multi-megabyte rendition and costs real CPU once, at upload, in the background pool. Processing time and peak memory per file both rise with the 50 MB cap; `MAX_PIXELS` (added in Phase 6) is the backstop. If the weight ever becomes a problem the answer is a cap on the native rendition, not a return to re-compressing the owner's work.

## ADR-015 — The copyright line is stored whole, and stops knowing the year

- Date: 2026-08-08
- Status: accepted
- Context: `partials/site_links.html` renders `© {{ current_year }} {{ rights }}`, so only the name is editable and the year is assembled in the template. The owner wants to edit the line itself.
- Decision: `footer.rights` stores the entire line — `© 2026 Дмитрий Богданов` — and the template prints it verbatim. Existing rows are migrated by prefixing the symbol and the current year, so nothing visibly changes on the day it ships.
- Consequences: the year no longer advances by itself; on 1 January the owner edits one field, from the site, which is what "editable in full" means. `current_year` loses its only consumer. The value stays plain text with `value_html` blank, per `pages._put_value` — a name is not Markdown, and rendering it would invite a stray `*` into the footer.

## ADR-016 — Reorder controls stay enabled at the ends of a list and answer instead of greying out

- Date: 2026-08-10
- Status: accepted
- Context: `docs/UI-AUDIT.md` F-002. htmx restores focus after a swap by looking the element up by `id`, which is exactly why `#project-{id}-up`, `#photo-{id}-down` and their siblings carry ids. But when a move lands an item at an end, the button comes back carrying `disabled`, and a disabled element cannot take focus — the restore fails silently and focus falls to `<body>`, so the next Tab restarts at the skip link. The ★ "set cover" button is worse: `{% if ready and not is_cover %}` deletes it outright, so pressing it always drops focus. Separately (F-006), the server's no-op branch is the one mutation in this codebase that sends no `HX-Toast`, so the owner cannot tell a refused move from a failed request. Two findings, one cause.
- Decision: the ↑/↓ and ★ controls are **never** `disabled` and never removed. They are always rendered, always focusable, and the endpoint — which already treats an impossible move as a no-op — answers with an informational toast («уже первый», «уже последний», «уже обложка»). htmx's own focus restoration then works as designed and needs no JavaScript fallback.
- Alternatives rejected: keeping `disabled` and adding an `htmx:afterSettle` handler in `ui.js` that catches focus on `<body>` and redirects it — more code, in a shared script, to repair a state we chose to create, and it leaves F-006 open. Putting `tabindex="0"` on the disabled buttons — that reintroduces a focus stop with no action behind it, which is worse than the defect.
- Consequences: the owner loses one signifier — a button at the end of a list no longer looks unavailable — and gains a sentence that says why nothing happened, which is the more useful of the two and the one every other mutation on this site already provides. `.button:disabled` is still worth having (F-005) for the file inputs and the lightbox controls, so it lands anyway. No test asserted the old behaviour: `grep disabled` over `tests/` and `e2e/` finds nothing, which is itself the coverage gap F-001 describes.

## ADR-017 — The UI audit's P2 and P3 findings are deferred to a later iteration

- Date: 2026-08-10
- Status: accepted
- Context: `docs/UI-AUDIT.md` returned 26 findings — no P0, four P1, fifteen P2, seven P3 — with a three-phase plan. Taking the whole document as one milestone is the anti-pattern the iteration pipeline exists to prevent: several P2 items are consolidations of shared primitives (`.status-chip` replacing three draft chips, `.form-error` replacing four error boxes, splitting `.label` into three roles) that would land underneath the P1 work and make any regression hard to attribute to a cause.
- Decision: iteration I1 takes Phase A only — F-001, F-002, F-003, F-004, plus F-006 which the same change closes and F-005 which is six lines of CSS the F-002 fix leaves half-orphaned. Everything else is deferred, not dropped: F-007…F-018 (P2) and F-019…F-026 (P3) stay in `docs/UI-AUDIT.md`, which remains the backlog for a later round. F-026 in particular is not a defect at all — the audit itself says "no change unless measured", and `docs/qa/perf-article.json` is where that question gets settled.
- Alternatives rejected: closing every P2 in the same round — a week of work touching tokens, the base template and every section sheet at once, against a product with no remote and no staging. Closing nothing but the four P1s and deleting the audit — the fifteen P2s are real findings and re-deriving them would cost more than keeping the file.
- Consequences: the site keeps three visual treatments for «черновик», four near-identical error boxes and one `.label` doing ten jobs until Phase B is scheduled. The gap is documented rather than forgotten, and the P1 work can be verified against a suite whose only new failures come from this round. The audit's own "Definition of done" is therefore **partly** met by I1 by design — the P2 half is explicitly deferred here, which is what that checklist's "or explicitly deferred with a reason in `docs/DECISIONS.md`" asks for.

## ADR-018 — The site is deployed from a registry onto TrueNAS Scale, with the router holding TLS

- Date: 2026-08-13
- Status: accepted
- Context: the production stack had never run on a real server (`docs/HANDOFF.md` §8). The server that appeared is a TrueNAS Scale appliance at `192.168.1.20` with Portainer from its Apps catalogue, behind a Keenetic router on a grey IP. Four properties of that host contradict the existing overlay at once: its own web interface holds ports 80 and 443; a Portainer stack created in the web editor has no build context, so `build: context: .` cannot run; `.env` is git-ignored and there is no checkout on the server for `env_file:` to read; and the same absence leaves `./Caddyfile` with nothing to bind-mount. Behind a grey IP, Caddy also cannot complete an HTTP-01 challenge on its own.
- Decision: GitHub Actions builds two images and pushes them to GHCR under one tag — the application, and a `caddy:2-alpine` with this repository's `Caddyfile` baked in. Portainer is handed one self-contained compose file (`deploy/portainer-stack.yml`) and a set of environment variables; the server stores no source and no configuration files. The Keenetic terminates TLS and forwards to the stack over plain HTTP, so `CADDY_SITE_ADDRESS` becomes a bare port and Caddy asks for no certificate. Photographs and the Postgres data directory are bind-mounted to ZFS datasets. Caddy stays in the stack for the cache headers on `/media` and `/static`, the request-body ceiling and compression.
- Alternatives rejected: **Docker Hub** — the repository is private and image layers carry the source; its free tier allows one private repository, while GHCR is private by default and authenticates with the token Actions already has. **A Portainer stack built from Git on the server** — puts credentials for a private repository on the appliance, makes a NAS compile Python wheels, and still leaves `.env` absent. **Inlining the Caddyfile into the compose file via `configs: content:`** — a second copy of the proxy configuration that drifts from the first; this codebase already carries one "keep the two in step" pair (`MAX_UPLOAD_MB` and Caddy's `max_size`) and the cost of that pair is documented in `docs/HANDOFF.md` §6. **Dropping Caddy** — `/media` is content-addressed and wants `immutable`, and nothing else in the path sets it. **Moving the TrueNAS interface off 80/443** — a system-level change to the appliance for one application's convenience.
- Consequences: `make backup` does not apply on this host — it needs a checkout and `make`, neither of which is there — so durability moves to TrueNAS snapshot tasks on both datasets plus a scheduled logical dump, the snapshot of a live Postgres being only crash-consistent. A release reaches the server when the owner redeploys, not when CI finishes; `latest` follows `main` and CI runs no gates, so the local suite stays the gate that matters. Whether the login throttle sees real client addresses depends on the router forwarding `X-Forwarded-For`, which is why `CADDY_TRUSTED_PROXIES` is a variable rather than a constant, and why it is the third item on the post-deploy checklist. The arrangement is expected to be long-lived but not final: moving to a dedicated server turns `CADDY_SITE_ADDRESS` from a port back into a domain and changes nothing else about the topology.

## ADR-019 — HEIC is accepted on input; AVIF is not produced on output

- Date: 2026-08-14
- Status: accepted
- Context: `docs/ROADMAP.md` R-10 proposes both halves of a media-format change. They turn out to have very different costs. **HEIC in** needs `pillow-heif` (a wheel exists for the container's cp313, verified by a dry-run resolve) and touches intake only: `ALLOWED_CONTENT_TYPES`, `ALLOWED_EXTENSIONS`, the magic-byte table and the extension map in `store_original`. The file is decoded at ingest and the existing WebP ladder is written from it, so nothing downstream — `renditions_of`, the `photo` path columns, `srcset`, the orphan sweep — learns a new format. **AVIF out** is the opposite shape: Pillow 12.3 encodes it with no new dependency at all, but every rendition becomes a second file, `renditions_of` and `_delete_stem` glob `*.webp` by name, `_MEDIA_IN_TEXT` matches `.webp` in stored prose, `photo.thumb_path/medium_path/large_path` hold one format each, and every template that shows a picture would need a `<picture>` with a second `<source>`.
- Decision: take HEIC on input in this iteration. Do not produce AVIF. The owner's call, made at the intake gate.
- Alternatives rejected: **AVIF on the thumbnail rungs only** (640 and 1600, leaving the native rung WebP) — the cheapest useful version, and still the full cross-cutting change to globbing, path columns and templates for a fraction of the win. **AVIF everywhere** — doubles `derived/` against a volume already projected at 20–25 GB (`SPEC.md:229`) and lengthens every 50-file batch on a NAS, in the same iteration that rewrites the photo tile. **HEIC by converting on the client** — needs a decoder in the browser, which means a build step and a large dependency, both refused by `docs/UI-AUDIT.md:812`.
- Consequences: the phone in the owner's pocket stops being a format the site refuses, which is the scenario `SPEC.md:27` describes. Images are served as WebP only, as before; the ~25–30% AVIF saving stays on the table and is cheap to revisit because nothing in this iteration makes it harder. `pillow-heif` is the first native-code dependency added since the initial build, so the image gains a wheel whose provenance is worth watching. If AVIF is taken later, the honest shape is a `formats` field on `Profile` and a glob widened to both extensions — not a second set of path columns.

## ADR-020 — F-016 is closed as "not a defect"; only its useful half is built

- Date: 2026-08-14
- Status: accepted
- Context: F-016 predicted that a four-button toolbar plus a full-width alt input cannot fit a 9:16 tile at 360 px, and that `overflow: hidden` would clip it. I1 then measured what F-001 asked for, and the audit's own correction stands in `docs/STATUS.md`: **zero** targets failed WCAG 2.5.8 at 360 px in an authenticated session. The finding's conformance argument does not survive its own measurement. What remains is a comfort question, and `docs/UI-AUDIT.md:873` already routes comfort questions about target size to ADR-010 rather than treating them as defects.
- Decision: F-016 is not built. F-017 — the count of photographs with no owner-written description, and a marker on those tiles — is built, because it is independent of the layout question and useful at any width.
- Alternatives rejected: **building the preferred fix anyway** (moving alt inputs out of the overlay into a list below the contact sheet) — the most expensive change in Phase B, restructuring `_photo_tile.html` and the ratio-driven flex layout that `docs/UI-AUDIT.md:882` explicitly asks not to be touched, with no measured failure behind it. **Shrinking the buttons** — refused by the finding itself.
- Consequences: the audit's Phase B exit criterion "the admin UI measures as well as the public one" is met by measurement rather than by rebuild. On a narrow screen the tile overlay stays dense; if the owner reports it as painful from an actual phone, that is a new finding with evidence, which is a better basis than arithmetic. The alt inputs remain inside the hover overlay, so F-017's count is what makes undescribed photographs findable.

## ADR-021 — The blog gets pagination, not an archive by year

- Date: 2026-08-14
- Status: accepted
- Context: `docs/ROADMAP.md` R-05 bundles three things: bounded indexes, an archive by year for the blog, and honest result counts on search. Only the first is the problem the item argues for — "invisible at ten articles, a multi-second page and a megabyte of HTML at eighty". An archive by year is a second navigational entity: its own URL space, its own canonicals, its own sitemap entries, its own empty states for a year with one post, and a year list on the index that is itself a thing to design.
- Decision: bounded indexes and search counts now; no `/blog/YYYY`. The owner's call at the intake gate.
- Alternatives rejected: **archive now, pagination later** — inverts the argument; the archive does not bound anything, since a prolific year still renders whole. **Both now** — widens a milestone that already carries the whole of Phase B.
- Consequences: an article older than one page is reachable by paging, not by year. The URL scheme stays small, which is the property R-05 says is cheaper to get right before the pages are indexed and shared. If an archive is wanted later it composes with pagination rather than replacing it.

## ADR-022 — `/photo` is paginated for the visitor and whole for the owner

- Date: 2026-08-14
- Status: accepted
- Context: `_board.html` is the swap target of six mutating endpoints, and `album_reorder` (`app/routers/photos.py:700`) hands the posted ids and the **global** ordered row list to `_reorder_from_ids`. Paginating the list the owner sees would make a drag mean something different on page 2 than on page 1, would require a page parameter threaded through all six endpoints, and would leave ↑ on the first album of page 2 with no defined destination. The payload problem R-05 names is a visitor's problem: the owner is one person on a page he is editing.
- Decision: `_visible_albums` bounds what an anonymous visitor is shown and links to the rest; a signed-in owner is shown every album. `_board()`, `album_reorder`, `album_move` and `_reorder_from_ids` are not touched.
- Alternatives rejected: **paginate for everyone and make reorder slice-aware** — changes the meaning of a working primitive, in an iteration whose whole risk is regression, for the convenience of one user. **Paginate for nobody** — leaves the index unbounded, which is the finding. **Infinite scroll** — needs client-side state, has no shareable URL, and is not crawlable.
- Consequences: the owner and the visitor see the same `/photo` in different lengths, which is a difference the site already draws for drafts, unpublished albums and failed photos. Drag-reorder keeps working over the whole set with no change at all. The asymmetry must be stated in F3 so it is not later read as a bug — it is.

## ADR-023 — ZFS snapshots are the backup; the repository ships only the command the appliance cannot supply

- Date: 2026-08-15
- Status: accepted
- Context: `scripts/backup.sh` calls `docker compose exec -T db pg_dump`, which needs a compose project in the working directory. The TrueNAS deployment has none: `deploy/portainer-stack.yml` is pasted into Portainer's web editor, the server holds no checkout, no compose file and no `scripts/` directory (ADR-018). The script cannot run there at all, which is the mechanical reason R-01 is still open. But both halves of the data already sit on ZFS datasets — `deploy/portainer-stack.yml:50-55` chose the `pgdata` mount point *so that* snapshots would cover the database — and TrueNAS takes periodic snapshots and replicates them between machines from its own web interface, with no code anywhere. The owner's position at the gate was that while the site is in test mode with throwaway photographs he does not want an engineered backup at all, and would accept copying files by hand.
- Decision: the appliance's Periodic Snapshot Task *is* the routine backup, configured in the TrueNAS interface and recorded in `docs/HANDOFF.md` §5 — **zero lines of code in this repository**. The repository contributes exactly one thing the interface cannot: `scripts/backup.sh` gains an additive server mode (`BACKUP_DB_CONTAINER` → `docker exec` instead of `docker compose exec -T db`) so a *logical* dump is one pasted command on the server when one is actually wanted — before a migration, before an upgrade, before the move off the NAS. No cron task, no retention policy, no manifest, no rehearsal harness.
- Alternatives rejected: **a cron task on the host running `backup.sh` nightly** — the previous draft of this ADR, and four tasks of work (server mode, retention, manifest, rehearsal) to reproduce, in shell, what the appliance already does natively and replicates for free. **A backup sidecar in the stack** — puts a scheduler and a retention policy inside the stack that serves the site, and is dead exactly when the stack is dead. **Nothing at all** — the owner offered it, and it is one `docker exec` away from being avoidable; a five-line change is cheaper than the conversation about whether to make it.
- Consequences: a ZFS snapshot of a running Postgres is **crash-consistent, not a clean dump** — it restores the way a power cut restores, which Postgres is built to survive but which is not what a DBA would call a backup. The stack file already says this in a comment. That trade is acceptable for test data and is exactly what the logical dump exists to close when it stops being acceptable. Retention, off-machine replication and the schedule all live in the TrueNAS interface, so `docs/HANDOFF.md` §5 is their only record here and has to be exact. Nothing in this decision blocks the engineered form later; ADR-024 says when it comes back.

## ADR-024 — R-01's engineered form waits for the move off the NAS

- Date: 2026-08-15
- Status: accepted
- Context: R-01 as the roadmap wrote it asks for a schedule owned by the repository, a 7/4/6 retention policy, a self-describing set sufficient to rebuild from nothing, and a copy pushed off the machine with `rclone` or `rsync`. Each is defensible for a site holding work that cannot be recreated. This one currently holds test uploads on an appliance in the owner's flat, and he said so twice at the gate: he would be satisfied copying files by hand, and was prepared to drop the item entirely.
- Decision: defer the engineered form — retention policy, manifest (the former F58), restore rehearsal on the server, and any off-machine push this repository configures — until the site moves to a dedicated server. What ships now is ADR-023's snapshot task and one-command dump. The off-machine copy stays the owner's, arranged with TrueNAS replication, and this repository holds no credential for it.
- Alternatives rejected: **build it now anyway** — four tasks and a shell retention policy protecting photographs that are deliberately disposable, in an iteration whose other half is a production 500. **Build the `rclone` push against an unconfigured destination** — a code path nothing exercises, which is the shape of every backup that turns out not to work.
- Consequences: for the duration of test mode a total loss of the appliance costs the photographs and the written content; the site itself is rebuildable from this repository and the three secrets are regenerable. That is a real, accepted exposure and it is the owner's, stated knowingly. The trigger to revisit is the move to a dedicated server, which is also when the photographs stop being disposable — the same trigger as ADR-025's. R-01 stays open in `docs/ROADMAP.md` rather than being ticked; this iteration must not claim it is done.

## ADR-025 — R-03 puts the log on disk instead of building a notifier

- Date: 2026-08-15
- Status: accepted
- Context: R-03 as written has three parts: an external uptime check on `/healthz`, a notifier for 500s and for photographs left at `status=failed`, and log rotation. The notifier is the only one that is application code, and the only one needing a channel, a secret and a policy about what is worth interrupting someone for. The owner's answer at the gate was that he does want a Telegram bot, but not now and not on this machine — "this is something to do when the site is on a dedicated server". What he wants instead is immediate and much smaller: **the log file sticking out of the container so he can open it on disk and see what went wrong.**
- Decision: the application writes its log to a file under a bind-mounted directory alongside the media (F58), rotated by size and count, in addition to the stdout the container already prints; the container log drivers get explicit ceilings (F60); the external `/healthz` check is documented. The notifier is not built, and the Telegram bot is deferred with the same trigger as ADR-024 — the move to a dedicated server.
- Alternatives rejected: **`docker logs` and the existing json-file driver** — the lines are already on disk, but under `/var/lib/docker/containers/<id>/`, behind a shell on the appliance and a container id that changes on every redeploy; the owner asked for a file he can open, and that is not one. **A generic webhook left unconfigured** — an untested path pretending to be a safety net, the same objection as ADR-024's rejected `rclone` push. **Ship the Telegram bot now anyway** — it was wanted, but not here: it is a secret and an outbound dependency added to a machine the site is about to leave.
- Consequences: a 500 is still not pushed to anyone — it is written where the owner can find it in ten seconds instead of ten minutes, which is the actual improvement he asked for. A photograph left at `failed` remains visible only on its own page. The restart-loop failure R-03 names is caught by the external check regardless, and R-02 makes the bad `latest` that causes it much less likely. The log file is a new place secrets could leak to, so F58 states that none may appear in it and the review must check. When the bot is built later, F60's ceiling means the evidence it would have reported is still on disk.

## ADR-026 — R-15 waits for R-02 rather than riding along with it

- Date: 2026-08-15
- Status: accepted
- Context: the roadmap's own I2-Operations grouping puts R-15 (performance as a gate) in the same iteration as R-02, "because it is a job in the workflow R-02 creates". True, but it is also a second set of decisions: which of the existing Playwright measurements run in CI, on what hardware budget, and what a threshold breach does to a push. The measurements in `docs/qa/perf-50.json` and `perf-article.json` were taken on this machine; the same numbers on a GitHub runner are a different measurement, and choosing thresholds that hold on both is the actual work.
- Decision: R-15 is deferred out of I3. R-02 builds the workflow with a job structure that a performance job can be added to.
- Alternatives rejected: **fold R-15 in now** — turns a two-file change into a threshold-calibration exercise inside an iteration whose other half is backups. **Drop R-15** — the budget in `SPEC.md:151-154` is real and nothing enforces it; deferring is not dropping.
- Consequences: page weight and LCP stay unenforced for another iteration, as they have been since launch. F-026's six render-blocking stylesheets stay open, which the audit itself conditioned on a measurement saying it matters. The cost of doing R-15 next is now one job in an existing workflow.

## ADR-027 — The admin bar is retired into the navigation capsule

- Date: 2026-08-16
- Status: accepted
- Context: the site has one persistent object on every page — the navigation capsule. A signed-in owner gets a second one: `.admin-bar`, fixed at the bottom centre (`app/static/css/admin.css:113-130`), a different shape, holding the mode indicator, «Показать правки» and «Выйти». Because it floats over the end of the document, `admin.css:28-34` lengthens the whole page with `padding-block-end` and sets `scroll-padding-block-end` on the root so a tabbed-to control does not stop underneath it. That was the right fix for F-015 given a bar at the bottom; it also means the signed-in page is literally a different length from the visitor's. The owner's complaint is the plain-language version of the same thing: the «Выйти» button in the middle covers part of the site. And «Выйти» is the rarest action the owner takes, holding the most valuable position on the screen.
- Decision: delete `partials/admin_bar.html` and its clearance rules. The navigation capsule gains an owner control that opens a menu holding the mode indicator, the mode switch, a link to the cabinet and «Выйти» (F61). Nothing is fixed over the content, and the document reserves no clearance a visitor's would not.
- Alternatives rejected: **move the bar to the top and reserve space for it, as WordPress does** — solves the overlay but keeps two chromes competing on a site whose whole navigation is one capsule. **Keep the bar and shrink it** — the position, not the size, is what covers the page. **Leave «Выйти» in the open** — the objection is not that it is hard to reach.
- Consequences: `tests/api/test_authz_sweep.py:121` greps anonymous HTML for the literal `admin-bar`; that marker is replaced by the owner menu's class. **The list is extended, never shortened** — the guarantee it encodes is unchanged, and F36 is reworded for the same reason. The menu is a new focus-management surface: it opens, traps nothing, closes on Escape and returns the caret, exactly as `nav.js` already does for the mobile links. WCAG 2.4.11 stops being a thing this layout has to work around, because there is nothing left to be obscured by.

## ADR-028 — Edit affordances become a mode, not a hover reveal

- Date: 2026-08-16
- Status: accepted
- Context: there are two discovery mechanisms for the same controls, running at once. Every in-place affordance rests at `opacity: 0` and appears on hover — `.editable__edit` (`admin.css:183`), `.site-links__edit` (`components.css:758`), `.photo-item__admin` (`photo.css:463`) — each with a focus-visible escape, a `@media (hover: none)` branch for touch, and a `:root.show-edits` override. That override is «Показать правки», added in I2 to close F-018: hover is no use for finding an affordance nobody told you about. It closed the finding without removing its cause, so the toggle now duplicates hover rather than replacing it. The owner reports exactly that: the control feels redundant and is still necessary. The cost is also carried by the tests — `e2e/test_a11y.py:111-122` forces `opacity: 1` through the CSSOM so the sweeps can measure controls the page is hiding.
- Decision: two modes, one mechanism. In **Просмотр** no edit control is rendered visible at all, hover included — the page is the page a visitor gets. In **Правка** every affordance is shown permanently and editable regions are outlined. Twelve rules across three stylesheets collapse into one class on the root, which the pre-paint script in `base.html` already applies. F55 is reformulated to describe the mode rather than the reveal.
- Alternatives rejected: **keep hover and drop the toggle** — returns to F-018, which was a real finding. **Keep both and make the toggle louder** — polishing the redundancy the owner is objecting to. **Show every affordance always** — the site is also the published page; the owner reads it far more often than he edits it, and `.editable__edit` borders under every paragraph make that unpleasant.
- Consequences: all four tests in `e2e/test_show_edits.py` change, and so does the reveal helper both accessibility sweeps use — those sweeps get *better*, because they will measure the real «Правка» state instead of simulating it through inline styles. `e2e/test_admin_keyboard.py`'s helper docstring describes the old resting state and its helper must enter «Правка» first; the focus-restoration behaviour it actually tests is untouched. The `@media (hover: none)` branches disappear, so touch and pointer behave identically for the first time. The choice keeps living in `localStorage` and keeps being applied before first paint, so nothing flashes.

## ADR-029 — The cabinet is a summary, not an admin panel

- Date: 2026-08-16
- Status: accepted
- Context: the owner asked for "a personal page visible only when logged in". `SPEC.md` lists as a non-goal "a separate admin panel as the primary editing surface", and ADR-001's whole model is that the published page and the editing page are the same page. But there is a real gap that in-place editing cannot close: state that is not on the page you are looking at. Drafts are visible only on `/blog`, unpublished albums only on `/photo`, and a photograph left at `status=failed` only inside its own album — ADR-025 declined to build a notifier for exactly that, and named the log file as the substitute, which requires knowing something went wrong first.
- Decision: a private page at `/me` answering one question — what needs the owner's attention — and linking every answer back to the page that edits it. It renders lists and one existing action (the retry that `_photo_tile.html` already offers); it is not where anything is authored. The non-goal stands, because the primary editing surface does not move.
- Alternatives rejected: **a full `/admin` panel** — contradicts the non-goal, doubles the interface, and the site's editing model is its best feature. **Put the summaries on the home page behind `is_admin`** — makes the owner's home page a different document from the visitor's, which is the thing ADR-001 avoids. **Wait for a notifier (ADR-025's deferral)** — the notifier needs a channel, a secret and a policy; a page the owner already visits needs none of them and answers the same question.
- Trigger to revisit: the panel question was put again at I4's gate — *build one now?* — and declined again, for the reasons above plus one this ADR should record: the site is still in test mode carrying disposable content, so **the workload a panel would be designed for has not been observed yet**. The question comes back on a reported pain, not on a date. The likeliest pain is photographs at scale — the same operation over many images at once (delete a batch, move a batch between albums, publish a batch, retry every failure in one), which in-place editing forces through one tile at a time. **The answer to that trigger is multi-select inside the album grid that already exists, not `/admin`**: a selection state on the tiles the owner is already looking at, one action bar over the selection, and the per-photograph routes that exist today taking a list instead of an id — no second editing surface, no second copy of the queries, and ADR-001's model intact. A panel becomes the right answer only if the pain turns out *not* to be per-album — cross-cutting work over content from several sections at once, which no single grid can express. `/me` is the cheap probe for exactly that: it is the one screen showing every section together, so what the owner tries to **do** from it is the evidence for which of the two answers he actually needs.
- Consequences: `/me` answers **404** to anyone without a session, not a redirect to `/login` — the same treatment a draft article gets, so the address does not confirm its own existence; `robots.txt` gains a `Disallow` and the page a `noindex`. It joins `admin_surfaces` in `e2e/conftest.py`, so both accessibility sweeps cover it, and the parametrized admin-read case in `test_authz_sweep.py`. **Changing the password is not on it**: `ensure_admin_user` (`app/security.py:196-201`) rewrites the hash from `ADMIN_PASSWORD` at every start, so a password set through the UI would revert at the next restart; the page says where the password lives rather than pretending to own it. Every list it renders is a query that already exists somewhere in the routers, so nothing about the model changes and there is no migration.

## ADR-030 — `docs/` is prose, and ruff does not format prose

- Date: 2026-08-16
- Status: accepted
- Context: I4's baseline found `ruff format --check .` red on `docs/iterations/I3-operations.md`. Ruff formats fenced Python blocks inside Markdown, and the block it wants to rewrite is the illustrative excerpt of the T125 dedup race — pseudo-code with aligned trailing comments (`# ← the row is now in-flight, on disk`) that carry the explanation. I3's own baseline recorded "clean, 127 files"; the count is 128 now and the extra file is the I3 page itself, written after that check ran and never checked since. The failure is inherited, and it will recur for every iteration page that explains code by quoting it.
- Decision: add `docs` to `extend-exclude` in `pyproject.toml`. `docs/` holds English prose artefacts, not source; nothing under it is imported, executed or tested.
- Alternatives rejected: **change the fences so ruff skips them** — fixes one file, loses syntax highlighting in the document whose job is explaining code, and the next iteration page hits it again. **Accept ruff's rewrite** — the aligned comments are why the excerpt is laid out that way; a formatter would delete the explanation to satisfy a rule about code that is not code. **Pin an older ruff** — nothing is wrong with the version.
- Consequences: a Python file that ever lands under `docs/` is not linted; none exists and none is expected — scripts live in `scripts/`, which is not excluded. The CI lint gate from F59 goes green on the same command it runs today.

## ADR-031 — The cabinet ships without a version line

- Date: 2026-08-16
- Status: accepted
- Context: the cabinet was specified with a "state" block including the running image's version. The application does not know its own build: nothing in `app/` reads a version, and `static_url` versions assets off file mtime (`app/templating.py:71`). Surfacing a `sha` means a build arg in the Dockerfile, an environment variable through `docker-compose.yml`, `docker-compose.prod.yml` and `deploy/portainer-stack.yml`, and a change to `publish.yml` to pass it — four deployment files for one line of text.
- Decision: deferred out of I4. The cabinet ships with what the database already holds.
- Alternatives rejected: **read the git sha at runtime** — there is no checkout in the image, by design. **Show the build date from a file mtime** — a plausible-looking number that answers a different question, which is worse than no number.
- Consequences: the owner still identifies the running image the way he does today, through Portainer and the tag `publish.yml` moved. The cost of adding the line later is unchanged by this iteration and the plumbing is the same work whenever it is done — it becomes worth doing when something else needs the version too, most likely a 500 report.

## ADR-032 — «Просмотр» is the visitor's page, carried by one marker class

- Date: 2026-08-16
- Status: accepted
- Context: I4 built the mode over the three affordance families that had a hover reveal to replace — `.editable__edit`, `.site-links__edit`, `.photo-item__admin`. Everything else the owner sees is gated on `is_admin` alone and therefore renders in both modes: the upload zone, «Новый альбом», the album's edit/publish/delete row, the reorder hints, the draft chips and notes, the drafts section on `/blog`, unpublished album and project cards, unfinished photo tiles, and `.photo-item--undescribed`'s dashed rim — which the owner reported as a defect, because beside `.photo-item__link:hover::after`'s solid accent rim it reads as a line that changes on hover for no reason. F55 already promised «the page he reads is the page a visitor reads»; the implementation kept that promise for three selectors out of twenty-odd. This is a defect against F55, not a new requirement.
- Decision: every owner-only block carries the class `owner-only`, and `admin.css` — which only a signed-in owner ever downloads — hides all of them in one rule, `:root:not(.show-edits) .owner-only { display: none }`. The three families from I4 fold into the same marker and lose their bespoke `display: none` default and their `:root.show-edits` override, so there is exactly one mechanism. In «Просмотр» that includes unpublished cards and unfinished tiles, because the server withholds those from a visitor and the mode is meant to reproduce what a visitor gets. Two things stay visible in both modes: **the mode switch itself**, or the mode could not be left, and **the one line on a draft's own page saying a visitor would not see it** — a statement of fact, not an affordance, and its absence would make the mode misleading rather than faithful.
- Alternatives rejected: **a cookie, so the server renders the visitor's page** — literally faithful, and it costs a round trip per switch, an `is_editing` split through every router and template, and a mode that htmx swaps have to carry; it also cannot render the owner menu, so it would not be literal after all. **Keep per-selector rules and add the missing ones** — the same twelve-rule pattern that just failed to cover the page once; a block added next year would leak again by default rather than by mistake. **`visibility: hidden` or `opacity: 0`** — I4 already established that only `display: none` takes a control out of the accessibility tree and the tab order at once, which is what "the page a visitor reads" means.
- Consequences: `owner-only` is a class that must never reach a visitor, so it joins the marker list in `test_authz_sweep.py` — that list only ever grows. Every e2e flow that clicks an owner control must enter «Правка» first, through the `switch_mode` helper I4 introduced; the last two iterations each owed more of those than their impact map named, and this change widens the hidden set by roughly a factor of seven. The HTML a signed-in owner receives is unchanged — the fidelity is visual and in the accessibility tree, not in the source — which is stated here so that nobody later reads «as if not authenticated» as a promise about bytes.

## ADR-033 — The search page's owner-only hits stay visible in both modes

- Date: 2026-08-16
- Status: accepted
- Context: `/search` passes `include_hidden=admin is not None` (`app/routers/search.py:53`), so a signed-in owner sees drafts and unpublished items among the results. Under ADR-032 those rows are content a visitor would not get, and hiding them is one class in `partials/search_group.html`.
- Decision: not done. The group heading is `t("search.group_heading", shown=…, total=…)` — «Показано 3 из 5» — and both numbers come from the server. Hiding two rows in the browser leaves the heading claiming five above three visible ones.
- Alternatives rejected: **hide the rows and leave the counts** — replaces a small leak with a visible contradiction on the same line. **Recount in the browser** — the `total` is a `count()` over the whole predicate, not the length of the list, so it cannot be recomputed from what is on the page. **Send the mode to the server** — the mode is a `localStorage` class applied before first paint; making it a request parameter is ADR-032's rejected cookie design arriving through a side door.
- Consequences: in «Просмотр» the search page is the one surface where the owner still sees more than a visitor. It is a page they reach by typing, not one they read the site through, and it says so in the iteration record. If the mode ever does reach the server, this is the first thing to revisit.

## ADR-034 — Prefix search is unioned into the existing query, not substituted for it

- Date: 2026-08-16
- Status: accepted
- Context: search runs `websearch_to_tsquery('russian', q)` (ADR-002), which matches whole stemmed lexemes: «фотогр» finds nothing. The owner asked for partial matching «as it is normally done», which for a text search means matching a prefix.
- Decision: build a second `tsquery` in Python — each token stripped of tsquery metacharacters and suffixed `:*`, passed through `to_tsquery('russian', …)` so the dictionary still stems it — and OR it into the existing one: `websearch_to_tsquery(…) || prefix_query`. `ts_rank` runs against the combined query. When the query yields no usable token the prefix half is omitted and the statement is exactly today's.
- Alternatives rejected: **replace `websearch_to_tsquery`** — quoted phrases and `-excluded` terms are its semantics and nothing else provides them; every existing search test asserts behaviour that would have to be re-argued. **`pg_trgm`** — matches inside a word and tolerates typos, at the cost of a PostgreSQL extension, a migration, new indexes on three tables, and a similarity score that has to be reconciled with `ts_rank` into one ordering. Prefix matching is what the request meant; the rest is available later and is recorded here so the option is not lost. **Building the prefix query in SQL from `tsvector_to_array`** — one statement, and unreadable at the point where a mistake is an injection.
- Consequences: strictly additive — nothing found today stops being found, so no existing search test changes, which is what makes this task cheap to verify. The tokeniser is the one place user input reaches `to_tsquery`, whose error on a malformed query is a 500; it strips `&|!()<>:*'` and drops empty tokens, and it gets its own unit tests including the empty, punctuation-only and over-long cases.

## ADR-035 — Video is a facade the reader opts into, and `iframe` never enters the allow-list

- Date: 2026-08-16
- Status: accepted
- Context: the owner asked for video in articles and chose the service-link form over uploading files. The CSP is `default-src 'self'` with no `frame-src` (`app/main.py:142-155`), so an embed is blocked outright today; the Markdown pipeline disables raw HTML at the parser *and* sanitises the output, and `attrs_plugin` reaches images and `class` only.
- Decision: a paragraph holding nothing but a link to YouTube, RuTube or VK Video — the same shape `_figure_paragraphs` already recognises for pictures — renders as `<figure class="prose-video">` containing a `<button>` with the embed URL in a data attribute, and a small script builds the `<iframe>` when it is pressed. If that link wraps a picture from this site's own media, the picture is the poster; otherwise the button is a plain framed play control. `ALLOWED_TAGS` gains `button` and nothing else; `iframe` stays out, so no path through the sanitiser can produce one. The CSP gains `frame-src` with the three hosts named explicitly, and `img-src` is not touched — a poster is always this site's own file.
- Alternatives rejected: **render the `<iframe>` directly** — needs `iframe` in the allow-list, which turns a second mistake anywhere in the parser configuration into an embedding hole, and it contacts the service on page load for every reader. **The service's own thumbnail as the poster** — `i.ytimg.com` in `img-src`, and the reader's address reaches Google before they have shown any interest. **A third-party lite-embed component** — a script from a CDN, which `script-src 'self'` forbids and which would be the first dependency of its kind here.
- Consequences: the URL in the data attribute is author-influenced but renderer-closed, exactly as `WIDTH_WORDS` closes the class attribute — nh3 filters attribute names and never values, so the closing has to happen in the renderer, and the recogniser is a set of anchored patterns per host rather than a general URL parse. A visitor's page carries no `iframe` and makes no third-party request, which is assertable and is exit criterion 6. Self-hosted `mp4` is not built: it is a storage and bandwidth commitment with no transcoding behind it, and it would need a second player kept accessible. Adding it later is `media-src 'self'` — already implied by `default-src` — plus the uploader, and touches nothing decided here.

## ADR-036 — The cabinet becomes rooms with their own addresses; the undescribed list leaves it

- Date: 2026-08-16
- Status: accepted
- Context: `/me` shipped in I4 as one column of grouped links. On the owner's real data its «Снимки без описания» section is 24 rows all reading «Снимок в альбоме «X»», told apart only by where they lead — the failure I4's own record predicted and left for this intake. The owner also wants the cabinet to be where administrative things live that have no place on the site itself, and one growing column is not that.
- Decision: three rooms, each its own route and address — `/me` («События», F62's list), `/me/stats` («Сводка») and `/me/media` («Медиа») — sharing a layout partial with a menu that marks the room it is in. Photographs with no description are removed from the cabinet entirely; the prompt stays in the album, in «Правка», where `photo-item--undescribed` and the count line are a hint in place at the moment the owner is looking at the picture.
- Alternatives rejected: **tabs swapped by htmx on one route** — one address for three views, so a room cannot be linked, opened in a tab or bookmarked, and the browser's back button stops meaning anything. **Collapse the undescribed list behind a disclosure** — keeps a non-problem on the page that lists problems, which is the objection. **A generic `/admin`** — still contradicts the non-goal at `SPEC.md:265` and ADR-029; these are read-only rooms that link back to in-place editing, and none of them deletes anything.
- Consequences: `tests/api/test_me.py` and `e2e/test_me.py` both assert the undescribed group today and both change — a behaviour change, which is why it is here. Every room needs the same 404-without-a-session treatment as `/me`, the same `noindex, nofollow`, and a place in `e2e/conftest.py`'s `admin_surfaces` so both accessibility sweeps cover it. `seo.py`'s `Disallow: /me` already covers the prefix; that is checked rather than assumed. The next administrative thing is a fourth room, and this decision is what makes that cheap.

## ADR-037 — The orphan scan runs on request, and the script and the page share one implementation

- Date: 2026-08-16
- Status: accepted
- Context: «Медиа» wants to show the files on disk nothing points at. That answer exists only in `scripts/media_orphans.py`, which walks both media roots with `rglob` and asks `owners_of` per stem. On the owner's storage that is a filesystem walk of unbounded duration inside a request that also has to render a page.
- Decision: the room renders immediately from the database — photographs in flight, failed, totals, `SUM(media_asset.byte_size)` — and the disk walk happens only when the owner presses «Проверить», answering into its own region via htmx. The walk itself moves out of the script into a service both call, so the number on the page and the number the command prints cannot disagree; the script keeps `--prune` and keeps being the only thing that deletes.
- Alternatives rejected: **walk on page load** — makes the cabinet's slowest room its front door, on the one page that must stay usable when something is wrong. **Cache the result** — a stored number about a directory that changes under it, and the first question about it is always "when was this measured". **Duplicate the walk in the router** — two implementations of "what is an orphan", and ADR-013 is precisely about not having two answers to who owns a file.
- Consequences: `scripts/media_orphans.py` is edited by a task that names it, and its behaviour from the command line must be identical afterwards — verified by running it before and after and diffing the output. The room shows a size and a count and offers no delete; pruning stays a deliberate command on the server, where the owner can read what will go before it goes.

## ADR-038 — A video's own label stays out of the excerpt only in the next iteration

- Date: 2026-08-18
- Status: accepted
- Context: `excerpt_from` (`app/services/markdown.py:504`) renders the body and strips every tag, keeping the text inside. Since T138 a paragraph that is only a video link renders as a `<button>` whose label is «▶ Смотреть видео», so an article that *opens* with a video and has no excerpt of its own puts that label at the front of its meta description and its card. Run 7 of the review confirmed it by probe. Before T138 the same article put a raw URL there, so nothing that read well now reads worse.
- Decision: leave it. It is recorded here and in `docs/iterations/I5-authoring.md` (T138, note 10) and goes to the next intake as its own item.
- Alternatives rejected: **fix it inside T138** — the task's DoD says nothing about excerpts, and the regression contract puts code a task does not name out of bounds; **strip `figure.prose-video` in `excerpt_from` now** — the right fix, but it is a change to what every card and every meta description on two sections contains, which is an owner-visible SEO change and deserves its own line in an intake rather than a quiet ride on a review.
- Consequences: one class of article — video first, no excerpt written — carries a control's label in its description until the next iteration takes it. The owner can defeat it today by writing an excerpt or by putting a sentence above the video.

## ADR-039 — The home page's copy blocks render prose without the prose assets

- Date: 2026-08-18
- Status: accepted
- Context: `/` edits its eyebrow and its intro in place through the same `render_markdown` the blog uses (`app/routers/pages.py:45,108`), but it loads neither `prose.css` nor `video.js` — those are on `blog/post.html`, `dev/detail.html` and `blog/editor.html`. A bare video link pasted into a home block therefore renders the facade with no styling and a play control that does nothing, because the delegated listener that builds the `iframe` is not on the page. Found by run 7 of the review; not a regression, since before T138 the same paste produced a bare link.
- Decision: leave the home page as it is. The two blocks are one-line copy — an eyebrow and an intro — not an article, and no requirement asks them to carry video.
- Alternatives rejected: **load `prose.css` and `video.js` on `/`** — a stylesheet and a script on the site's most-visited page, for every visitor, to cover a video in a hero eyebrow; **give the copy blocks a restricted renderer** — a second definition of what Markdown means on this site, and F28's whole point is that preview and published output come from one renderer.
- Consequences: a video link in a home block is a dead control that only the owner can produce and only the owner sees the consequence of. If the home page ever gains a real prose block, this decision is the thing to revisit, and the fix is two lines.
- **Update, ADR-041 (I7, 2026-08-26):** the premise above no longer holds. There is no more click-to-build script for `/` to lack, and `_ProseRenderer.link_open` renders the `<iframe>` itself regardless of which page called `render_markdown` — so a bare video link in a home block is now a live, unstyled (no `prose.css`) but functional embed, not a dead control. `/` still loads no `prose.css`, so the frame renders at its intrinsic size rather than the `16 / 9` box `prose.css` gives it elsewhere; that is the one thing this decision would need to revisit if it mattered, and nothing here says it does. The decision to leave the home page as it is stands regardless — reviewed as part of I7's `secure-review` (Run 9, `docs/REVIEW.md`) and found to raise no new risk, only a cosmetic one nobody has asked to fix.

## ADR-040 — A video's caption is fetched once, at edit time, from YouTube's or Rutube's own oEmbed — never from VK's

- Date: 2026-08-25
- Status: accepted
- Context: the owner asked, in I6 intake, for a video in an article to carry some identifying information in the editor rather than an anonymous play button. `_video_paragraph` (`app/services/markdown.py:200`) already turns `[Название](url)` or `[![заставка](url)](url)` into a caption or a poster — the gap is that nothing teaches or offers this, so a pasted bare link stays anonymous. Checked live against all three services `_VIDEO_SERVICES` recognises: `https://www.youtube.com/oembed` and `https://rutube.ru/api/oembed/` both answer a title and a thumbnail for a real URL of each, publicly, with no key. VK has no equivalent — only the authenticated `video.getOembed` API method, which needs a registered VK application and an `access_token` to hold and rotate.
- Decision: the editor's video toolbar action and its cheat sheet are rewritten to insert and explain the captioned form for every service (T142) — the one-time fix ADR-035 already made possible but never surfaced. On top of that, inserting a recognised YouTube or Rutube link fetches that host's own public oEmbed title once, server-side, and offers it as the caption, still editable (T143, F66). A VK link keeps the manual form only — T142's improvement is what VK gets. The fetch is a plain `GET` from a synchronous (non-`async def`) route, so FastAPI runs it in its thread pool rather than blocking the event loop; nothing beyond the standard library is added to run it, so `httpx` — already a dependency, but a **dev**-only one for the test client — is not promoted to a runtime dependency for one feature. The fetch target is built through the same anchored, per-host patterns `_VIDEO_SERVICES` already constrains the embed URL with, so the endpoint can never be made to fetch an arbitrary host.
- Alternatives rejected: **fetch live on every render** — `render_markdown` runs on every keystroke's preview and on every published-page render; a network call there makes the site's own latency and uptime depend on YouTube's and Rutube's, and reintroduces exactly the kind of reader-facing external request F63 was written to rule out. **Register a VK application for `video.getOembed`** — a real integration: an app to register, a secret to hold and rotate, and a quota to watch, for one caption field on one of three services; rejected the way ADR-025's notifier and ADR-031's version line were, as not pulling its weight next to the manual form that already works. **Scrape a VK page's Open Graph tags instead of the API** — no documented contract, and VK's own pages already refused this session's fetch attempt, which is not a foundation to build a feature on.
- Consequences: a YouTube or Rutube link the owner pastes gets a real title without them typing one; a VK link still needs one typed, exactly as it does today, and the cheat sheet now says so. The server gains a narrow, admin-only, timeout-bound outbound dependency on two named hosts, active only while the owner is editing — not while a page is being served to anyone else. If VK ever grows a public oEmbed, or the owner decides the token is worth holding, this ADR is the thing to revisit.

## ADR-041 — Video embeds directly; the click facade is retired and `iframe` re-enters the allow-list

- Date: 2026-08-25
- Status: accepted, supersedes ADR-035
- Context: the owner opened an article and found the facade ADR-035 built cost *two* presses to actually watch a video — their own `<button>`, then YouTube's own paused thumbnail-and-title state inside the `<iframe>` that press built, because the browser will not honour `autoplay=1` on an iframe created by anything other than a direct user gesture consistently across hosts, and some monetised videos gate the real first frame behind their own click regardless. The owner asked for the ordinary embed every other site uses — an `<iframe>` present from the moment the page loads — having weighed and explicitly accepted, in chat, the cost that ADR-035 was written to avoid: every reader's browser now contacts the video host on page load, whether or not they ever watch.
- Decision: `_ProseRenderer.link_open`/`link_close`'s video branch (`app/services/markdown.py`) renders `<iframe class="prose-video__frame" src="…">…</iframe>` directly in place of the `<button class="prose-video__play">` facade; `ALLOWED_TAGS` and `ALLOWED_ATTRIBUTES` swap the `button` entry for an `iframe` one (`src`, `title`, `allow`, `allowfullscreen`, `loading`, `class`). The security invariant ADR-035 built for `button`'s `data-video` carries over unchanged onto `iframe.src`: nh3 filters attribute *names*, never values, so the only way this renderer ever emits that attribute is with a value already matched against `_VIDEO_SERVICES`'s anchored per-host patterns — an author's own hand-typed `<iframe>` still cannot survive as an element, because raw HTML stays disabled at the parser, exactly as a hand-typed `<button>` already could not. `app/static/js/video.js` (the click-to-build script) and its three `<script>` inclusions are deleted; `prose.css`'s `.prose-video__play`/`__glyph`/`__label` rules and their `forced-colors` treatment go with them, since a plain `<iframe>` needs no bespoke repaint of its own. CSP's `frame-src` already names the three hosts (ADR-035's own consequence) and needs no change. The poster-picture affordance — wrapping the video link around one of this site's own photos — is retired: a live iframe already shows the host's own current thumbnail before any interaction, so a second, separately-uploaded, potentially stale image drawn behind a button that no longer exists has nothing left to do; the picture's `title`, or its `alt` if it has none, still becomes the figure's `<figcaption>` (widened from `title`-only, so the author's words are not silently dropped now that the image itself no longer carries them to the page). ADR-038's excerpt fix (stripping the button's own label so it would not open a card's meta description) becomes dead code, not a still-needed guard, and is deleted along with the button it was about.
- Alternatives rejected: **keep the facade and try to make the reader's press actually autoplay** — tried conceptually and rejected: `autoplay=1` on a JS-built iframe is not honoured reliably across browsers and hosts regardless of the gesture that built it, and some monetised videos gate their real first frame behind a genuine click no matter how the iframe arrived, so the second press cannot be engineered away from the facade side. **Auto-fetch the host's own thumbnail (F66's oEmbed answer already has one) as a static poster instead of retiring the picture affordance** — pure duplication once the iframe itself shows that same thumbnail live, and it would be a second image fetched and cached for a state the reader sees for a moment at most. **Keep the poster picture rendering behind/beside the iframe** — two visuals for one video, which reads as broken rather than considered.
- Consequences: every reader's browser now requests the video host on page load for any article containing one, whether or not the reader ever watches — the exact cost ADR-035 named and rejected, now accepted by the owner directly. `iframe` is back in `ALLOWED_TAGS`; `secure-review` re-examined the renderer-closed-URL invariant specifically rather than taking the allow-list change on trust. The editor's own live preview now also reaches the video host on every htmx-triggered refresh while the owner edits a video paragraph, not only once on a manual click — admin-only traffic, not a reader's, and no CSP directive moves beyond what ADR-035 already opened. A video pasted with a poster picture before this iteration keeps its picture in the source (nothing rewrites the author's Markdown) but that picture stops rendering from the next time the article is served. If a genuinely single-click, no-request-until-interaction embed is ever wanted again, this ADR — not ADR-035 — is the one to revisit, since it record what was actually tried and why it did not reach that outcome from the facade side.

## ADR-042 — Private articles are shared by a secret token link, not a multi-user account system, and the token is read-only

- Date: 2026-08-29
- Status: accepted
- Context: the owner wants friends to read specific hidden articles (a trip plan, personal links) without registering on the site. `SPEC.md`'s own Non-goals already rule out "multi-user accounts or public registration" for the product as a whole; this iteration needed a concrete mechanism that respects that line while still letting a handful of named people in on specific content. The scale is explicitly small and stable — "a couple of friends look occasionally" — not a membership system with turnover.
- Decision: a new `shared_article` entity (separate from `post`) carries a `share_token` (`secrets.token_urlsafe(32)`, 256 bits of entropy). `GET /s/{share_token}` renders the article to anyone holding the link — a capability URL, not an identity. The token is **read-only in every case**: it is never accepted on any create/update/delete route (F68), and it is checked by the same structural sweep (F18, `tests/api/test_authz_sweep.py`) that covers every other mutating endpoint. Editing a shared article is reachable only through the single existing admin session (F15–F18), never through the link itself.
- Alternatives rejected: **a real multi-user account system** (one login per friend) — rejected as overbuilt for the actual need; it would require per-person credential issuance, password reset, and account lifecycle management for a use case that is "share a link in a chat message." **A bearer token that also grants edit rights to whoever holds the link** — rejected because a leaked link would become a leaked edit right with no way to revoke it from one person without breaking it for everyone else holding the same link; read-only removes that failure mode entirely — the worst a leaked link can do is let an unintended reader read one article. **Per-person access lists with individual revocation** — rejected for this round; see the two deferrals below, which are the direct costs of the token approach.
- Consequences: the owner **cannot revoke one specific person's access** without regenerating the token and breaking the link for everyone else who has it (F71) — accepted, because at this scale re-sending one new link costs nothing and the alternative (per-person accounts) costs a real system. There is **no view auditing** — the owner cannot see who opened a link, when, or how often — also accepted, and both of these are ordinary additive features to build later if the friend group grows past "a couple of people" or if the owner starts caring who read what; neither requires undoing this decision, only extending `shared_article` with per-recipient rows. A leaked link exposes exactly the one article it names, nothing else on the site, and never write access — the smallest blast radius a bearer link can have.

## ADR-043 — No rate limiter on the shared-article token route

- Date: 2026-08-29
- Status: accepted
- Context: F17 protects `/login` with a per-IP limiter because a username/password pair is short enough to be worth guessing. The shared-article route (ADR-042) is guarded by a `secrets.token_urlsafe(32)` value instead — 256 bits of entropy in the URL path itself, not a credential checked against a small keyspace. The question raised at intake was whether `/s/{token}` should reuse the same `login_attempt`-style limiter pattern that already exists in the codebase, purely because the pattern is there.
- Decision: no rate limiter on `GET /s/{token}`. The 404-for-anything-invalid behaviour (F67) is unconditional and does not itself get cheaper or more informative under repeated guessing — every miss looks identical to every other miss, so there is nothing a limiter would be protecting that entropy does not already close off computationally.
- Alternatives rejected: **reuse the `login_attempt` limiter pattern (F17) keyed by IP** — rejected because it protects against exactly the wrong threat model here. F17 exists because a password can be short and human-chosen; a 256-bit random token cannot be shortened by better guessing, so a limiter would add a second moving part (another table, another prune job, another way for a shared IP — a household, a café — to lock friends out of a link that was never guessed at) for a threat that is already computationally closed.
- Consequences: `/s/{token}` accepts requests at whatever rate they arrive, same as any other public GET route on the site (`/blog/{slug}`, `/photo/{slug}` carry no per-route limiter either). If the threat model ever changes — token length shortened, tokens made guessable, or generic bot traffic becomes a real cost concern independent of guessing — this ADR is the one to revisit, not F17's.

## ADR-044 — The shared-article editor gets the blog editor's formatting toolbar, not its image pipeline

- Date: 2026-09-01
- Status: accepted
- Context: I9, an owner request, asked the shared-article editor (`shared_editor.html`) to reuse the
  blog editor's interface — it shipped in T147 (I8) as title + body + preview only, with no
  `.md-toolbar` and no image upload. That trim was never its own decision; the template's own
  comment attributed it to ADR-042, but ADR-042 is about the token/capability-URL architecture, not
  the editor's feature set — T147's own impact map row had said "modelled on blog/editor.html —
  full editor with live preview". Reusing the toolbar (bold, italic, heading, list, quote, code,
  link, table, video, and F38's size-vocabulary cheat sheet) contradicts nothing already decided.
  Extending shared articles with an image upload pipeline is a different question: `shared_article`
  has no storage association today, and giving it one is a new capability with its own security
  surface, not a UI change.
- Decision: `shared_editor.html` gets the same `.md-toolbar` and cheat sheet as `blog/editor.html`,
  sourced from one shared definition rather than a second copy (T148). The photo action is the one
  button excluded — shared articles stay text/links/Markdown only, matching ADR-042's original
  framing ("a trip plan, personal links").
- Consequences: formatting parity between the two editors closes the gap the owner reported (no
  discoverable syntax help while writing a shared article). Photo upload for shared articles stays
  out of scope this round — an ordinary additive feature for later, the same shape ADR-042 already
  anticipated for per-recipient access lists and view auditing, not a reversal of anything here.
