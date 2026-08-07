# Handoff

Everything needed to run, edit, back up and deploy this site. Written 2026-08-07.

The site is a personal portfolio with four public sections — Главная, Разработка, Фото, Блог —
and no separate admin area: the owner signs in and edits the public pages in place.

---

## 1. What it is made of

| Piece | Choice |
|---|---|
| Application | FastAPI 0.141, server-rendered Jinja2 templates |
| Interactivity | htmx 2.0, vendored — no Node build, no bundler, no `npm install` |
| Database | PostgreSQL 18, with its own full-text search (`russian` configuration) |
| Images | Pillow 12.3 — WebP derivatives at 640 / 1600 / 2560 px |
| Styling | Hand-written CSS with design tokens; both themes from one `light-dark()` file |
| Auth | Argon2id, server-side sessions, token rotation on logout |
| Runtime | Docker Compose; Caddy terminates TLS in production |

There is no build step for the frontend. Editing a template, a stylesheet or a Python file and
reloading the page is the whole loop.

---

## 2. Running it locally

```bash
cp .env.example .env      # then edit — see §3
make up                   # → http://localhost:8000
```

`make up` builds if needed, starts Postgres and the app, waits for the database healthcheck, and
runs migrations on startup. Admin sign-in is at `/login`; it is deliberately not linked from the
navigation.

| Task | Command |
|---|---|
| Start | `make up` |
| Stop (photographs untouched) | `make down` |
| Follow logs | `make logs` |
| Shell in the container | `make shell` |
| psql session | `make psql` |
| Apply migrations | `make migrate` |
| New migration | `make revision m="add table"` |
| Unit + API tests | `make test` |
| End-to-end tests | `make e2e` |
| Lint + format check | `make lint` |
| Autofix + format | `make fmt` |
| Backup | `make backup` |
| Drop the database volume (media survives) | `make clean` |

On Windows, `run.ps1` wraps the same targets for PowerShell.

### Two environment traps that have cost time here

- **The Compose project is named `dmkdok-portfolio`, and must stay that way.** A bare `portfolio`
  collides with a different stack on the owner's machine at `C:\Users\dmkdok\AI\Portfolio`, and
  `docker compose up` under the colliding name recreated *that* project's containers once already.
- **Do not run `pytest` for `tests/` on the Windows host.** Starlette's `TestClient` hangs there
  before collection. That is why the suite runs in a container (ADR-008). `e2e/` is the exception:
  it drives a real browser over HTTP and runs from the host.

---

## 3. Configuration

`.env`, copied from `.env.example`. The application refuses to start if the first three are absent.

| Variable | Meaning |
|---|---|
| `SECRET_KEY` | Session signing key. Generate a fresh one per environment. |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Seeded into the database on first startup. The plaintext is never logged and never stored — only the Argon2id hash. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Database credentials. |
| `MEDIA_ROOT` | Where photographs live *inside the container* — `/data/media`. |
| `MEDIA_HOST_DIR` | Where that directory sits on the **host**. Defaults to `./data/media`. On a server point it outside the checkout — `/srv/portfolio/media`, or a mounted block device — so re-cloning the repository or `git clean` cannot take the originals with it. Backups read the same directory. |
| `ENV` | `local` or `production`. `production` makes session cookies `Secure`. |
| `SITE_URL` | Absolute base for canonical tags and `sitemap.xml`. |
| `SITE_DOMAIN` | Production only. The hostname Caddy obtains a certificate for. |

Changing `ADMIN_PASSWORD` in `.env` and restarting updates the stored hash.

---

## 4. Editing content

Sign in at `/login`; an admin bar appears and every page grows edit controls. There is no CMS
screen to learn — you edit where the content is.

**Photographs.** `/photo` → «Новый альбом» → title and caption → the album page opens on its drop
zone. Drop or pick up to 50 files at once, 25 MB each. Each upload gets a UUID filename, is checked
by extension, MIME type, magic bytes and a decode attempt, then processed in the background while
you keep working; the grid polls until every photo reports ready and then stops polling. Per photo
you can set alt text, make it the cover, reorder by drag or by the ↑/↓ buttons, and delete — which
removes the derivatives and the original from disk too. An album stays invisible to visitors until
you publish it. If the server restarts mid-processing, the startup sweep re-queues anything left
pending and fails anything whose original has vanished.

**Articles.** `/blog` → «Новая статья» → the editor has a Markdown pane and a live preview rendered
through the *same* function as the published page, so the preview cannot drift. Raw HTML is
disabled and the output is sanitised against an allow-list, so pasted `<script>` or `onerror=`
simply disappears. Images can be dropped into the editor, pasted, or picked with the toolbar
button, and are inserted at the cursor. Drafts are 404 for visitors and marked «черновик» for you.
Publishing sets `published_at`; unpublishing puts it back to a draft.

*Sizing a picture inside an article.* A picture on a line of its own becomes a figure and can claim
one of three widths — the disclosure under the editor's text area shows all of them:

| You write | You get |
|---|---|
| `![описание](адрес)` | the width of the text column |
| `![описание](адрес){.wide}` | wider than the column, breaking out on both sides |
| `![описание](адрес){.full}` | the full content column |
| `![описание](адрес "подпись")` | the same, with «подпись» underneath as a caption |

Nothing else is accepted: an unknown word in the braces is dropped rather than passed through, and
there is no way to write a raw width or a `style` (ADR-011).

**Contact links and the copyright line.** Signed in, «Изменить ссылки» at the footer edits the four
social links and the name in the copyright. The footer and the home page's contact chips read the
same five values, so one edit changes both; clearing a link removes it from both. Only `http` and
`https` addresses are accepted (F39).

**Projects.** `/dev` → cards created and edited inline: title, summary, optional Markdown body,
repository and demo links, tech stack, optional cover. Drag to reorder, toggle to publish. A
project with no long description links straight to its repository.

**Search.** The field in the navigation capsule searches articles, projects and albums together
with Russian stemming — «эльбрусе» finds «Эльбрус». Drafts and unpublished albums never appear for
visitors.

---

## 5. Backups and restore

```bash
make backup                       # → ./data/backups
BACKUP_DIR=/mnt/x ./scripts/backup.sh
```

Writes `db-<timestamp>.sql.gz` (a `pg_dump --clean --if-exists`) and `media-<timestamp>.tar.gz`,
then prunes both older than 30 days. Run it from a cron entry on the server.

**Restore.** The database dump is self-cleaning, so it can be replayed over a running database:

```bash
gunzip -c data/backups/db-20260807-030000.sql.gz | docker compose exec -T db \
  psql -U portfolio -d portfolio

tar -xzf data/backups/media-20260807-030000.tar.gz -C ./data
docker compose restart web
```

Media and database must come from the same run, or photo rows will point at files that are not
there. Photos already survive `docker compose down` followed by `up` — they are on a host bind
mount, not in a volume — and `make clean` deletes only the database volume.

**Rehearse it without touching anything live:**

```bash
make restore-check          # newest pair in ./data/backups
```

It replays the dump into a scratch database beside the real one, unpacks the media archive into a
temporary directory, and then checks that every media path in the restored rows is actually present
in the archive — the check that catches a database and a media archive taken from two different
runs, which is the failure mode that matters. The scratch database is dropped afterwards.

> Rehearsed 2026-08-07 and passed: 13 rows restored, 44 files, nothing missing (T086).

---

## 6. Deploying to a VPS

Requirements: Docker with Compose v2, ports 80 and 443 reachable, and an A record for
`SITE_DOMAIN` pointing at the server.

```bash
git clone <repo> portfolio && cd portfolio
cp .env.example .env      # set SECRET_KEY, ADMIN_*, POSTGRES_PASSWORD, SITE_URL, SITE_DOMAIN
mkdir -p data/media data/backups

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The production overlay: Caddy obtains and renews the certificate automatically, neither the app nor
the database publishes a host port, the code is baked into the image instead of bind-mounted,
`ENV=production` makes cookies `Secure`, and Caddy caches `/media` hard (content-addressed names)
and `/static` for a week. The upload ceiling is set in two places that must agree — `MAX_UPLOAD_MB`
in `.env` and `request_body max_size` in the `Caddyfile`, currently 25 MB and 30 MB to leave room
for the multipart envelope.

Then: sign in at `https://<domain>/login`, change the seeded password, and add the cron entry for
`make backup`.

> **Not yet deployed.** The overlay and `Caddyfile` are written and validate, but this stack has
> never been brought up on a real server (T074). Expect first-run certificate issuance to need
> DNS to have propagated.

---

## 7. Verification status

Last run 2026-08-07, end of the second session, on the owner's machine.

| Gate | Command | Result |
|---|---|---|
| Unit + API | `docker compose run --rm tests` | **193 passed**, exit 0 |
| End-to-end | `uv run pytest e2e` | **36 passed**, exit 0 |
| Six launch flows | `uv run pytest e2e -m launch_flow` | **6 passed**, exit 0 |
| Lint | `uv run ruff check .` | clean |
| Format | `uv run ruff format --check .` | clean |

Beware `-q` is set twice, so a passing run prints dots and no summary line. **Read the exit code.**
Never pipe a test run through `tail` or `grep` — you get the pipe's status and a red suite reads as
green.

Accessibility and performance evidence is committed as JSON under `docs/qa/`:
`contrast-light.json`, `contrast-dark.json`, `focus-sweep.json`, `target-size-360px.json`,
`perf-50.json`, and a screenshot of the 50-photo grid.

Measured on a 50-photo album at 1440×900: CLS 0.00023, LCP 168 ms, heaviest thumbnail 96 KB, all 50
images carrying `loading="lazy"`, intrinsic dimensions, `srcset` and alt text.

---

## 8. Known gaps

1. **The production stack has never been deployed** (§6). The highest-value thing to do next.
2. **A picture inside an article shifts the page as it loads.** Measured 2026-08-07: an article with
   two pictures scores CLS 0.119 against this project's 0.02 budget, on a 400 kB/s cold load. They
   are lazy-loaded and carry no `width`/`height`, so nothing reserves their height. The album grid
   is unaffected (`docs/qa/perf-50.json`); this is the article page only. The renderer already
   inspects each rendition when it builds the `srcset` — reading the dimensions there is the fix.
3. **Touch targets follow WCAG 2.2 AA 2.5.8 (24 px), not the 44 px that SPEC F12 originally
   asked for.** 54 controls at 360 px width sit between the two — the icon buttons at 34×34, footer
   links from 17×17, buttons 36 px tall. None breach the accessibility standard. Waived
   deliberately in ADR-010; revisit if the site gains finger-driven surfaces.
4. **The nav search field's focus ring comes from its wrapping label** via `:focus-within` rather
   than its own outline, and measures 1.83:1 against the field. It passes AA and every one of the
   69 focus stops has *some* visible indicator, but this one is weaker than the rest.
5. **Two minor labelling gaps**: the upload queue `<ul>` has no accessible name (its caption is a
   loose `<p>` above it), and the lightbox position indicator is a bare `<p>` with no role.
6. **Draft Russian copy.** The home page and section intros were written as placeholders and
   accepted as such; they are the owner's to rewrite.

---

## 9. Where to look in the code

```
app/
  main.py            app factory, middleware (CSRF, security headers), lifespan, admin seeding
  config.py          pydantic-settings; fails loudly on missing secrets
  db.py              engine, session factory, declarative base
  security.py        Argon2id, sessions, CSRF, rate limiting
  deps.py            OptionalAdmin / CurrentAdmin dependencies
  background.py      the two-thread pool and the startup recovery hook
  templating.py      render() — always use it; injects is_admin, CSRF, globals
  models/            SQLAlchemy models, one per table
  routers/           photos.py, blog.py, projects.py, pages.py, search.py, seo.py, auth.py
  services/          images.py, markdown.py, slugs.py, search.py
  templates/         base.html, partials/, and one directory per section
  static/            css/ (tokens.css first), js/, fonts/
  i18n/ru/           one JSON per area — no user-visible string lives in a template
migrations/          Alembic; the whole schema is one revision
scripts/             backup.sh, restore-check.sh, migrate_media.py
tests/               unit + API suite (container only)
e2e/                 Playwright (host only)
docs/                SPEC, PLAN, TASKS, CONVENTIONS, DECISIONS, STATUS, qa/
```

**Where the pictures are.** Everything one album, article or project owns lives in a directory of
its own: `<originals|derived>/<photos|posts|projects>/<id>-<slug>/`. Only `derived/` is mounted at
`/media`, so an original cannot be reached by a URL — that is a property of the layout, not a rule
someone has to remember. `scripts/migrate_media.py` moved the old year-based tree and is safe to
re-run; it reports files nothing references rather than deleting them (ADR-012).

Read `docs/CONVENTIONS.md` before writing code here. It records the rules the modules rely on and
a short list of Jinja and CSP traps that have already cost this project time — two of them were
still live in the photo templates as of 2026-08-06 and caused 17 test failures.

`docs/DECISIONS.md` holds ADR-001..010: why FastAPI over an SPA, why Postgres FTS instead of a
search service, why images are processed in-process, why the tests run in a container, and why the
CSP stayed strict.
