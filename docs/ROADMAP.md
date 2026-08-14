# Roadmap

Written 2026-08-14, against the tree at `8ec69a5`, after the site went live on the NAS.
Status: **proposed, not approved.** Nothing here is scheduled until the owner picks items;
approval is the same gate as everywhere else in this repository.

Source: a read of `docs/SPEC.md`, `docs/UI-AUDIT.md`, the application code and the deployment
configuration — not a wish list. Every item below names what is in the tree today and where.

## How to read this

Fifteen items in three tiers. Tier 1 is what an unattended live site cannot go without; tiers 2
and 3 are what makes it worth being live. Items carry `R-` numbers so they can be referred to
before they are accepted; an accepted item gets a real `F` requirement in `SPEC.md` and tasks in
`TASKS.md`, and this file stops being the authority for it.

Sizes are in the unit this project already uses — a task in `TASKS.md`, not a day:
**S** ≈ one task, **M** ≈ two or three, **L** ≈ a milestone.

Three items (R-04, R-06, R-07) contradict the non-goals list at `SPEC.md:223`. They are here with
the argument for reopening each, and they are the owner's decision, not the roadmap's. See
[Non-goals this roadmap challenges](#non-goals-this-roadmap-challenges).

---

## Tier 1 — the site does not survive without these

These are not features. They are the difference between a site that is running and a site that is
being operated.

### R-01 — Backups run on a schedule, and a copy leaves the machine

- **Now:** `scripts/backup.sh` dumps the database and archives the media, `make restore-check`
  rehearses a restore, and both work — a restore was rehearsed on 2026-08-07 (T086). But nothing
  runs them. There is no scheduler in `deploy/portainer-stack.yml`, no cron in any image, and the
  default `BACKUP_DIR` is `./data/backups` — the same disk that holds the originals it is meant to
  protect.
- **Do:** a scheduled job on the NAS (a stack service or a TrueNAS cron task) running
  `scripts/backup.sh` nightly; retention of 7 daily / 4 weekly / 6 monthly; a copy pushed off the
  machine with `rclone` or `rsync` to a second target; `make restore-check` on a monthly schedule
  with its result reported somewhere the owner reads. Log rotation for the backup job itself.
- **Why:** the media volume is projected at 20–25 GB of photographs (`SPEC.md:229`) that exist
  nowhere else. Today their survival depends on the owner remembering to type `make backup`, and
  on one disk. Every other item in this document is worth less than this one.
- **Size:** S. Most of the work is already written; what is missing is a scheduler and a second
  destination.
- **Depends on:** nothing. This is first.

### R-02 — The test suite gates the image, instead of running beside it

- **Now:** `.github/workflows/publish.yml` says so in its own header — *"This workflow does not run
  the test suite … `latest` therefore follows `main` whatever state it is in"*. There are 226
  unit/API tests and 60 e2e tests, and the only thing standing between a red suite and the running
  container is the owner running the gates by hand before a release (`docs/HANDOFF.md` §7).
- **Do:** a `tests` job — `docker compose run --rm tests` plus `ruff check`/`ruff format --check` —
  that `publish` declares as a dependency. e2e on tags `v*` only, where the extra minutes are
  affordable. Keep the exit-code discipline from `CLAUDE.md`: never pipe a test run through `tail`.
- **Why:** a suite that nothing enforces decays into a suite that is not run. The discipline exists
  today because one person remembers it; CI is how that survives a distracted week.
- **Size:** S.
- **Depends on:** nothing.

### R-03 — Something watches the site besides the owner's browser

- **Now:** `/healthz` exists and checks the database (`app/main.py:194`), and both compose files
  define container healthchecks. Nothing outside the host reads either. Unhandled exceptions are
  logged and forgotten (`app/main.py:183`), photos that end in `status=failed` are visible only on
  the page they belong to, and no `logging:` options are set on any service, so the JSON driver
  grows without a bound.
- **Do:** an external uptime check against `/healthz` (Uptime Kuma on the same NAS is enough) with
  a notification channel the owner already reads; a notifier for 500s and for failed photo
  processing — one webhook, no third-party SaaS, nothing that touches CSP because it is
  server-side; `max-size` / `max-file` on the log driver in `deploy/portainer-stack.yml`.
- **Why:** a personal site fails quietly. The realistic failure is not a crash but a container that
  restart-loops after a bad `latest`, or a disk that fills, discovered days later by a visitor.
- **Size:** S–M.
- **Depends on:** R-02 for the 500-notifier to be worth much (otherwise it reports defects CI should
  have caught).

### R-04 — A way to make contact that is not a social network

- **Now:** the home page offers GitHub, VK, Telegram and YouTube links, editable per F39. There is
  no email address and no form. `SPEC.md:223` lists a contact form as a non-goal.
- **Do:** the minimum first — a visible address with a copy-to-clipboard control, which needs no
  new endpoint and no non-goal revision. If the owner wants a form: one POST, honeypot plus the
  existing IP throttle from `app/security.py`, delivery by SMTP, no third-party service, no stored
  message table.
- **Why:** the primary user in `SPEC.md:15` is a prospective client answering "how do I reach him"
  within thirty seconds. An agency, an editor or a client's procurement department writes email and
  will not open Telegram to start a conversation. This is the one gap on the critical journey the
  product declares for itself.
- **Size:** S for the address, M for a form.
- **SPEC:** the address needs nothing; the form needs the non-goal at `SPEC.md:223` amended.

### R-05 — Indexes stop rendering everything they have

- **Now:** `post_index` selects every published article with no `LIMIT`
  (`app/routers/blog.py:121-131`), and `_visible_albums` does the same for albums
  (`app/routers/photos.py:138-145`). Search caps each group at twelve and says nothing about it —
  `DEFAULT_LIMIT = 12` at `app/services/search.py:24`, which the audit already filed as **F-014**.
- **Do:** pagination or "показать ещё" on `/blog` and `/photo`, an archive by year for the blog,
  and result counts plus a way to see the rest of a group on `/search`.
- **Why:** invisible at ten articles, a multi-second page and a megabyte of HTML at eighty. The
  cost of adding it later is that the URL scheme changes after the pages have been indexed and
  shared — this is cheaper before there is content, not after.
- **Size:** M.
- **Note:** F-014 is already in the audit backlog. Fold it in here rather than doing it twice.

---

## Tier 2 — reach and findability

The site is built to be found and read. These are the parts of that job it does not do yet.

### R-06 — A feed

- **Now:** none. `SPEC.md:223` lists RSS as a non-goal.
- **Do:** `/feed.xml` (Atom) built the way `sitemap.xml` already is — the same query, the same
  router, the same "published only" rule (`app/routers/seo.py:57-90`); an autodiscovery `<link>` in
  `base.html`. Optionally JSON Feed alongside, which is a second serialisation of one query.
- **Why:** the secondary user in `SPEC.md:20` is someone who follows the owner across VK, Telegram
  and YouTube and wants the writing in one place. A feed is exactly that promise, in the one form
  that does not require the reader to hold an account anywhere. It is also how aggregators and
  readers pick up articles without the owner posting three times.
- **Size:** S. This is the cheapest item in the document relative to what it buys.
- **SPEC:** needs the non-goal amended.

### R-07 — Some measurement, on this origin

- **Now:** none, by design (`SPEC.md:223`).
- **Do:** a self-hosted counter — Umami or GoatCounter on the same NAS, served from this origin so
  `connect-src 'self'` still holds and no third party is contacted. No cookies, no cross-site
  identifiers; that is what made analytics objectionable, and it is avoidable.
- **Why:** the site's own success criterion is "a visitor knows what he does, whether the work is
  good, and how to reach him, in thirty seconds". Nothing in the current build can say whether that
  happens — whether anyone reaches `/photo`, which article is read, where the drop is. Every
  content decision after launch is otherwise made blind, including which of the items in this
  document actually matter.
- **Size:** S–M.
- **SPEC:** needs the non-goal amended. The original reason — no third-party requests — is
  preserved by the self-hosted form, so the amendment is narrow: "no third-party analytics" rather
  than "no analytics".

### R-08 — Structured data, and an image for articles that have no cover

- **Now:** `base.html` carries a unique title, description, canonical, Open Graph and
  `twitter:card` (`app/templates/base.html:22-38`). There is no `application/ld+json` anywhere —
  `grep` finds none. T100 added a default `og:image` for index pages, so every coverless article
  shares one banner.
- **Do:** JSON-LD in the head — `Person` on `/`, `Article` on a post, `ImageObject` /
  `ImageGallery` on an album, `BreadcrumbList` on detail pages. All server-rendered, so the CSP is
  untouched. Optionally generate a per-article OG image from the title.
- **Why:** this is what a search engine reads to attribute an article to a named author and to
  build a rich result. For a portfolio whose whole purpose is to be the authoritative page about
  one person, saying so in machine-readable form is the cheapest SEO left.
- **Size:** S for JSON-LD, M with generated OG images.

### R-09 — The English version the schema was built for

- **Now:** `lang` columns on every content table, `app/i18n/ru/` with five per-area catalogues, and
  **ADR-007** stating plainly that both exist from day one so that an English version is additive
  rather than a rewrite. Nothing has been built on top of it; `DEFAULT_LANG` is `ru` and
  `SPEC.md:198` fixes v1 to Russian.
- **Do:** `/en/` routing, a language switch beside the theme toggle, `hreflang` and per-language
  canonicals, an `app/i18n/en/` catalogue, and a per-record translation path for content the owner
  chooses to translate (not everything needs to be).
- **Why:** the audience for the developer half is not confined to one country, and the architecture
  for this was already paid for. Left much longer, the cost rises with every template that quietly
  assumes one language.
- **Size:** L. It touches every router and every template, and half of it is the owner writing
  English copy.
- **SPEC:** an explicit v2 scope decision, not an amendment — `SPEC.md:198` already anticipates it.

### R-10 — HEIC in, AVIF out

- **Now:** `ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}`
  (`app/services/images.py:51`), and the rendition ladders write WebP only
  (`app/services/images.py:454`). Since I1/F-004 the client refuses an unsupported type before
  sending it — so a HEIC file is now rejected faster, but still rejected.
- **Do:** accept HEIC/HEIF on input via `pillow-heif`, converting on ingest so nothing downstream
  learns a new format; add AVIF as a second output rendition beside WebP, offered through
  `<source>` with WebP as the fallback.
- **Why:** HEIC is the iPhone default. The owner scenario in `SPEC.md:27` is publishing from a
  laptop after a shoot, and the phone in his pocket produces files this site will not take. AVIF is
  the other half: ~25–30% smaller at matched quality on exactly the payload this site is mostly
  made of.
- **Size:** M. AVIF encoding is slower, so measure `docs/qa/perf-50.json` again rather than
  assuming — the T094 discipline.

---

## Tier 3 — product and craft

### R-11 — Photographs carry their shooting data

- **Now:** EXIF is read once, to correct orientation, and then discarded —
  `ImageOps.exif_transpose` at `app/services/images.py:436`. Pillow writes no EXIF into the
  derivatives, so camera, lens, exposure, aperture, ISO and date are lost at ingest.
- **Do:** extract the shooting fields during processing, store them on `photo`, and render them
  under the frame or in the lightbox behind a per-album toggle. **Never surface GPS** — it is in
  the originals, the originals are never served (`app/main.py:149-152`), and it should stay that
  way.
- **Why:** for a photography section this is both credibility and free content: it says the picture
  was taken rather than generated, and it is the detail other photographers arrive for.
- **Size:** M. A migration, a pipeline change and a UI.
- **Note:** this pairs naturally with **F-017** in the audit backlog — every photograph without an
  owner-written alt currently gets the same sentence (`app/routers/photos.py:119-121`).

### R-12 — Phase B of the UI audit, as one iteration

- **Now:** thirteen P2 findings (F-007…F-018) deferred by **ADR-017**, with a phased plan already
  written at `docs/UI-AUDIT.md:828`. Deferred, not dropped, and the backlog is still accurate.
- **Do:** take Phase B whole, in the order the audit gives. The findings that cost the owner most
  daily: error toasts that cannot be dismissed and vanish in four seconds (F-007), form errors not
  bound to their field (F-008), the admin bar sitting over the bottom of every admin page (F-015),
  and edit affordances that appear only on hover with no way to reveal them all (F-018).
- **Why:** it is the only improvement queue in this repository that is already evidenced, ordered
  and given exit criteria. It needs a decision, not an analysis.
- **Size:** L — but it is sixteen small pieces with a written plan, which is the cheapest kind of L.
- **Depends on:** nothing. I1 already landed everything it needed.

### R-13 — A draft can be shown to someone, and a post can be published later

- **Now:** a draft is a 404 for anyone without a session (`SPEC.md:214`, edge case 7), and
  `published_at` is set at the moment «Опубликовать» is pressed (F30). So showing a draft to an
  editor means handing over the password, and publishing at a chosen hour means being awake for it.
- **Do:** a signed preview token with a TTL, giving one read-only URL for one draft; and a
  scheduled `published_at` with a background sweep — `app.background` already owns the pattern and
  the startup recovery hook.
- **Why:** both are the difference between writing alone and writing with anyone else involved.
- **Size:** M.

### R-14 — Reuse a picture without uploading it again

- **Now:** `media_asset` already stores every upload keyed by SHA-256, so re-uploading the same
  frame writes no second copy (F42, T090). But there is no way to *choose* an existing image: the
  only path into an article or a cover is the file dialog or a drop. Deduplication saves the disk;
  it does not save the owner from hunting for the file.
- **Do:** a picker over `media_asset` in the editor and the cover controls — a grid of recent
  uploads served from `<stem>_640.webp`, inserting the existing paths.
- **Why:** the second time a photograph is wanted — a portrait reused as an article cover months
  later — the owner has to find the original on disk. The table that makes this trivial already
  exists.
- **Size:** M. Note the table is deliberately thin (`app/models/media_asset.py`): no kind, no
  original filename, no alt. A picker needs at least a label, which means a migration, and it must
  not turn `media_asset` into the reference table **ADR-013** refused to build.

### R-15 — Performance is a gate, not a measurement

- **Now:** `docs/qa/perf-50.json` and `perf-article.json` are measured by hand when someone
  remembers (T094 re-measured them deliberately, which is the exception that proves it). **F-026**
  records six render-blocking stylesheets on an article page. `static_url` already versions assets
  by mtime, so caching is not the gap — the gap is that nothing fails when a page gets slower.
- **Do:** fold the existing Playwright measurements into the CI job from R-02 with the thresholds
  `SPEC.md:151-154` already states — LCP under 2.5 s, grid thumbnails ≤ 120 KB, CLS ≈ 0 — and
  close F-026 by reducing the stylesheet count or inlining the critical set, *if* the measurement
  says it matters, which is the condition the audit itself attached.
- **Why:** a budget nobody enforces is a budget that has already been exceeded and not noticed. The
  measurements exist; only the gate is missing.
- **Size:** S once R-02 exists.
- **Depends on:** R-02.

---

## Non-goals this roadmap challenges

`SPEC.md:223` forbids, among other things: comments, RSS, newsletter, contact form, analytics,
tags, reading time, view counters, English UI. Most of that list should stay exactly as it is —
it is the design, and `docs/UI-AUDIT.md:869` is right to say so.

Three entries are challenged here, each for the same reason: the ban was written for a site with no
third-party requests and no clutter, and all three are now achievable without either.

| Non-goal | Item | Original reason | Why it no longer applies |
|----------|------|-----------------|--------------------------|
| Contact form | R-04 | fewer moving parts; social links suffice | The declared primary user writes email. The address alone needs no form at all; a form adds one endpoint reusing throttling that already exists. |
| RSS | R-06 | one more surface to maintain | It is the same query `sitemap.xml` already runs, in a second serialisation, and it serves the declared secondary user directly. |
| Analytics | R-07 | no third-party requests, no tracking | Self-hosted on this origin, cookieless, cross-site identifiers absent. The prohibition can narrow to "no third-party analytics" and lose nothing it was protecting. |

If the owner keeps any of these closed, record it as an ADR with the reason, the way ADR-017
recorded the audit deferral. A non-goal that has been re-argued and kept is stronger than one that
was never questioned.

## Suggested iterations

Grouped so that each has one theme and can be run through `iterate-product` on its own. Order is by
dependency and risk, not by appetite.

| Iteration | Contents | Rationale |
|-----------|----------|-----------|
| **I2 — Operations** | R-01, R-02, R-03, R-15 | Everything that protects what already exists. R-15 rides along because it is a job in the workflow R-02 creates. Do this before adding anything. |
| **I3 — Reach** | R-04 (address first), R-05, R-06, R-08 | The gates a visitor and a search engine hit. Requires the non-goal decision on R-04 and R-06 up front. |
| **I4 — Phase B** | R-12, folding in F-014 from R-05 if it is still open | The audit backlog, taken whole in the order it prescribes. |
| **I5 — Photography** | R-10, R-11, R-14 | One theme, one part of the pipeline, one migration window. |
| **Later** | R-07, R-09, R-13 | R-07 is worth having early but is small enough to slot anywhere; R-09 is a milestone of its own; R-13 waits until someone besides the owner is in the loop. |

## Deliberately not here

- **Comments, tags, reading time, view counters, GitHub API sync.** Non-goals that contradict the
  product's intent rather than an outdated constraint. Their absence is the design (`SPEC.md:223`,
  `docs/CONVENTIONS.md:115`).
- **A client-side framework or a build step.** Ruled out by the audit's architecture actions
  (`docs/UI-AUDIT.md:802`) and unnecessary for every item above.
- **Moving image processing to a worker queue.** **ADR-004** decided in-process background work,
  with a queue named as the fallback if it proves insufficient. It has not. Revisit when a batch
  actually fails, not before.
- **Larger touch targets.** Settled by **ADR-010** with measurements in `docs/qa/`. Not a defect.
- **A separate admin panel.** The single strongest product constraint in the brief; nothing in this
  document weakens it.
