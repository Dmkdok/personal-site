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
