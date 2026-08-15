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
| List unreferenced media | `make media-orphans` |
| Delete unreferenced media | `make media-prune` |
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
BACKUP_DB_CONTAINER=<name> BACKUP_DIR=/mnt/x ./scripts/backup.sh
```

Writes `db-<timestamp>.sql.gz` (a `pg_dump --clean --if-exists`) and `media-<timestamp>.tar.gz`,
then prunes both older than 30 days.

The third form is the only difference between a development checkout and a host where the stack was
started by something other than this checkout. Unset, the script reaches the database with
`docker compose exec -T db`, exactly as it always has; set, it reaches the named container with
`docker exec -i` instead. Nothing else changes — same artefact names, same layout, same prune — so
`restore-check.sh` reads either run's output without knowing which produced it.

> Verified 2026-08-15 (T128): run from the host checkout and run again by container name against
> the same dev stack, both exit 0, artefact names identical to a pre-change run. The rehearsal below
> was then run over the container-mode pair — 4 albums, 24 photos, 84 files, nothing missing.

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

### On the appliance, where there is no checkout

The stack there is deployed from Portainer, so there is no compose project, no `make`, and no
`scripts/`. Two things cover it, and **both are needed** — neither is a substitute for the other.

**1. Snapshots, taken by the appliance itself.** Storage → Snapshots → Periodic Snapshot Tasks:

| Field | Value |
|---|---|
| Dataset | `tank/app_data/_dev_/portfolio` — **recursive**, so `media`, `pgdata`, `backups` and `logs` are all covered by one task |
| Schedule | Daily |
| Retention | 2 weeks |
| Naming schema | the default `auto-%Y-%m-%d_%H-%M` |
| Allow taking empty snapshots | on — otherwise a quiet day silently takes nothing |

A snapshot of a *running* Postgres is **crash-consistent, not clean**: the database will replay its
WAL and come up, but the snapshot restores only onto the same major version and the same on-disk
layout. That is why the dump below is not optional. Snapshots are also on the same pool as the
thing they protect — they survive a mistake, not a dead pool.

**2. A logical dump, one pasted command.** No checkout needed:

```bash
docker exec -i $(docker ps -qf name=portfolio.*db) pg_dump -U portfolio -d portfolio \
  --clean --if-exists | gzip > /mnt/tank/app_data/_dev_/portfolio/backups/db-$(date +%Y%m%d-%H%M%S).sql.gz
```

It writes into the `backups` dataset, which the snapshot task above then covers, and the artefact is
named exactly as `scripts/backup.sh` names it — so it can be carried to a machine that has a
checkout and fed straight to `make restore-check`.

**The three secrets are not in any of this, by design.** `SECRET_KEY`, `ADMIN_PASSWORD` and
`POSTGRES_PASSWORD` live only in the Portainer stack definition. They are not in the repository, not
in a file on the host, and not in a backup artefact. After a rebuild they are **regenerated, not
restored** — a new `SECRET_KEY` invalidates existing admin sessions, which costs one sign-in, and
`POSTGRES_PASSWORD` must be set to whatever the restored database expects, or set in both places at
once.

**What this deliberately is not.** No repository-owned schedule, no retention policy beyond the two
above, no manifest, no off-machine copy, and no restore rehearsal on the appliance. While the site
is in test mode on the NAS carrying disposable photographs, that is the accepted level (ADR-023);
the engineered form waits for the move to a dedicated server (ADR-024), and **R-01 stays open in
`docs/ROADMAP.md` until then.**

### Media maintenance

Deleting an article, a project, an album or a photograph now deletes the files that went with it,
and saving an article deletes the pictures you took out of the text. Nothing that another page
still uses is removed — the check reads the same rows the pages are built from (ADR-013). The same
frame uploaded twice is stored once, so a picture used by two articles is one file on disk.

Two consequences worth knowing before editing the media tree by hand:

* a deduplicated file physically lives in the directory of whatever uploaded it **first**, so
  `tar`-ing one article's directory can carry a file another article needs;
* the application will never delete a file something still references, but that guarantee does not
  extend to `rm`.

```bash
make media-orphans     # what nothing references, and what is shared. Deletes nothing.
make media-prune       # deletes exactly what the report listed
```

Both are safe to run repeatedly, and `--prune` re-checks the database before it unlinks anything.

---

## 6. Deploying

Two deployments out of one repository, differing in who terminates TLS and where the image comes
from. `CADDY_SITE_ADDRESS` is the whole switch: a domain and Caddy gets its own certificate, a bare
port and it speaks plain HTTP behind something that already has one. ADR-018 records why.

### 6.1 TrueNAS Scale behind a Keenetic router — the current target

The server holds no source and no configuration files. GitHub Actions runs the unit/API suite and
the lint gate on every push to `main`, and only then builds two images — the application, and
`caddy:2-alpine` with this repository's `Caddyfile` baked in — and pushes both to GHCR under one
tag, so the proxy configuration can never lag the templates it fronts. A red suite publishes nothing
and moves no tag, so `latest` can only point at a commit whose gates were green (F59, T127). The
Playwright suite is not in that gate; it runs on `v*` tags. Portainer is handed one compose file and
a set of variables.

Ports 80 and 443 on that host belong to the TrueNAS web interface and are not ours to take, which
is why the stack publishes `HTTP_PORT` (8080) instead. The router reaches it there.

**Once, before the first deploy:**

1. Datasets under `tank/app_data/_dev_/portfolio`: `media`, `pgdata`, `backups`, `logs` — beside
   `_dev_/raskladka`, following this appliance's own convention for the owner's projects. The image
   runs unprivileged as uid 1000, so `chown -R 1000:1000` the media **and** the logs datasets, or
   every upload fails on permissions and the log silently falls back to stdout (T126).
   `atime=off` on all four, `recordsize=16K` on `pgdata`. Note the parent carries
   NFSv4 ACLs, under which a plain `chown` is enough only because TrueNAS's default ACL gives
   `owner@` full control; verify by writing, not by reading the mode bits.
2. Portainer → Registries → add `ghcr.io`, username your GitHub name, password a personal access
   token with `read:packages`. The package is private because the repository is.
3. Portainer → Stacks → Add stack → Web editor. Paste `deploy/portainer-stack.yml` whole and fill
   in the variables listed in its header. `SECRET_KEY`, `ADMIN_PASSWORD` and `POSTGRES_PASSWORD`
   are generated here and exist nowhere else — not in the repository, not in a file on the host.
4. A reverse-proxy rule on the Keenetic pointing at `192.168.1.20:8080`.

**Every release after that:** push to `main`, wait for the `publish` workflow, then Redeploy the
stack in Portainer with *Re-pull image* enabled. Nothing on the server needs touching. To pin a
release rather than follow `main`, set `IMAGE_TAG` to a `sha-<short>` tag.

**External access, and why it is not simply "publish it in KeenDNS".** The router has a grey IP, so
KeenDNS runs in cloud mode, which proxies HTTP/HTTPS only and only on a fixed list of ports —
80, 81, 280, 591, 777, 5080, **8080**, 8090, 65080 for HTTP. `HTTP_PORT=8080` is on that list, and
that is not an accident to be optimised away later: move it to 8081 and the site becomes
unreachable from outside with no error that says so.

The obstacle is the certificate. KeenDNS publishes an internal web application under a **fourth**
level name — `portfolio.<router>.keenetic.pro` — while the certificate Keenetic issues covers
`*.keenetic.pro` and `keenetic.pro`, and a TLS wildcard matches exactly one label. Fourth-level
names therefore fail validation; Keenetic's own forum has this open and unresolved. A browser can
be clicked through, but link previews, Open Graph fetchers and crawlers cannot, and the admin
session cookie is `Secure`. Either publish under the router's own third-level name, where the
certificate is valid, or terminate TLS somewhere else — a Cloudflare Tunnel costs nothing, is
indifferent to a grey IP, carries a real certificate for a real domain and has no port list.

Two things the KeenDNS documentation does not state at all: whether the cloud proxy caps request
size, and whether it forwards `X-Forwarded-For`. Those are exactly checks 2 and 3 in §7, and they
are why those checks exist.

**Backups on this host are a Periodic Snapshot Task plus one pasted dump command** — `make backup`
wants a checkout and `make`, and there is neither. Both are specified in **§5, "On the appliance,
where there is no checkout"**, including why neither one alone is enough.

### 6.2 A server that faces the internet itself

Requirements: Docker with Compose v2, ports 80 and 443 reachable, and an A record for the domain
pointing at the server.

```bash
git clone <repo> portfolio && cd portfolio
cp .env.example .env      # SECRET_KEY, ADMIN_*, POSTGRES_PASSWORD, SITE_URL, CADDY_SITE_ADDRESS
mkdir -p data/media data/backups

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The production overlay: Caddy obtains and renews the certificate automatically, neither the app nor
the database publishes a host port, the code is baked into the image instead of bind-mounted, and
`ENV=production` makes cookies `Secure`. Expect first-run certificate issuance to need DNS to have
propagated. Then sign in at `https://<domain>/login`, change the seeded password, and add the cron
entry for `make backup`.

### Two ceilings that must agree, in both deployments

The upload limit is set in two places — `MAX_UPLOAD_MB` and `request_body max_size` in the
`Caddyfile`, currently 50 MB and 55 MB to leave room for the multipart envelope. **Move them
together.** With the proxy set lower, Caddy answers a bare 413 before the application is reached,
so the size the owner was promised is not the size he gets and no Russian message explains why —
and nothing local reproduces it, because dev runs without the proxy.

Behind the Keenetic there is now a third ceiling, the router's own, which this repository cannot
see or set. It is the first thing to suspect when a large upload fails there and nowhere else.

> **Brought up 2026-08-13** on TrueNAS 26.0.0-BETA.2 at `192.168.1.20`, Portainer stack
> `portfolio`, datasets under `tank/app_data/_dev_/portfolio`, reachable at
> `http://192.168.1.20:8080`. `db` and `web` healthy, public pages, `/healthz`, `sitemap.xml` and
> `robots.txt` all answering; migrations applied; Caddy's cache headers confirmed on the wire. The
> media dataset carries NFSv4 ACLs and the unprivileged container writes to it — proven by the
> `originals/` and `derived/` directories the application created there itself, owned by uid 1000.
>
> **Not yet done: anything requiring HTTPS.** Admin sign-in cannot be tested over the LAN address
> because `ENV=production` marks the session cookie `Secure` and a browser will not send it over
> `http://`. Nor, therefore, can the upload ceiling or the login throttle. Those three are §7's
> post-deploy checks and they wait on external access — see the KeenDNS constraint below.

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

### Post-deploy checks

Four things no local test reaches, in the order they are worth doing. All of them are the owner's:
they need the live route, the real router and a browser.

1. **Sign in over the public address.** `ENV=production` sets the session cookie `Secure`; the
   browser talks HTTPS to the router, so it should be sent — but only the live path proves it. If
   the login form accepts the password and returns you to the login form, this is why.
2. **Upload a file between 30 and 50 MB.** Exercises the client-side gate, the application's
   `MAX_UPLOAD_MB`, Caddy's `max_size` and the router's own undocumented ceiling in one go. The
   most likely thing to fail on first contact.
3. **The login throttle, from two different networks.** Six failed attempts from a phone on mobile
   data, then a real sign-in from a laptop. If the laptop is locked out too, the router is not
   forwarding `X-Forwarded-For`, every visitor is sharing one bucket, and `CADDY_TRUSTED_PROXIES`
   needs narrowing to the router's LAN address — or the header needs enabling on the router.
4. **A restore rehearsal from server artefacts.** Bring the newest dump and a media snapshot up as
   a separate stack and open a few album pages. `make restore-check` does this locally; on the
   appliance it is done by hand, because there is no checkout to run it from.

### Watching it while nobody is looking

The site runs unattended for weeks. Two things watch it, and it is worth knowing exactly what each
one does and does not cover.

**The container healthcheck** already in `deploy/portainer-stack.yml` polls `/healthz` every 10
seconds from *inside* the container. It is what `depends_on: service_healthy` reads, and Docker
restarts nothing on its own — so it tells Portainer the container is unwell and tells the owner
nothing at all.

**The external check** is the one that reaches a human. It lives on the appliance, outside the
stack, so a stack that will not come up at all is still noticed. System Settings → Advanced → Cron
Jobs:

| Field | Value |
|---|---|
| Description | `portfolio /healthz` |
| Command | `curl --fail --silent --show-error --max-time 10 --output /dev/null http://localhost:8080/healthz` |
| Run As User | `root` |
| Schedule | every 10 minutes |
| Hide Standard Output | **on** — a healthy run must be silent, or this mails every 10 minutes and is muted within a day |
| Hide Standard Error | **off** — this is the whole point: curl writes the failure here |

It polls the published `HTTP_PORT`, so it exercises the router-facing path — Caddy *and* the
application — rather than the application alone. A stopped `web` answers 502 through Caddy and
`--fail` turns that into a non-zero exit and a line on stderr; a stopped stack answers nothing and
`--max-time` turns that into the same.

This needs the appliance's email alerts configured (System Settings → Alert Settings → Email), or
the failure exists only in the job's run history, which nobody reads. That is a weaker signal, not
no signal — but it is not what "something watches it" is supposed to mean.

**Verify it by breaking it, not by watching it pass.** Stop the `web` container in Portainer, wait
for the next run, and confirm the failure arrives. Then start it again and confirm the noise stops.
A check that has only ever been seen green is a check nobody has tested.

**There is no notifier for a 500 or a failed photograph, and there is not meant to be yet.**
ADR-025 records why: the owner wants a Telegram bot for this and wants it on a dedicated server, not
on the appliance. Until then the place to look is the log — `app.log` on the `logs` dataset, put
there by T126 (F58), readable over the share without a Docker client. A photograph that fails now
says so on its own tile and offers a retry (T130), so the two things most likely to go wrong are
both visible without a terminal.

---

## 8. Known gaps

1. **The site runs on the LAN but is not published** (§6.1). Everything that can be verified over
   `http://192.168.1.20:8080` is verified; sign-in, the upload ceiling and the login throttle
   cannot be, because all three need working HTTPS. The KeenDNS certificate constraint in §6.1 is
   the decision blocking that.
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
