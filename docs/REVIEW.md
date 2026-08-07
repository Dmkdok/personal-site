# Review

Phase 6, run 2026-08-08 on commit `cbe63de` plus the CLS fix. Two independent
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
