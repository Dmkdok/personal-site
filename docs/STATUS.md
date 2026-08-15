# Status

phase: review
approved: true
approved_at: 2026-08-04

## Baseline I3

Recorded 2026-08-15 on branch `iteration/I3-operations`, cut from `iteration/I2-pagination-media-phaseb`
at `8c75582` (the I2 close). Every command below was run in this session, on this tree.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **271 passed**, exit 0 |
| e2e | `uv run pytest e2e` | **80 passed + 1 error**, exit 1 · then **81 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | clean, 127 files |

**The baseline is not green, and the failure is inherited.** Two full e2e runs, twenty minutes
apart, on identical code: the first ended `80 passed, 1 error`, the second `81 passed, exit 0`. The
error is a fixture setup, not an assertion — a photograph upload answered **500**:

```
File "/app/app/routers/photos.py", line 799, in photo_upload
    _assign_renditions(photo, images.stored_from_asset(known))
File "/app/app/routers/photos.py", line 376, in _assign_renditions
    photo.thumb_path = ordered[0]
IndexError: list index out of range
```

The deduplication branch reads the disk **twice**. `images.find_asset` globs the renditions and
drops the row if they have gone — its docstring says why: "Reusing it would hand the caller URLs
that 404." Twelve lines later `images.stored_from_asset` globs the same directory again, and between
the two globs the files were removed. `_assign_renditions` then takes `ordered[0]` without checking
that the list is non-empty, although its own docstring promises "Every case still has to leave a
servable thumbnail." Taken into I3 as **T125**, first task.

**It predates I2.** I2's hunks in `app/services/images.py` are HEIC only (the magic table, the brand
list, `store_original`'s extension map); its hunks in `app/routers/photos.py` stop at line ~632,
and the upload route begins at 767. `find_asset`, `missing_rungs`, `stored_from_asset` and
`_assign_renditions` are untouched by the iteration — they are M9 code from 2026-08-08.

**Note for whoever reads the I2 close:** commit `8c75582` records the e2e gate as "81 passed exit 0",
which was true of the run it was written from. It is not true of every run. T124 fixed two *other*
intermittent e2e checks (both sampling a value in the same tick as the event that changes it); this
one is a third, in the application rather than in the test, and was not known when that commit was
written.

Progress:
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred)
- [x] 2 impact map written
- [x] 3 docs amended (SPEC F57–F60 + Operations and risk 6, ADR-023…026, TASKS M15)
- [x] 3b delta re-cut on the owner's instruction — eight tasks to five, R-01 reduced to the
      appliance's own snapshots plus one command (ADR-023/024), the declined notifier replaced by
      the log file on disk (ADR-025)
- [x] **GATE approved by the owner — «утверждаю», 2026-08-15**
- [x] 4 implementation — T125, T130, T126 complete; T127, T128, T129 written and committed, each
      with a half only the owner can run
- [x] 5 verification green, baseline suites still green — unit/API **277** exit 0, e2e **81** exit 0
      twice, lint and format clean over 53 files
- [x] 6 review — `docs/REVIEW.md` run 5, PASS on what was run, and it says plainly that it is a
      self-review rather than an independent one
- [ ] 7 closed — **M15 cannot be ticked**: three tasks have owner-only halves outstanding

### I3 close, 2026-08-15 — unit/API **277**, e2e **81 twice**, lint and format clean

Five tasks implemented in the ordered sequence, each with its check watched failing first:

- **T130** (`6867154`) — `process_photo` committed `PROCESSING` and then ran four more steps
  *outside* its `try`. A raise in any of them was swallowed by `submit_with_session`, whose rollback
  cannot undo a commit that already happened, so the row spun until the next restart with no retry
  offered. The render-and-record sequence moved inside the guard; each handler rolls back before
  `_fail` writes, so a raise from the database work cannot make `_fail`'s own commit raise in turn.
  Two tests, one per named window. `recover_stuck_photos` deliberately untouched.
- **T126** (`0ec22c1`) — `LOG_DIR`, empty by default, adds a `RotatingFileHandler` (5 MB × 4)
  *beside* the stdout stream. An unwritable path warns and starts anyway. Both deployment files
  gained a `logs` mount on `web` and an explicit `max-size`/`max-file` on every service; both render
  under `docker compose config`. `docker-compose.yml` untouched, as the DoD required.
- **T127** (`729fce3`) — `publish` now declares `needs: tests`. **Not ticked.**
- **T128 + T129** (`66455ca`) — `BACKUP_DB_CONTAINER` on `backup.sh`, run both ways with the
  artefact names diffed and a restore rehearsed; `HANDOFF.md` §5 and §7 rewritten. **Not ticked.**

**Three tasks are not done and were not ticked**, because their remaining halves cannot be run from
a session: T127's proof needs a push to GitHub, T128's snapshot task and T129's external check are
created in the TrueNAS interface. The written-but-never-run tick is the T073 mistake this project
already paid for once in T086.

## Baseline I2

Recorded 2026-08-14 on branch `iteration/I2-pagination-media-phaseb`, cut from `main` at `dfc8f92`
(the roadmap commit; `8ec69a5` plus `docs/ROADMAP.md`, which had been left uncommitted).

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **233 passed**, exit 0 |
| e2e | `uv run pytest e2e` | **60 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | 120 files already formatted |

Green baseline; nothing inherited. **The 226 in the I1 close below is stale** — the tree collects 233
unit/API tests (counted with `--collect-only`, not read off a summary line). The suite grew after
that close; the number here is the one to beat.

Progress:
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred)
- [x] 2 impact map written
- [x] 3 docs amended (SPEC F3/F8/F10/F24 + F51–F56, ADR-019…022, TASKS M11–M13)
- [x] GATE approved by the owner — «утверждаю», 2026-08-14
- [x] 4 implementation — M11 (T107–T116), M12 (T117–T120, T123), M13 (T121–T122), M14 (T124)
- [x] 5 verification green, baseline suites still green — and it earned a defect, T123
- [x] 6 review clean (`docs/REVIEW.md` run 4, PASS; one High and five Mediums found and fixed)
- [x] 7 closed (STATUS rewritten, milestones ticked)

### M11 closed 2026-08-15 — unit/API **237**, e2e **77**, lint and format clean

Ten tasks, ten commits, every one with a check that was watched failing first. Three of the ten
turned out to be about the audit rather than about the code, and those corrections are the part
worth reading — all three are written up in `docs/iterations/I2-pagination-media-phaseb.md`:

- **F-015** — the prescribed fix was half a fix on the wrong element. `padding-block-end` had to go
  on `.page` (the footer is `.page__main`'s sibling and carries the very button the audit found
  under the bar), and document length does nothing for focus on its own: Chromium scrolls a
  tabbed-to control to the viewport edge, which is *under* the bar, so `scroll-padding-block-end` on
  `:root` is the half that satisfies 2.4.11. Both halves watched failing alone.
- **F-011** — the overhang does not reproduce. `backdrop-filter` on the capsule already made it a
  containing block; the menu has been aligned all along. `position: relative` is kept so that
  alignment does not depend on a visual effect, and the new test measures the result, not the
  mechanism.
- **F-012** — already closed since `2a986ca` (2026-08-08), with three unit tests. The audit was
  written afterwards and did not check.

One thing is genuinely outstanding: **the forced-colors pass on a real Windows contrast theme.**
The automated pass under Chromium's emulation is done and recorded; the four manual steps in Edge
are written down in `docs/qa/forced-colors.md` and are the owner's to run.

### M12, M13 and M14 closed 2026-08-15 — iteration I2 is complete

`/blog` and `/photo` render a page instead of a table (`/photo` for the visitor only, ADR-022), the
search page says how much it found and offers the rest, and a `.heic` straight off the owner's phone
uploads, converts and appears in the album. Fourteen tasks across three milestones, then a fourteenth
milestone for what the review found.

**Two defects were found after their tasks were ticked, and both are worth carrying forward.**

- **T123 — «Показать ещё» took the caret with it.** Found in phase 5 by a test written after T120
  was closed. The button lives inside the element it replaces, so pressing it deletes it, and htmx
  restores focus only to something that still exists under the same id. The next Tab restarted at
  the top of the document. Fixed with an id on the button, a `tabindex` and a one-shot
  `data-autofocus` on the section, and `ui.js` now clears that attribute once it has honoured it.
- **T124 — the same control was permanently dead above 200 hits.** Found by *both* reviewers
  independently. It asked for `shown + 12` while the route clamps at `MAX_GROUP_LIMIT`, and
  `has_more` stays true above the cap, so every press returned the same section byte for byte. The
  shape is the lesson: **two numbers that must agree, written in two places, one of them a literal
  in a template.** T117 had already put page size in one constant; search grew its own step and its
  own ceiling and obeyed neither.

**Phase 6 was two independent reviewers, neither of which wrote the code** — one on completeness
against the ticked task list, one carrying the security and interface checklists against a running
instance. Verdict PASS, one High and five Mediums, all fixed in T124, everything watched red first.
Full record: run 4 in `docs/REVIEW.md`. What is carried rather than fixed is listed there too, with
reasons — the honest ones being that T112's test cannot fail (`backdrop-filter` already did the work
`position: relative` was added for), and that the counts wrap a full entity `SELECT` in a subquery
so that one predicate serves both the count and the list.

**Two of the checks written this session were themselves wrong**, both sampling a value in the same
tick as the event that changes it — one raced `htmx:afterSettle`, one read a transitioned
`background-color` mid-animation. Both passed once and failed once against identical code. Anything
an animation or a settle step touches must be asserted with a retry, never with a single read.

**`docs/UI-AUDIT.md` now carries a closure register at the top**, because after this iteration the
findings below it would otherwise read as thirteen open P2s. The findings themselves are untouched:
they were an audit, not a backlog, and editing them in place would destroy the record.

## Resume here

**Branch `iteration/I3-operations`, cut from `8c75582` (the I2 close). It is not merged and not
pushed** — `main` itself is one commit ahead of `origin/main` (the roadmap, `dfc8f92`). The remote
is `origin` → `https://github.com/Dmkdok/personal-site.git`. The dev stack (`db`, `web`) is up;
`docker compose down` stops it. Docker Desktop is not always running on this host — start it and
wait for `docker info` before the first suite.

**Two traps this session hit, both cheap to avoid.** A full e2e run started immediately after
`docker compose restart web` fails all 81 at fixture setup, because the site is not answering yet —
wait for `/healthz` first. And Git Bash rewrites container-absolute paths on this host, so
`docker compose run -e LOG_DIR=/tmp/x` arrives inside the container as `C:/Users/...`; prefix the
command with `MSYS_NO_PATHCONV=1`. The same conversion makes `tar` treat a `C:/...` `BACKUP_DIR` as
a remote host and fail — give `scripts/backup.sh` a POSIX-relative path.

**Iteration I3's code is finished. The iteration is not, and M15 is not ticked.** Its page —
intake, the re-cut, the impact map, both pipeline defects and the exit criteria — is
**`docs/iterations/I3-operations.md`**. Milestone **M15** in `docs/TASKS.md`, six tasks:

| | | State |
|---|---|---|
| **T125** | the dedup race: an upload could answer 500 | **done**, `4255ec4` |
| **T130** | a photo failing *after* the render spins instead of failing | **done**, `6867154` |
| **T126** | the log as a file on disk + log ceilings | **done**, `0ec22c1` |
| **T127** | the suite gates the published image | code done `729fce3` — **needs a push to prove** |
| **T128** | a dump that runs on the server + snapshot task | script + docs done `66455ca` — **needs the snapshot task** |
| **T129** | an external check on `/healthz` | docs done `66455ca` — **needs the cron job** |

**Gates at the close (2026-08-15):** unit/API **277** exit 0, e2e **81 passed exit 0 twice
consecutively**, six launch flows 6 passed, lint and format clean over 53 files. The baseline's
intermittent 500 did not recur, and neither did the unexplained login failure recorded below.

**What is left is the owner's and only the owner's — do not tick any of it from a session.**

1. **T127** — push a scratch branch, dispatch the workflow with a deliberately red commit and watch
   `publish` skip, then with a green one and watch it build. `gh workflow run publish.yml --ref
   <branch>`. A scratch branch does not move `latest`: the `latest` tag is enabled only on the
   default branch, so a dispatched green run publishes `sha-` tags only.
2. **T128** — create the Periodic Snapshot Task in the TrueNAS interface. The dataset, schedule and
   retention are specified in `docs/HANDOFF.md` §5; paste the resulting listing into the iteration
   page.
3. **T129** — create the cron job in `docs/HANDOFF.md` §7 and **verify it by stopping `web`**, not
   by watching it go green.
4. **T126's last mile** — create the `logs` dataset (`chown 1000:1000`), set `LOGS_HOST_DIR` in
   Portainer, redeploy, then open `app.log` over the share and grep it for every value in the stack's
   variables. `LOGS_HOST_DIR` is a **required** variable in `deploy/portainer-stack.yml`: the stack
   will refuse to deploy until it is set.

**Merging is the owner's call and the consequence is now different from what it was.** A push to
`main` runs `publish`, which since T127 runs the suite and the lint gate first and builds nothing if
they fail. `latest` still follows `main` — but only a green `main`. The sane order is still to prove
T127 on a scratch branch before trusting it.

**Iteration I2 is complete.** `docs/TASKS.md` has no unticked line, M11 through M14. Its page is
**`docs/iterations/I2-pagination-media-phaseb.md`**; the review is run 4 in `docs/REVIEW.md`.

**One intermittent was seen and is not explained.** In one full e2e run of three, the
`admin_storage_state` fixture failed at setup: the login POSTed and answered `303`, and the page it
redirected to came back anonymous — no admin bar, so the session cookie was issued and then not
honoured. It did not recur on the next run, and the same fixture succeeds fifteen-odd times in every
run. Two runs of that batch also had the app restarting underneath them, because a `git stash` cycle
of `app/**` (used to watch a test go red) trips uvicorn's `WatchFiles` reloader — **so do that with
the stack down, or expect `ERR_EMPTY_RESPONSE` in the middle of a suite.** Whether the login failure
was the same disturbance or something in `end_session`'s token rotation is genuinely unknown. It is
the first thing to chase if it shows up again; there is nothing to fix until it does.

**The audit is now half finished, deliberately, and it says so itself.** Phase A (P1) closed in I1;
Phase B (P2) closed in I2, with F-016 closed as not-a-defect by ADR-020. Seven P3 findings
(F-019…F-022, F-024…F-026) remain open, deferred by ADR-017. `docs/UI-AUDIT.md` carries the register
at the top — that is the only edit ever made to it, and the findings below it are untouched.

## The deployment, built this session

A server appeared: **TrueNAS Scale at `192.168.1.20`**, Portainer from its Apps catalogue on
`https://192.168.1.20:31015` (self-signed), behind a **Keenetic** router on a grey IP. Its own web
interface holds `:5000` — and also `:80` and `:443`, which is the first thing that broke the old
plan. **ADR-018** records the shape and the four rejected alternatives.

What the arrangement is: GitHub Actions builds **two** images and pushes them to GHCR under one tag
— the application, and `caddy:2-alpine` with this repository's `Caddyfile` baked in. Portainer gets
one self-contained compose file and a set of variables; the server stores no source and no config
files. The router terminates TLS, so `CADDY_SITE_ADDRESS` is a bare port and Caddy asks for no
certificate. Media and the Postgres data directory bind-mount to ZFS datasets.

| File | What it is |
|---|---|
| `deploy/portainer-stack.yml` | the whole server side — pasted into Portainer, variables documented in its header |
| `.github/workflows/publish.yml` | builds and pushes both images to GHCR on push to `main` |
| `Dockerfile.caddy` | the proxy with the Caddyfile baked in; `caddy validate` runs at build time |
| `Caddyfile` | site address and trusted-proxy list are now variables — one file, both deployments |
| `docs/HANDOFF.md` §6 | rewritten: §6.1 this deployment, §6.2 a server that faces the internet |

**`ASSET_VERSION` is fixed** — the defect the last handoff left for the owner to decide. `static_url`
now keys `?v=` on the requested file's own mtime instead of `templating.py`'s, which moved for
neither a restart nor a stylesheet edit. It became load-bearing rather than theoretical the moment a
proxy with `max-age=604800` entered the picture. Seven tests in `tests/unit/test_static_url.py` hold
it, including the exact shape of the old bug (two assets sharing one version).

**Also:** `COPY scripts ./scripts` in the `Dockerfile`. `scripts/` was never in the image and the
prod overlay never mounted it, so `media_orphans.py` — documented in `docs/HANDOFF.md` §5 as the way
to maintain the media tree — did not exist on a deployed site. Only development bind-mounted it,
which is why nobody noticed.

**Gates, on the final tree:** unit/API **233** passed exit 0 (226 before, +7 new), e2e **60** passed
exit 0, `ruff check` and `ruff format --check` clean. Separately: `caddy validate` passes both for a
bare port and for a domain, `docker compose config` renders the stack and refuses it when a secret
is missing, and `Dockerfile.caddy` builds.

## Published, 2026-08-13

**`https://profile.dmkdok.crazedns.ru:8443/`** — KeenDNS cloud mode, on the owner's own KeenDNS
domain `dmkdok.crazedns.ru` rather than `keenetic.pro`. `profile` is a fourth-level name published
from the router's «доступ к веб-приложениям» form and pointed at `192.168.1.20:8080`. Port **8443**
because a VPN on the same router holds 443; 8443 is on KeenDNS's allowed HTTPS list, as is the 8080
the stack publishes, so both ends of the path are legal by luck and should stay put.

**Immediately outstanding: `SITE_URL` is still `http://192.168.1.20:8080`.** Canonical tags, Open
Graph and `sitemap.xml` therefore advertise a LAN address to the public internet — confirmed by
reading the published page. Fix is one variable in Portainer → Stacks → portfolio → Editor plus a
redeploy; it changes no code.

### Tested against the public URL, 2026-08-13

| Check | Result |
|---|---|
| TLS, strict verification | **passes** — Let's Encrypt, SAN `*.dmkdok.crazedns.ru`, valid to 13 Oct 2026 |
| Public pages, `/login` | 200 |
| Admin sign-in | **works** — `POST /login → 303` observed in the application log |
| Cache headers through the proxy | `Cache-Control: public, max-age=604800` and HSTS survive intact |
| Upload ceiling | 1, 10 and **40 MB reach the application**; 60 MB → 413 from our own Caddy |
| Client address seen by the application | **`192.168.1.1` for every external request** |

Two of those overturn things written earlier in this file, and one is a new defect.

**Correction — the certificate objection was wrong.** §6.1 of `docs/HANDOFF.md` and the entry above
argued that a fourth-level KeenDNS name cannot have a valid certificate, reasoning from a
`*.keenetic.pro` wildcard. Keenetic in fact issues a wildcard for the *router's own* name —
here `*.dmkdok.crazedns.ru` — which covers `profile.dmkdok.crazedns.ru` exactly. Strict `curl`
verification passes. No Cloudflare Tunnel is needed and none should be built.

**Confirmed good — KeenDNS imposes no request-size cap.** A 40 MB body reached FastAPI (which
answered 422, being a login form). The only ceiling on the path is the intended one: Caddy's 55 MB,
which returned 413 at 60 MB. A 30–50 MB photograph will upload.

**New defect — the login throttle is effectively global.** The router sends no `X-Forwarded-For`,
so Caddy substitutes its peer and the application records `192.168.1.1` for every visitor on earth.
`LOGIN_MAX_ATTEMPTS=5` per 15 minutes is therefore shared by everyone: any stranger can lock the
owner out of his own site with five wrong passwords, and the owner cannot fall back to the LAN
address because `ENV=production` makes the session cookie `Secure` and the LAN address is plain
HTTP. The flip side is that brute force is throttled unusually hard. Not fixable in this repository
— it needs the header from the router, or a deliberate decision about the limit.

### Open problems and bugs, all of them

Ordered by what bites first. Items 1–3 are consequences of this deployment; 4–8 predate it or sit
beside it.

1. **`SITE_URL` advertises `http://192.168.1.20:8080` to the internet.** Canonical, Open Graph,
   `sitemap.xml`. One variable in Portainer, then redeploy. Note the replacement must carry the
   port: `https://profile.dmkdok.crazedns.ru:8443`.
2. **The login throttle is shared by every external visitor** — no `X-Forwarded-For` from the
   router, so everyone is `192.168.1.1`. Five wrong passwords from a stranger lock the owner out
   for 15 minutes, with no LAN fallback because the LAN address is plain HTTP and the cookie is
   `Secure`. Detail above.
3. **No backups are scheduled.** No ZFS snapshot task on `media` or `pgdata`, no `pg_dump` cron.
   Harmless while the site is empty; not harmless the moment content exists. `make backup` does
   not apply here — see `docs/HANDOFF.md` §6.1.
4. **The Cyrillic font is downloaded twice on every cold load.** `base.html` preloads it through
   `static_url`, so the preload URL carries `?v=…`, while the `@font-face` rule asks for the same
   file without a query. The preload never matches, and it is the LCP-critical font. Pre-existing.
5. **CI runs no tests.** `publish.yml` builds and pushes; `latest` follows `main` in whatever state
   `main` is. The local gates are the only gates.
6. **The appliance runs TrueNAS 26.0.0-BETA.2.** A beta OS under a live site. Nothing has
   misbehaved, but it is worth knowing before diagnosing anything strange.
7. **`docs/TASKS.md` has no milestone for any of this work.** The deployment happened outside the
   M-numbering; it is the one place the tree and the checklists disagree.
8. **Credential hygiene, outstanding.** The TrueNAS account password and four tokens were pasted
   into a chat transcript. The classic GHCR PAT is *in use* — it is Portainer's registry credential
   — so it must be replaced in Portainer before being revoked, not after. `Test_Key` in TrueNAS is
   revoked and should be deleted. Full order of operations at the end of this session's notes.

Older functional gaps — article-image CLS, touch-target sizing, two labelling gaps, draft Russian
copy — are unchanged and live in `docs/HANDOFF.md` §8.

**Not a bug, but it will cost time again.** `media`, `pgdata` and `backups` are separate ZFS
datasets, so anything rooted at `portfolio` that does not cross a mount boundary shows them as empty
directories. Two consequences already met: an SMB share must be created on `media` itself, not on
the parent; and the **File Browser app cannot see them at all** — it bind-mounts `/mnt/tank` with
`propagation=rprivate` and has been running since 10 July, so mounts created afterwards never
entered its namespace. Restarting that app fixes it, and will be needed again for every future
dataset, ours or anyone's.

## Deployment, brought up on the LAN

Brought up 2026-08-13 through the Portainer API. Stack `portfolio`, three containers, `db` and `web`
healthy, serving `http://192.168.1.20:8080`. Datasets `tank/app_data/_dev_/portfolio/{media,pgdata,backups}`
— beside `_dev_/raskladka`, which is this appliance's own convention for the owner's projects.

Verified on the wire, not assumed: public pages, `/healthz`, `sitemap.xml`, `robots.txt`; migrations
applied (Postgres created `pgdata/18`); `Cache-Control: public, max-age=604800` on stylesheets;
`?v=` moving with the release. And the one that mattered most — **the unprivileged container writes
to an NFSv4-ACL dataset**, proven by the `originals/` and `derived/` directories the application
created there itself as uid 1000. Only Caddy publishes a port (8080); `db` and `web` publish none.
The host went from 29 containers to 32; nothing else was touched.

**What is still unverified, and why:** sign-in, the upload ceiling and the login throttle all need
working HTTPS, because `ENV=production` marks the session cookie `Secure`. They wait on external
access, which has a real obstacle recorded in `docs/HANDOFF.md` §6.1: KeenDNS publishes internal
apps under a *fourth*-level name while Keenetic's certificate covers only `*.keenetic.pro`, and a
TLS wildcard matches one label. Port 8080 is on KeenDNS's allowed list, which is luck worth keeping.

**A correction to ADR-018 and to the commit that carried it.** Both say the `ASSET_VERSION` defect
"became load-bearing" under a proxy caching `/static` for a week. That overstates it *for this
deployment*: the image is rebuilt from a fresh checkout each release, so `templating.py`'s mtime
moved too and the old code would have busted caches anyway. The fix is still right — it makes the
mechanism mean what its name says, and it is the difference between working and not in any
deployment that bind-mounts `app/`, which is what development does — but the week of stale CSS was
never going to happen here. Recorded so the next session does not inherit the wrong reason.

**One defect found from the live request log, not fixed.** The base template preloads
`onest-cyrillic.woff2` through `static_url`, so the preload carries `?v=…`, while the `@font-face`
rule in CSS asks for the same file without a query. Different URLs: the preload never matches, the
browser fetches the font twice and warns that a preloaded resource went unused. It is the
LCP-critical font. Pre-existing — the version query was appended before this session too — and
outside the deployment's scope, so it is left for a decision rather than fixed in passing.

### Next actions, in order

1. **Set `SITE_URL` to `https://profile.dmkdok.crazedns.ru:8443` and redeploy the stack.** Until
   then the site tells search engines and link previews that it lives at `192.168.1.20`.
2. **The four post-deploy checks**, in `docs/HANDOFF.md` §7 — sign-in, a 30–50 MB upload, the login
   throttle from two different networks, a restore rehearsal. The upload is the likeliest to fail:
   whether KeenDNS caps request size is undocumented, and so is whether it forwards
   `X-Forwarded-For`, which is what the throttle depends on.
3. **The owner's own unaided pass through all three publishing flows.** Still the single open item on
   the launch checklist in `docs/SPEC.md`, and still his by definition. Better done against the
   deployed site than locally.
4. **Backups.** Nothing is scheduled yet — no snapshot task on the two datasets, no `pg_dump` cron.
   The site now holds real state, so this stops being theoretical the moment content is added.

**Credentials.** `ADMIN_USERNAME` is `admin`; `ADMIN_PASSWORD`, `SECRET_KEY` and `POSTGRES_PASSWORD`
were generated during deployment and exist only in the Portainer stack's environment, readable at
Portainer → Stacks → portfolio → Editor. Changing `ADMIN_PASSWORD` there and redeploying updates the
stored hash.

**If instead the next session is more UI work:** open `docs/UI-AUDIT.md` at «Phase B», run
`iterate-product` again as I2, and take the cheap end first — F-011 (`position: relative` on
`.nav__capsule`), F-012 (named scroll regions), F-015 (admin bar clearance), F-023 (`:active`, which
now has the `:disabled` rule it depended on). The consolidations — F-009, F-010 — touch shared
primitives and want a milestone of their own.

**Waiting on the owner:** step 2 above, and `docs/TASKS.md` has no milestone for this work — the
deployment was planned and executed outside the M-numbering. Add one or leave it; it is the only
place the tree and the checklists now disagree.

**CI runs no tests.** `publish.yml` builds and pushes; it does not gate on the suite. `latest`
follows `main` whatever state `main` is in. The local gates remain the only gate, which is fine
while one person releases by hand and worth revisiting when that stops being true.

**Two things about this machine that cost time today.** `make` is **not on PATH** here, in either
shell, although `README.md` and `docs/CONVENTIONS.md` document every command as `make …` — run the
`Makefile`'s body directly (`docker compose up --build -d`, `docker compose run --rm tests`). And
**Docker Desktop was not running** at the start of the session; `docker compose` fails with a
named-pipe error until it is started and the daemon answers `docker version`.

**Decided by the owner on 2026-08-08:** «блог» and «статьи» mean the same thing, so one rule for
pictures in text — 1920 px — and it covers project descriptions too; he exports files up to
**50 MB**, so the cap is 50 (and the proxy is now 55); `README.md` is **Russian**, unlike
everything under `docs/`. And, put to him during this session's review: when deduplication hands
back a ladder narrower than the profile asks for, **top the ladder up** rather than refuse to
deduplicate.

## Baseline I1

Recorded 2026-08-10 **before** any work on the UI audit, on branch
`session/2026-08-06-m3-fixes-and-e2e` with a clean tree (only `docs/UI-AUDIT.md` and the two new
skills untracked). This is the line any regression in M10 is measured against.

| Gate | Command | Result |
|---|---|---|
| Unit + API | `docker compose run --rm tests` | **224 passed**, exit 0 |
| End-to-end | `uv run pytest e2e -q` | **40 passed**, exit 0 |
| Lint + format | `uv run ruff check .` then `uv run ruff format --check .` | clean, 114 files already formatted |

Two environment facts, unchanged from the last session and paid for again today: `make` is **not on
PATH** here, so the `Makefile`'s bodies are run directly; and Docker Desktop was not running at the
start, so `docker compose` failed with a named-pipe error until it was started.

## Iteration I1 progress — closed
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred)
- [x] 2 impact map written
- [x] 3 docs amended (SPEC F24/F49/F50, ADR-016/017, TASKS M10)
- [x] **GATE approved by the owner 2026-08-10 («утверждаю»)**
- [x] 4 implementation — T102–T106, all five
- [x] 5 verification green (226 / 57 / lint clean), baseline suites still green
- [x] 6 review clean (`docs/REVIEW.md` run 3, PASS; no Critical/High/Medium)
- [x] 7 closed (STATUS rewritten, M10 ticked)

## Checklist
- [x] Phase 0 intake
- [x] Phase 1 elicit (DoR met)
- [x] Phase 2 SPEC.md
- [x] Phase 3 PLAN.md + TASKS.md
- [x] GATE user approved
- [x] Phase 4 implementation (M0–M9 done)
- [x] Phase 5 tests green (unit/API 224/224; e2e 40/40; lint and format clean)
- [x] Phase 6 review clean (`docs/REVIEW.md` run 1, PASS at `a0c2835`; Critical + 6 High fixed, Mediums scheduled as T100/T101)
- [x] Phase 7 handoff (`docs/HANDOFF.md`; the production deploy stays open by the owner's choice)
- [x] **GATE — M9 approved 2026-08-08 («утверждаю»)**
- [x] **M9 complete — T090–T101, all twelve done and ticked**
- [x] **Phase 6 re-run against M9** (`docs/REVIEW.md` run 2, PASS; 2 High + 2 Medium found and fixed in the same session)
- [x] **GATE — I1 delta approved 2026-08-10 («утверждаю»)**
- [x] **M10 complete — T102–T106, all five done and ticked**
- [x] **Phase 6 against M10** (`docs/REVIEW.md` run 3, PASS; no Critical/High/Medium, one latent CSS defect found by the new tests and fixed)

## Test report

Each gate below carries its own last-run timestamp and the command that produced it.

| Gate | Command | Last run | Result |
|---|---|---|---|
| Unit + API | `docker compose run --rm tests` | 2026-08-15, close of I2 | **271 passed**, exit 0 |
| End-to-end | `uv run pytest e2e` | 2026-08-15, close of I2 | **81 passed**, exit 0 |
| Six launch flows | `uv run pytest e2e -m launch_flow` | 2026-08-08 | **6 passed**, exit 0 |
| Lint | `uv run ruff check .` | 2026-08-15, close of I2 | clean, exit 0 |
| Format | `uv run ruff format --check .` | 2026-08-15, close of I2 | clean, 127 files |

No failing tests. **Iteration I2 grew the suite 233 → 271 and 60 → 81**, against the baseline in
`## Baseline I2` taken before the change request was read. Iteration I1 before it grew 224 → 226 and
40 → 57, and the search-field fix that followed took e2e to 60.

**Only the tests the impact map named were edited**, plus one it did not: `e2e/test_login.py`'s
unscoped `get_by_role("alert")`, which resolves to two elements once the toast host has a permanent
alert region on every page. Everything else new is an addition, and every addition fails without the
change it guards — with one named exception, T112, argued in the iteration doc.

`-q` is set twice, so a passing run prints dots and no summary line. **Read the exit code.** Never
pipe a test run through `tail` or `grep`: you get the pipe's status and a red suite reads as green.

**Two traps this machine cost time on, both of which will recur.** The i18n catalogue is behind
`@lru_cache` in `app/templating.py`, so a **newly added translation key does not appear until the web
container restarts** — it surfaces as the raw key (`blog.save_failed`) rendered on the page, and it
cost one confusing red test. `docker compose restart web`, then wait for `/healthz` before running
e2e; a run started against a restarting container fails at the `_site_is_up` fixture with
`RemoteDisconnected`, which looks nothing like the real cause. And `docker compose run --rm tests
<path>` **replaces the command rather than appending to it** — the service's command is
`["python", "-m", "pytest", "-q"]`, so a single file is run as
`docker compose run --rm tests python -m pytest <path>`.

**Nothing is known bad.** Every task in every milestone including M10 is done and ticked; the only
unticked item anywhere is T074, the production deploy, which the owner has chosen to run himself.

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
- **2026-08-08 — Phase 6 ran for the first time and returned FAIL.** Two independent reviewers, neither of which wrote code. Full record in `docs/REVIEW.md`. **The Critical: F17's login throttle was bypassable with one header.** `client_ip()` took `X-Forwarded-For`'s *leftmost* entry — the one the client writes — so a rotating value bought a fresh five attempts every time; `docker-compose.prod.yml` made it worse with `--forwarded-allow-ips "*"`, under which uvicorn rewrites `request.client.host` from the same header, leaving **no untainted source of the peer address anywhere in the shipped configuration**. Reproduced before it was touched: `[401 × 6]`, never a 429. **The suite had been green because no test sent the header** — the lesson worth carrying, and the second time this project has found a control that passed while checking nothing (the authorisation sweep was the first).
- 2026-08-08 — Six High findings, all fixed with the Critical: `ADMIN_PASSWORD=change-me` shipped unvalidated while `SECRET_KEY`'s identical placeholder was refused; `DecompressionBombError` is not an `OSError` or a `ValueError` and walked past `verify_decodable`, giving a 500 with an HTML body to a client parsing JSON and leaving the original on disk; `.search-field__input` killed the site-wide focus ring with `outline: none` inside `@layer components`, on the one control present on every page; the reorder/publish/delete buttons carried no `id`, so htmx could not restore focus and a keyboard admin dropped to `<body>` on every arrow press; a rejected site-links save returned 200 and therefore said nothing at all, in the footer; `.prose table { display: block }` stripped the table's role in Chrome and Firefox, and the comment claiming the browser wraps it was simply wrong; the upload queue was a live region that announced ~150 times for a 50-file drop.
- 2026-08-08 — **In-article picture CLS closed: 0.119 → 0.00023** (`docs/qa/perf-article.json`). `markdown.py` emits the rendition's own size, read from the file header by `images.intrinsic_size` — Pillow opens lazily, so it is a seek and not a decode. Two things worth keeping: **`body_html` is rendered once, at save**, so a renderer change reaches new writing only — `scripts/rerender_prose.py` re-renders stored rows from the Markdown that produced them, and it has to skip rows whose HTML is deliberately blank, because `pages._put_value` empties it for the social links and the copyright name on purpose. And **the e2e case is portrait deliberately**: with the fix disabled, two landscape frames measured 0.014, inside budget, and the test would have proved nothing; portrait measured 0.030. Verified both ways before believing it.
- 2026-08-08 — Owner's decisions recorded under "Resume here": no production deploy inside a working session, «блог» = «статьи», 50 MB uploads, Russian README.
- 2026-08-08 — **M9 written and awaiting the gate.** F41–F48, T090–T101, ADR-013/014/015 proposed. Two design notes that took the most thought: deletion **asks the database** who still uses a file rather than keeping a reference table, because a count that drifts either leaks files (harmless) or deletes one that is still on a page (the exact failure being prevented) — the cost is a few `LIKE` scans, fine at this size, and the threshold to revisit is a few thousand articles. And "photographs at their best" is delivered as a **native-width rendition at quality 92**, not as the original file: `/media` is mounted over `derived/` only, and that mount is what makes an original unreachable structurally rather than by rule (ADR-012). Serving the original would trade a structural guarantee for a configuration one, on the single property that must not fail.
- **2026-08-08 — Session ended mid-milestone on an out-of-band `/pause`, and this time the handoff was audited rather than summarised.** Two implementer subagents had just been dispatched for M9 and were stopped while still reading; `git status` confirmed neither had written a file. **This is the second time a `/pause` has landed on this project while subagents were in flight** — the first, on 2026-08-06, produced a handoff written from a mid-run snapshot that had to be corrected afterwards. The rule that follows: on pause, stop the agents first, then read the tree, and never record a subagent's self-report as the state of the repository.
- 2026-08-08 — T099 is deliberately half done rather than half claimed. `README.md` and `scripts/screenshots.py` are written and **the script was actually run** (8 screenshots, both themes) rather than committed unexercised — the T073 mistake, where "documented *and* tried once" was ticked with the second half unmet. The «Обслуживание медиа» section was cut from the README before committing because it documented `make media-orphans` / `make media-prune` and the deduplication guarantee, none of which exist until T090 and T093. An accurate short README beats an aspirational one; the task line says exactly what to put back.
- **2026-08-08 (session 2) — M9 implemented, 11 tasks of 12. Every gate green, nothing left mid-edit.** Done solo rather than by parallel implementers: the last two sessions both had a `/pause` land while subagents were in flight, and T090–T093 are one design that does not split.
- 2026-08-08 — **T090–T093, the media lifecycle, are one mechanism and worth reading as one.** `media_asset` keys a stored upload by the SHA-256 of its bytes; `images.owners_of(db, stem)` asks the content tables who still points at a file; `is_referenced` is `bool(owners_of(...))` and `release(db, *paths)` deletes only what nobody claims. **One predicate, two callers** — `release` and `scripts/media_orphans.py` — deliberately, because two implementations of "who uses this file?" would be free to disagree, which is the drift ADR-013 exists to prevent.
- 2026-08-08 — **Deduplication turned two test fixtures into liars, and both were silent.** `test_photo.py::make_jpeg` and `test_blog.py::png_bytes` returned identical bytes on every call, so one test's cover landed in another test's directory under another profile's ladder — the failure surfaced as `cover_path` ending `_1280.webp` in `posts/_unfiled/`. Both now vary one pixel per call and take a `seed` when sharing bytes is the point. **The same trap cost the e2e perf measurement more:** `big_album` cycled ten frames five times to save CPU, so fifty tiles pointed at ten URLs, forty were served from cache, and "what does a fifty-photograph page cost?" was answering for ten. Fifty distinct frames now. **Any fixture that reuses bytes is now a fixture that reuses files.**
- 2026-08-08 — **ADR-014's "quality 92" had to be amended in the doing.** Applied literally to every rung it put the grid's 640 thumbnails at 134 KB against a 120 KB budget — 40% heavier albums for a difference invisible at the ~300 CSS px a tile is drawn at, which contradicts the ADR's own stated consequence that "the grid is unaffected". `images.THUMBNAIL_QUALITY` (82) now governs the 640 rung for every profile; re-measured at 97.6 KB, CLS 0.00023, LCP 172 ms (`docs/qa/perf-50.json`). **The lesson: when a decision states an intent and a mechanism, and the mechanism defeats the intent, the intent is the decision.**
- 2026-08-08 — `cover_sources` moved out of `blog.py` into `images.py` and now globs. It used to build a `srcset` by *asserting* that a `_640.webp` sibling existed; with deduplication a cover can be a frame first stored under another profile, so the ladder behind it is not something any caller can state. `/dev` cards use it too now — with `COVER` at (640, 1600) a project card was downloading the 1600 rendition for a 240 px slot.
- 2026-08-08 — **A 500 used to leave without any security headers.** Starlette builds it in `ServerErrorMiddleware`, which sits *outside* the user middleware stack, so the middleware that stamps the CSP never runs on the way out — on precisely the response most likely to be carrying detail nobody meant to publish. `apply_security_headers` is a function now, called from both the middleware and the handler. Verified by removing the call and watching the test go red.
- 2026-08-08 — **`autofocus` is still on all five swapped fragments and that is not the finished state.** T101 wanted it replaced by a `[data-autofocus]` handler, because the spec lets a browser ignore the attribute on markup inserted after parse. The handler is written and both attributes are present, so nothing regressed — but with `autofocus` deleted the keyboard publish flow fails: the handler does not focus the «Новая статья» field. Tried on `htmx:afterSettle` reading both `event.detail.target` and `event.target`; neither worked, which points at the listener not firing rather than at the wrong element. Written into "Resume here" as action 3.
- 2026-08-08 — **`make media-orphans` / `make media-prune` exist, and the first prune deleted 29 orphaned uploads (33.2 MB) and 174 empty directories from the dev media root.** Eight of those files were the residue `scripts/migrate_media.py` reported after T083; the rest were e2e albums and abandoned uploads from before deletion released anything. Both targets are idempotent — a second run reported nothing to do — and `--prune` re-asks the database before it unlinks, so it cannot delete a file a row written since the listing now claims.
- 2026-08-08 — Two environment traps confirmed again, and one new one. The **i18n catalogue is cached at import**, so `app/i18n/ru/*.json` needs `docker compose restart web`; a **container older than a compose-file change does not have that change's bind mount** — `web` was three days old and had no `/app/scripts`, which read as "the script does not exist" until `docker compose up -d web` recreated it. And **Git Bash rewrites a leading `/app/...` into a Windows path** when it is an argument to `docker compose exec`; use the PowerShell tool for those.
- **2026-08-08 (session 3) — M9 closed, Phase 6 re-run against it, and every one of the three fixes checked in both directions.** T099 finished, T101 actually finished, the review found two Highs and two Mediums and all four are fixed. Nothing is left mid-edit and nothing is scheduled.
- 2026-08-08 — **`data-autofocus` never fired, and both recorded hypotheses were wrong.** The listener *does* run and *does* reach `document.body`; the selector was right. `event.detail.target` is htmx's **original** target, and every fragment here swaps `outerHTML`, so by the time the event fires that element has been removed from the document — the handler was searching the markup that was replaced. `(event.detail && event.detail.target) || event.target` therefore never reached the fallback, because the first operand is always truthy. Diagnosed in ten seconds by setting `htmx.logger` and printing, for every event, the element it fired on and `document.contains(elt)` — worth doing *first* next time an htmx handler looks dead. `swappedScope(event)` now takes whichever candidate is still in the document. **The same defect was two lines above**, in the handler that focuses a rejected save's invalid field; it had been doing nothing on these fragments.
- 2026-08-08 — **htmx's own `processFocus` implements `[autofocus]` on swapped content.** That is why the attribute appeared to work where the HTML spec says it need not, and why removing it did not degrade to "browser decides" but to nothing at all. Anything relying on `autofocus` inside an htmx swap is relying on htmx, not on the platform.
- 2026-08-08 — **The `Caddyfile` capped request bodies at 30MB while `MAX_UPLOAD_MB` was 50**, under a comment claiming the two matched, and `docs/HANDOFF.md` quoted «25 MB and 30 MB» — stale on both numbers. In production every upload between 30 and 50 MB would have been refused by the proxy before the application saw it: no Russian message, no hint which file. **No test can catch this class** — dev runs without the proxy, and the deploy is deliberately never run inside a session — so the only defence is that the two numbers now name each other in both files. Same shape as the review's original Critical: a control that is green everywhere except where it is load-bearing.
- 2026-08-08 — **Deduplication is keyed on bytes, not on what the bytes were wanted for, and that quietly capped photographs.** A frame first stored as a cover carries `COVER`'s ladder — 640/1600 at quality 85, never the frame's own width — and adding it to an album reused those renditions and marked the photo `READY` on the spot. The lightbox would have served 1600 px at q85 for a 4000 px original, forever, with nothing to revisit it: ADR-014's one property that must not fail, lost to a cache hit. **`COVER` and `PROSE` are subsets of neither**, so the same trap existed between a cover and an in-article picture. `images.missing_rungs` names what a profile wants and the disk lacks — by glob, because the profile a file came in under is recorded nowhere — and `images.top_up` renders exactly those onto the one stored copy. F42 asks for one file behind one URL; it does not ask for a rung to go unrendered.
- 2026-08-08 — **One of the tests was asserting the defect.** `test_a_second_upload_of_known_bytes_generates_no_new_renditions` demanded that a deduplication hit render *nothing* — it passed for the whole of M9 and was the reason the cap looked intentional. A test that encodes an implementation detail as a requirement will defend a bug against the person trying to fix it. It now asserts what F42 actually promises: one stored original, no second copy.
- 2026-08-08 — **`make` is not on PATH on this machine**, in Git Bash or PowerShell, although `README.md` and `docs/CONVENTIONS.md` document every command as `make …`. Run the `Makefile`'s body directly. Docker Desktop also needs starting before anything: `docker compose` fails with a named-pipe error until `docker version` answers.
- **2026-08-11 — The nav search field, reported by the owner from a screenshot rather than by a sweep.** Three faults on one control: two concentric focus rings in two different oranges (`--accent` on the label's border against `--accent-ink` on the input's outline); the ring painted on the inner `<input>` at `outline-offset: -3px` against 2px of padding, so its left stroke crossed the first letter of the query; and the user agent's own clear button, the one piece of chrome the token layer never saw, arriving white on dark and blue on light. **The ring belongs on the box the eye reads as the control** — the label, icon and clear button included — not on the focusable element inside it; `outline: none` on the input is the only one on the site and is bought by the label's ring existing, which `e2e/test_search.py` now asserts as one contract so neither half can be removed alone. Details under «After the close» in `docs/iterations/I1-ui-audit-p1.md`.
- 2026-08-11 — **A measurement trap worth keeping: `getComputedStyle` in the same tick as `.focus()` reads the *resting* value of any transitioned property.** `border-color` on `.search-field` transitions over `--dur-fast` (130ms), so the first failing run printed a transparent border and looked impossible. Outlines are not transitioned, which is why the assertions that mattered were unaffected — but a colour assertion on a transitioned property needs the transition waited out or it asserts the wrong frame.
- **2026-08-11 — `ASSET_VERSION` does not change when a static file does.** `app/templating.py` computes it from `Path(__file__).stat().st_mtime` — templating.py's own mtime — under a comment claiming it is "bumped whenever the process restarts". It is bumped by neither a restart nor a CSS edit, and `Caddyfile` caches `/static/*` for a week, so a CSS- or JS-only release serves stale assets to returning visitors for up to seven days. **Development cannot show this**: no proxy, and `./app` is bind-mounted. Reported, not fixed — see "Waiting on the owner".
- 2026-08-08 — The owner committed `eec956a` himself, mid-session, reverting most of an earlier tooling commit: the numeric thresholds (report-length budget, debug-round cap, STATUS line caps, the rotation of old notes into `docs/notes/`, `.test-runs/`) went, the SessionStart hook and the practices from Claude Code's own guidance stayed. Consequence worth knowing: **`.test-runs/` is not gitignored** — put long test logs in the session scratchpad, not in the tree.
