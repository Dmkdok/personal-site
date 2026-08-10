# Review

Three Phase 6 runs. **Run 3 is the current one and is below**; the earlier two
are kept underneath it because their findings are the reason half of M9 exists,
and a reviewer arriving later should be able to see what was already looked at.

---

# Run 3 — Phase 6 against M10 (iteration I1), 2026-08-10

Scope is the I1 delta only, not the product: the diff between `b69fe10` (the
approved docs commit) and the working tree. The impact map in
`docs/iterations/I1-ui-audit-p1.md` is what the diff was judged against —
the reviewer's question in an iteration is "did anything move that was not
supposed to", not "is this product good".

## Verdict

**PASS.** No Critical, High or Medium findings. Two notes, both recorded below
rather than fixed, and one defect **found by the new tests and fixed in the same
session** (`.button[hidden]`).

Nothing outside the milestone's owned paths moved. The three extra files the
diff touches beyond the task list — `dev/_board.html`, `photo/_board.html`,
`photo/_grid.html` — carried the `is_first`/`is_last` plumbing that existed for
one purpose, the `disabled` attribute this iteration removes; leaving it would
have left dead variables and a comment describing behaviour that no longer
exists. Two more, `dev/_project_form.html` and `blog/_editor_meta.html`, held
the third and fourth hardcoded copies of the accepted MIME list that T105 exists
to unify. Both extensions are named here because the task list did not name
them.

## Security

**Tooling:** manual (`semgrep` is not on PATH on this machine).

**No critical/high findings in scoped review.**

The one change with a security dimension is F-004, which is a *client-side*
gate. What matters is that it did not become the only gate:

- `app/services/images.py` and `app/config.py` are **byte-for-byte unchanged**
  (`git diff --stat` on both is empty). The size cap, the MIME allow-list, the
  magic-byte check and the decode verification are all exactly where they were,
  and `tests/unit/test_photo_pipeline.py`'s oversize rejection still passes.
- The new client check is deliberately *narrower* than the server's: a file
  whose `type` the browser could not determine is passed through rather than
  refused, because the server reads the magic bytes and would have accepted a
  JPEG saved without an extension. A client gate that refuses more than the
  server would is a bug that looks like caution.
- The values published to the page — `data-max-bytes`, `data-accept` — are
  public policy, not secrets, and the markup carrying them is admin-only
  (`album.html:26` wraps the uploader in `{% if is_admin %}`).
- No new route, and no route lost its `CurrentAdmin` dependency;
  `tests/api/test_authz_sweep.py` enumerates every non-`GET` route and passes.
- `_move_headers` builds a catalogue key by interpolation, so it was read
  twice: both halves are internal literals — `kind` is a call-site constant and
  `outcome` is one of three values `_swap` returns. The user-controlled
  `direction` never reaches the key.
- No `innerHTML` anywhere in the new JavaScript. File names — the only
  attacker-influenced strings in play — reach the DOM through `textContent` and
  `setAttribute`, as they did before.
- No inline `<style>` or `<script>` added, so the `style-src 'self'` CSP is
  untouched. (The a11y sweep reveals hover-only controls through the CSSOM for
  exactly this reason; an injected style tag would have been dropped silently
  and the sweep would have measured nothing while reporting success.)

| ID | Severity | Issue | Where | Fix |
|----|----------|-------|-------|-----|
| — | — | none | — | — |

## Found by the new tests, fixed in this session

**`.button[hidden]` did nothing.** `.button` sets `display: inline-flex`, which
outranks the user agent's `[hidden] { display: none }`. The new «Отменить»
control is the first button on this site to use the attribute, and
`test_a_running_batch_can_be_stopped` caught it immediately — the element
carried `hidden=""` and Playwright still reported it visible. One rule added in
`components.css` next to `.button:disabled`. Latent since the button component
was written; nothing had exercised it until now.

## Notes — recorded, not fixed

1. **The cover uploads have no size pre-check.** `_editor_meta.html`'s article
   cover and `_project_form.html`'s project cover now share the accepted MIME
   list with everything else, but they are plain htmx multipart forms with no
   JavaScript behind them, so a 60 MB cover still travels the whole way up
   before the server refuses it. F-004's target state named the album uploader
   and in-article images, and both are done. Extending the gate to the two cover
   forms means giving them a script they do not currently have; it belongs in
   its own task, not in this one.
2. **A cancelled upload is a client disconnect.** `cancelAll` calls `.abort()`
   on the live `XMLHttpRequest`s, which the server sees as a dropped connection
   mid-multipart — the same thing a lost Wi-Fi connection already produced, so
   no new server path is exercised. Nothing is written until the bytes are
   complete and validated, so an aborted upload leaves nothing behind.

## Regression against the impact map

Every row's stated proof exists and runs:

| Item | Proof named in the map | Status |
|------|------------------------|--------|
| F-001 | the four sweeps pass over an admin session, or an argued exception | Pass, **no exception needed** — 83 contrast samples per theme with zero failures and zero unmeasurable, 120 focus stops with zero missing indicators, zero targets under 2.5.8 at 360 px |
| F-002 + F-006 | focus is on the pressed button, never `<body>`, and a message appeared | `e2e/test_admin_keyboard.py`, 4 cases (project, album, photo, cover) |
| F-003 | a dialog on leaving dirty, none after a save; the failed state persists | `e2e/test_editor_guard.py`, 4 cases |
| F-004 | zero requests for a refused file; `data-max-bytes` equals the server's | `e2e/test_upload_guard.py` (3 cases, one a positive control) + `tests/api/test_photo.py::test_the_upload_zone_publishes_the_servers_own_limits` and `tests/api/test_projects.py::test_the_project_form_accepts_what_the_server_accepts` |
| F-005 | a `[disabled]` control differs in computed opacity | `e2e/test_a11y.py::test_a_disabled_button_looks_disabled` |

**No existing test was edited.** The prediction in the map held: `grep disabled`
found no assertion on the old behaviour, and the `beforeunload` guard did not
disturb any existing editor test, because none of them navigates away from a
dirty editor.

## Gates at the time of this verdict

| Gate | Command | Result |
|---|---|---|
| Unit + API | `docker compose run --rm tests` | **226 passed**, exit 0 (baseline 224) |
| End-to-end | `uv run pytest e2e -q` | **57 passed**, exit 0 (baseline 40) |
| Lint + format | `uv run ruff check .` / `ruff format --check .` | clean, 118 files |

---

# Run 2 — Phase 6 against M9, 2026-08-08

Read at `ab46f82`; the fixes below are committed on top of it.

Re-run because the passing verdict was against `a0c2835`, and M9 has since
rewritten the media lifecycle, the upload limit, the CSRF failure path and the
security headers on a 500. Read through Serena; the gates were re-run rather
than taken from a checkbox, and the two claims singled out for a second reading
— `images.release` and the one-shot CSRF retry guard — were traced end to end.

## Verdict

**PASS.** The pass returned **FAIL** on two High findings — no Critical — and
both were fixed in the same session, along with both Mediums, on the owner's
instruction. Neither High was a security defect and neither was visible to a
visitor; both silently defeated a decision the owner had made and signed off
on. Everything M9 claimed to have built, it built. What was wrong was the edge
where two of those mechanisms met something outside themselves — a proxy, and
another profile's ladder.

## High — fixed

- **The production body cap contradicts the 50 MB upload limit.**
  [Caddyfile:20-23](../Caddyfile#L20-L23) sets `request_body { max_size 30MB }`
  under a comment reading «Matches MAX_UPLOAD_MB with headroom for the multipart
  envelope». T094 raised `MAX_UPLOAD_MB` to 50 on the owner's explicit decision
  («he exports files up to 50 MB»), and the proxy was not moved with it. In
  production every upload between 30 and 50 MB is refused by Caddy with a bare
  413 **before the application is reached**, so `validate_upload`'s Russian
  «слишком большой файл» never runs and the size the owner was promised is not
  the size he gets. Nothing local catches it: dev runs without the proxy, and
  T074 — the one thing that would exercise this path — is deliberately never run
  inside a working session. This is the same shape as run 1's Critical: a
  control that is green everywhere except where it is load-bearing.
  **Fixed**: `max_size 55MB`, with the coupling written into the comment and
  into `docs/HANDOFF.md`, which was quoting «25 MB and 30 MB» and was stale on
  both numbers. No test can cover this — the proxy is not in the dev stack — so
  the defence is that the two numbers now name each other in both places.

- **Deduplication can strand a photograph on the cover ladder.**
  [app/routers/photos.py:719-734](../app/routers/photos.py#L719-L734) accepts a
  content-hash hit from *any* profile. `COVER` is `(640, 1600)` at quality 85;
  `PHOTO` is `(640, 1600, 2560)` **plus the original's own width** at quality 92
  ([images.py:109-116](../app/services/images.py#L109-L116)). So a frame first
  uploaded as an article or project cover and later added to an album reuses the
  cover's renditions, is marked `READY` on the spot, and never gets the
  native-width rung — the lightbox serves 1600 px at quality 85 for a 4000 px
  original, and nothing ever revisits it. ADR-014 calls showing the owner's
  frames at their best the property that must not fail, and `store_and_process`
  reasons about exactly this trade for prose, where it is invisible
  ([images.py:598-604](../app/services/images.py#L598-L604)) — the album path
  inherited the behaviour without inheriting the reasoning. The reverse
  direction is harmless: a `PHOTO`-first frame reused as a cover gets a richer
  ladder, and `cover_sources` globs rather than assuming.

  **Fixed**, by the owner's choice of the two options put to him: top up rather
  than refuse to deduplicate. `images.missing_rungs(asset, profile)` names the
  widths a profile wants and the disk does not have — by glob, because the
  profile a file came in under is recorded nowhere and would be one more thing
  free to drift — and `images.top_up` renders exactly those onto the one stored
  copy. `store_and_process` does it synchronously; the album route branches on
  the same predicate and sends the upload to the background pool as a fresh one
  would, because a 50 MB frame does not belong on the request path. One file,
  one URL, every rung anyone has asked for; F42 is untouched.

  Two regression tests, both confirmed to fail with the fix disabled: a cover
  reused as a photograph gains its native-width rung
  (`tests/unit/test_photo_pipeline.py`), and a cover reused in prose gains the
  1280 rung while the original stays a single file (`tests/api/test_blog.py`).
  **The second replaced a test that was asserting the defect** —
  `test_a_second_upload_of_known_bytes_generates_no_new_renditions` demanded
  that a dedup hit render nothing at all. It now asserts what F42 actually
  promises: one stored file behind one URL, not an unrendered rung.

## Medium / polish — fixed

- **Three user-visible Russian strings are still hardcoded**, against ADR-007
  and `docs/CONVENTIONS.md`: `aria-label="Блок кода"` and `aria-label="Таблица"`
  in [app/services/markdown.py:57-58](../app/services/markdown.py#L57-L58), and
  the «Сохранено» toast in
  [app/routers/pages.py:116](../app/routers/pages.py#L116). All three predate
  M9; T100 swept seven files for exactly this and these were not among them. The
  two `aria-label`s are the ones that matter — they are what a screen reader
  announces on entering a code block or a table.
  **Fixed**: a `prose` area in `app/i18n/ru/common.json`, and the two openers
  built per call rather than held as module constants — the catalogue is read on
  import, and reading it *at* import here would depend on which module got there
  first. The toast now uses `editable.saved`, which already held the same word
  and was already used eleven lines below.

- **`make media-prune` can end on a traceback after it has already deleted
  files.** [scripts/media_orphans.py:135-138](../scripts/media_orphans.py#L135-L138)
  calls `directory.rmdir()` unguarded, on a listing taken earlier in the run. A
  directory that gained a file in between raises `OSError` and the script exits
  non-zero having done most of its work — which reads as a failed prune when it
  was a successful one. The file deletion immediately above it is careful about
  precisely this race (`release` re-asks the database); the directory sweep is
  not.
  **Fixed**: each `rmdir` is guarded, a directory that refuses is named and
  counted out, and the closing line reports what was actually removed rather
  than what was listed.

## Read twice, and clean

- **`images.release` holds the line it is supposed to hold.** Every one of the
  eight callers commits the rows *before* releasing, which is the whole
  contract: `is_referenced` reads the database, so a row still in flight would
  read as a live reference and the file would be kept — the safe direction.
  `owners_of` scans every column in the schema that can hold a media path
  (`Photo` ×4, `Post`, `Project`, `SiteContent`, each in both Markdown and
  rendered HTML); the one it skips, `MediaAsset.original_path`, is bookkeeping
  that `release` deletes itself. `Album` has no path of its own — its cover is a
  foreign key to a `Photo`, so it is covered by the photo scan. `_delete_stem`
  globs rather than reconstructing widths, so a ladder stored under a different
  profile is still fully removed. The «owner deleted an article, owner broke
  another article's cover» case is the one the design is built around and it
  holds in both directions.

- **The one-shot CSRF retry cannot loop.** `data-csrf-retried` is set before the
  retry is issued and cleared only in `htmx:afterRequest` when
  `event.detail.successful` is true — and the vendored htmx sets
  `e.successful = !isError`, with `isError` true for any 4xx. So a second 403
  leaves the flag set and the retry path is skipped: at most two requests per
  episode. `/csrf` hands out the caller's *own* session token, there is no CORS
  middleware anywhere in the app, so another origin cannot read the answer.

- **Security headers now survive a 500.** `apply_security_headers` is a function
  called from both `_security_headers` and the `Exception` handler, which is the
  fix for `ServerErrorMiddleware` sitting outside the user stack. Confirmed live
  on a 404 as well; the unit suite covers the 500 and was verified by breaking
  the call.

- **Run 1's Critical did not regress.** `client_ip` still refuses to read
  `X-Forwarded-For`, with the reasoning written into the docstring.

- Spot-checked live against the running stack: `sitemap.xml` lists eleven URLs
  and every one of them returns 200, including both `/dev/{slug}`; a 205-
  character query returns 200 with guidance rather than a JSON 422; `.env` is
  untracked and both placeholder validators are in place; no credentials in the
  tree.

## Gates at the time of this verdict

Run 2026-08-08, after the fixes above.

| Gate | Command | Result |
|---|---|---|
| Unit + API | `docker compose run --rm tests` | **224 passed**, 4 skipped, exit 0 |
| End-to-end | `uv run pytest e2e` | **40 passed**, exit 0 |
| Six launch flows | `uv run pytest e2e -m launch_flow` | **6 passed**, exit 0 |
| Lint | `uv run ruff check .` | clean, exit 0 |
| Format | `uv run ruff format --check .` | clean, exit 0 |

The suite grew 222 → 224: the two rung-top-up regressions. Both were checked in
both directions by disabling the fix and watching them go red — as was the
`data-autofocus` handler earlier in the same session, which took four e2e tests
with it.

---

# Run 1 — Phase 6, 2026-08-08 at `a0c2835` (closed)

Run on commit `cbe63de` plus the CLS fix. Two independent
reviewers, neither of which wrote code: one on completeness/correctness/security
against `SPEC.md` with the `secure-review` checklist, one on UI/UX with
`web-design-guidelines`. Both read the tree through Serena and re-ran the gates
themselves rather than trusting a checkbox.

## Verdict

**PASS** — as of `a0c2835`. The first pass returned **FAIL** on one Critical;
that and all six High findings are fixed and covered by tests. Everything
remaining is Medium or polish and is scheduled as M9 or listed below as
knowingly carried.

## Critical — fixed

- **F17's login throttle was bypassable with one header.** `app/security.py`
  `client_ip()` took `X-Forwarded-For`'s **leftmost** entry — the one the client
  writes — so a rotating value bought a fresh budget on every attempt.
  Production compounded it: `docker-compose.prod.yml` passed
  `--forwarded-allow-ips "*"`, under which uvicorn 0.52 rewrites
  `request.client.host` from the same header, leaving no untainted source of the
  peer address anywhere in the shipped configuration.
  Reproduced before it was touched: six failed logins with a rotating header
  returned `[401 × 6]` and never a 429; the same six with a fixed value fired at
  the sixth. **Fixed**: `client_ip()` trusts only what the ASGI server resolved,
  and the overlay names a proxy subnet (`TRUSTED_PROXY_IPS`, default
  `172.16.0.0/12`) instead of `*`. `tests/api/test_auth.py`
  `test_a_rotating_forwarded_for_cannot_buy_more_attempts` is the regression —
  the suite had been green only because no test sent the header.

## High — fixed

- **`ADMIN_PASSWORD=change-me` shipped unvalidated** while `SECRET_KEY`'s
  identical placeholder was refused, and the launch checklist says the only
  manual step is copying `.env.example`. Now refused at startup, with a 12-character
  minimum under `ENV=production` (`app/config.py`).
- **`DecompressionBombError` is not an `OSError` or a `ValueError`**, so it walked
  past `verify_decodable`'s except clause: HTTP 500 carrying an HTML page to a
  client parsing JSON, and the stored original left on disk. Caught broadly now —
  everything reaching that function is untrusted input — plus an explicit
  `images.MAX_PIXELS` closing the band where Pillow only *warns* and then decodes
  anyway, in a background worker where nobody is waiting to be told.
- **The search field killed its own focus ring.** `.search-field__input` had
  `outline: none` inside `@layer components`, beating the site-wide
  `:focus-visible` in `base.css` — on the one control present on every page. Its
  stated replacement, `:focus-within` swapping `--line-strong` for a transparent
  border, measures ≈1.8:1 in the light theme against SC 1.4.11's 3:1.
  `docs/qa/focus-sweep.json` passed it because the sweep's criterion is
  "something changed", never the indicator's contrast.
- **Keyboard focus was lost on every reorder.** The move/publish/cover/delete
  buttons in `_photo_tile`, `_album_card`, `_album_head` and `_project_card` swap
  `outerHTML` on an ancestor and carried no `id`; htmx restores focus only to an
  id that survives the swap, so a keyboard admin reordering a 50-photo album
  dropped to `<body>` on every arrow press. Every one carries a stable id now.
- **A rejected site-links save said nothing.** It returns 200 with the form
  re-rendered, so `htmx:responseError` never fired, the submit button was
  destroyed by the swap and focus fell to `<body>` — in the footer, at the very
  bottom of the page. The exact failure F37 exists to prevent. Now: `role="alert"`
  on the error, an error toast on the rejection branch, and an `htmx:afterSwap`
  handler in `ui.js` that focuses the first `[aria-invalid]` in the swapped
  fragment.
- **`.prose table { display: block }` stripped the table's role** — header
  associations and row/column counts gone from the accessibility tree in Chrome
  and Firefox — and the comment claiming the browser wraps it was wrong; nothing
  did. The scroller is a wrapper emitted by the renderer now
  (`div.table-scroll[role=region][tabindex=0]`), and `<pre>` is focusable and
  named, because Chrome 127+ makes scroll containers focusable on its own and
  Firefox and Safari do not.
- **The upload queue was a live region.** Fifty files append fifty rows and
  rewrite each twice — roughly 150 polite announcements with no throttle, which a
  screen-reader user must drain before the page is usable. The list is
  `aria-live="off"`; one `role="status"` line beside it, outside anything
  `hidden`, reports "Готово N из M" once a second.

## Carried, with reasons

Not defects in the reviewers' sense; scheduled or knowingly accepted.

- **T074 — the production stack has never run on a real server.** The owner's
  call, made 2026-08-08: the deploy happens when the site is finished, not now.
  Everything else on the launch checklist is met.
- **Medium findings become M9.** Both reviewers flagged the same three: hardcoded
  Russian in templates and in Python against `CONVENTIONS.md` and ADR-007, the
  missing `og:image` on index pages, and `sitemap.xml` advertising `/dev/{slug}`
  URLs that 404 for projects without a long description. Those plus the rest are
  T098–T099 in `TASKS.md`.
- **`session-expiry-mid-edit` does not behave as SPEC edge case 5 describes.** An
  expired cookie means no session CSRF token, so the middleware rejects with 403
  before the route's 401 runs, and the toast advises a reload — which discards the
  typed content. `start_session` also rotates the CSRF token, so re-logging in
  another tab leaves the open page's token stale and the retry 403s too. Real, and
  the fix (a token refresh endpoint plus one retry in `ui.js`) is bigger than the
  finding; **T099**.
- **`login_attempt` grows without bound** — only an IP's failed rows are deleted,
  and only when that IP later succeeds. A personal site's table will not
  embarrass anyone this decade, but it never shrinks; **T099**.
- **Waived by ADR:** touch targets (ADR-010, WCAG 2.5.8 rather than SPEC F12's
  44 px), the `{.wide}`/`{.full}` vocabulary (ADR-011), media on a bind mount
  (ADR-012).

## What the reviewers checked and found clean

Worth recording so the next review does not repeat it. Authorisation: all 30
mutating routes carry `CurrentAdmin`, and the sweep's route enumeration was
dumped to confirm it matches real paths rather than silently matching nothing —
this had been a live defect once before. Draft and unpublished filtering: an
anonymous sweep of every public surface, search and the sitemap leaked no draft,
no unpublished album and no admin markup. SQL: the FTS query is
`websearch_to_tsquery` with a bound parameter; injection and operator-soup
payloads both return 200. XSS: fifteen crafted Markdown payloads — `<script>`,
`onerror`, `javascript:` and `vbscript:` links, `data:` images, raw `srcset`,
`<svg onload>`, inline `style`, attribute-quote breakout, a forged width class —
all neutralised. Secrets: `.env` untracked and git-ignored, history clean.
Cookies, CSP and the media-root containment all as specified. On the UI side: the
focus-visible treatment, the skip link, reduced motion, both themes, the lightbox
dialog and its focus trap, a keyboard alternative to every drag, designed empty
states everywhere, and — checked specifically, because it is the trap this
project keeps hitting — the ≤640 px admin-bar clearance on the footer, which
**is** handled.

Semgrep was not installed and was not installed for this review; the security
pass was the `secure-review` checklist applied by hand, with each finding
reproduced against a throwaway database.

## Gates at the time of the verdict

| Gate | Command | Result |
|---|---|---|
| Unit + API | `docker compose run --rm tests` | **204 passed**, exit 0 |
| End-to-end | `uv run pytest e2e` | **37 passed**, exit 0 |
| Lint | `uv run ruff check .` | clean, exit 0 |
| Format | `uv run ruff format --check .` | clean, exit 0 |
