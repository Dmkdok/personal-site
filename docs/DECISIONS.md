# Decisions

ADR-lite. All proposed on 2026-08-04, pending the approval gate.

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
- Consequence for ADR-012 that has to be said out loud: a deduplicated file lives in the directory of whatever uploaded it *first*. A frame shared by two articles physically sits under one of them. So `tar` of one article's directory may carry a file another article uses, and hand-deleting a group directory can break a page elsewhere. The application never removes a file something still references; the guarantee does not extend to editing the tree by hand. `make media-orphans` reports shared files so the owner can see which ones they are.

## ADR-014 — "Best view" is a native-width rendition, not the original file

- Date: 2026-08-08
- Status: accepted
- Context: the owner is a photographer who prepares his own frames, and says the current pipeline spoils them — `WEBP_QUALITY = 82` at a 2560 px ceiling. He wants the photography section shown at its best, article pictures capped around FullHD, and confirmed that "blog" and "articles" mean the same thing. The obvious reading, "serve the original as it was uploaded", breaks the one structural invariant this project has: `/media` is mounted over `derived/` **only**, which is what makes an original unreachable by URL as a matter of shape rather than of vigilance (ADR-012).
- Decision: the mount does not move and the originals stay unreachable. "Best" is delivered as a rendition at the original's **own width**, generated only when it is not already in the ladder, at quality 92 — visually indistinguishable from the source and still a file we produced, in the directory the web server is allowed to see. The scattered width tuples become three named profiles in `app.services.images`: `PHOTO` (640, 1600, 2560, native — quality 92), `PROSE` (640, 1280, 1920 — quality 85) and `COVER` (640, 1600 — quality 85). Nothing is ever upscaled. `MAX_UPLOAD_MB` goes to 50, the size the owner says he actually exports.
- Alternatives rejected: copying the original into `derived/` as a "full" rendition — that *is* publishing the original, with a rename to make it feel different. Serving `/media` through an application route or a rule-based Caddy matcher so `originals/` could be exposed selectively — trading a structural guarantee for a configuration one, on the single property that must not fail. A global quality bump without profiles — it would put a 92-quality 2560 px file behind every thumbnail in the grid for nothing.
- Consequences: the grid is unaffected, because `sizes` keeps it on the 640 rendition — the ≤120 KB thumbnail budget stands and is re-measured to prove it. The lightbox on a large display will now fetch a much bigger file, which is the point of the request; on a phone `sizes` still selects ~1600. A 6000 px upload produces a multi-megabyte rendition and costs real CPU once, at upload, in the background pool. Processing time and peak memory per file both rise with the 50 MB cap; `MAX_PIXELS` (added in Phase 6) is the backstop. If the weight ever becomes a problem the answer is a cap on the native rendition, not a return to re-compressing the owner's work.

## ADR-015 — The copyright line is stored whole, and stops knowing the year

- Date: 2026-08-08
- Status: accepted
- Context: `partials/site_links.html` renders `© {{ current_year }} {{ rights }}`, so only the name is editable and the year is assembled in the template. The owner wants to edit the line itself.
- Decision: `footer.rights` stores the entire line — `© 2026 Дмитрий Богданов` — and the template prints it verbatim. Existing rows are migrated by prefixing the symbol and the current year, so nothing visibly changes on the day it ships.
- Consequences: the year no longer advances by itself; on 1 January the owner edits one field, from the site, which is what "editable in full" means. `current_year` loses its only consumer. The value stays plain text with `value_html` blank, per `pages._put_value` — a name is not Markdown, and rendering it would invite a stray `*` into the footer.
