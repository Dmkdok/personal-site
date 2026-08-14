# I2 — Pagination, HEIC intake, and Phase B of the UI audit

Opened 2026-08-14 on `iteration/I2-pagination-media-phaseb`, cut from `main` at `dfc8f92`.
Source: `docs/ROADMAP.md` items **R-05**, **R-10** and **R-12**, chosen by the owner.

## Baseline

Recorded before the change request was read. Full table in `docs/STATUS.md` § *Baseline I2*.

| Suite | Result |
|-------|--------|
| `docker compose run --rm tests` | **233 passed**, exit 0 |
| `uv run pytest e2e` | **60 passed**, exit 0 |
| `ruff check .` / `ruff format --check .` | clean, 120 files |

Green, nothing inherited. The **226** quoted in the I1 close is stale — the tree collects 233,
counted with `--collect-only` rather than read off a summary line.

## Intake

### In

| Item | What is taken |
|------|---------------|
| **R-05** | Pagination on `/blog` and `/photo`; result counts and a continuation on `/search`, which is also audit finding **F-014** |
| **R-10** | **HEIC/HEIF accepted on input**, converted at ingest so nothing downstream learns a new format |
| **R-12** | Phase B of `docs/UI-AUDIT.md` — F-007…F-018 as the audit orders them, plus F-023, minus F-016 |

### Out, with reasons

| Deferred | Reason | Recorded |
|----------|--------|----------|
| **AVIF output** (the second half of R-10) | Owner decision. Every rung becomes a second file on the media volume and a second encoder pass in the background pool, against a volume already projected at 20–25 GB (`SPEC.md:229`). The byte win is real but it is not worth doubling `derived/` and lengthening every batch in the same iteration that rewrites the photo tile. | **ADR-019** |
| **F-016** — clipped tile controls on narrow portrait tiles | Owner decision, on I1's measurement: **zero** targets failed WCAG 2.5.8 at 360 px as admin. This is comfort, not conformance, and the audit itself routes comfort questions to ADR-010. Its useful half — F-017 — is taken. | **ADR-020** |
| **Blog archive by year** (the third part of R-05) | Owner decision. A new navigational entity — its own URLs, canonicals and sitemap entries — where pagination alone closes the page-size problem the roadmap names. | **ADR-021** |

### Acceptance

- `/blog` and `/photo` render a bounded number of items with a crawlable, shareable URL per page.
- `/search` states how many matches each group has and offers the rest of a capped group.
- A `.heic` file straight off an iPhone uploads, processes and appears in the album.
- Every P2 finding of the audit is closed or has an ADR saying why it is not.

### Non-negotiables

- The originals stay unreachable over HTTP; `/media` remains mounted over `derived/` only.
- No client-side framework, no build step, no third-party request (`UI-AUDIT.md:812`).
- Fragment boundaries stay as they are (`UI-AUDIT.md:809`) — `#album-board`, `#photo-grid`,
  `#editor-meta`, `#project-board` keep returning the whole surface they change.
- The server-side upload gate stays the authority; the client gate is the earlier of two.

## Impact map

`BR` = blast radius. **shared** = a primitive many things read; **local** = one surface.

| # | Change | Touches | SPEC | Covered today by | BR | Proof of no regression |
|---|--------|---------|------|------------------|----|------------------------|
| 1 | `is-admin` on `<body>`, global admin bottom clearance (F-015) | `app/templates/base.html`, `admin.css`, `components.css:564-572` | F36 preserved | `e2e/test_a11y.py` focus sweep (admin) | **shared** | Anonymous HTML still contains no admin markup (F36 test); tab to the last control at 360 px as admin, ring fully visible |
| 2 | One `.status-chip`, one `.form-error`; `.button:active` (F-010, F-023) | `components.css`, `dev.css`, `photo.css`, `blog.css`, `admin.css`, 4 templates, e2e selectors | — | e2e selectors naming `.badge`, `.post-flag`, `.photo-badge` | **shared** | Every renamed selector updated in the same commit; draft chips still render on all three sections |
| 3 | `.label` split into eyebrow / `.field__label` / `.meta` (F-009) | `components.css`, `admin.css`, `blog.css`, `photo.css`, templates using `.label` incl. `pages/search.html:44` | — | contrast sweep, both themes, 76 samples | **shared** | Contrast re-measured after the split; no sample below its threshold, and `--text-faint` is not moved down |
| 4 | Assertive, dismissable error toasts; z-index over the lightbox (F-007) | `app/static/js/ui.js:16-25`, `base.html:75-84`, `components.css:677-687` | F37 preserved | `e2e` tests asserting a toast appears | local | Success toasts keep the 4 s auto-remove; an error toast survives 5 s and closes on its «×» |
| 5 | Per-field error binding in project and album forms (F-008) | `app/routers/projects.py`, `app/routers/photos.py`, `dev/_project_form.html`, `photo/_album_form.html` | F21, F33 preserved | `tests/api/test_photo.py`, rejection paths | local | Rejecting a `repo_url` puts `aria-invalid` on that field and the caret in it, not on «Название» |
| 6 | `.nav__capsule { position: relative }` (F-011) | `components.css:30-42` | F1 preserved | e2e nav tests | local | Dropdown edges align with the capsule at 360/480/767 px, both themes, screenshots into `docs/qa/` |
| 7 | Named, focusable scroll regions in prose (F-012) | `app/services/markdown.py`, `app/i18n/ru/blog.json` | F9 preserved | `tests/unit` markdown tests | local | Tab reaches a wide `<pre>`; sanitiser still strips what it stripped before |
| 8 | `forced-colors` blocks (F-013) | `photo.css`, `components.css` | — | nothing — cannot be automated | local | **Manual**: Edge contrast theme, focus ring visible on every contact-sheet thumbnail; recorded in `docs/qa/` |
| 9 | Undescribed-photo count and marked tiles (F-017) | `photo/_grid.html`, `photo/_photo_tile.html`, `photo.css`, `app/i18n/ru/photo.json` | F25 preserved | alt-text sweep | local | Server-side alt fallback **unchanged**; the sweep still finds no empty alt |
| 10 | «Показать правки» toggle (F-018) | `partials/admin_bar.html`, `admin.css`, `base.html:12-19`, a small script | F36 preserved | — | local | `aria-pressed` tracks the state (do not repeat F-019); no flash on load; resting appearance unchanged when off |
| 11 | Pagination primitive | new `partials/pagination.html`, a helper, `base.html` for `rel=prev/next` | new requirement | — | **shared** | Page 1 is byte-identical in item order to today's first N items |
| 12 | `/blog` paginated | `app/routers/blog.py:122-147`, `blog/index.html` | F8 amended | `tests/api/test_blog.py`, `e2e/test_article_publish.py` | local | Drafts section stays whole; a published post is on exactly one page; `?page=999` is not a 500 |
| 13 | `/photo` paginated **for visitors only** | `app/routers/photos.py:138-145`, `photo/_board.html` | F3 amended | `tests/api/test_photo.py`, `e2e/test_album_upload.py` | local | See the ordering note below — `_board()` and its six mutation callers are untouched |
| 14 | Search counts and continuation (F-014) | `app/services/search.py:24,120-131`, `pages/search.html`, `app/i18n/ru/common.json` | F10 amended | `tests/api/test_search_seo.py` | local | The count is the group's real total, asserted against a seeded set larger than the cap |
| 15 | HEIC/HEIF accepted | `app/services/images.py:51,52,60-63,386`, `pyproject.toml`, `uv.lock` | F24 amended | `tests/unit/test_photo_pipeline.py`, `e2e/test_upload_guard.py` | **shared** (intake) | A `.heic` fixture stores, decodes and renders WebP rungs; a `.tiff` is **still** rejected; the 60 MB refusal still fires client-side |

### Ordering, and it is binding

1. **Rows 1–3 are shared primitives and land first, serially, in that order.** `.label` (row 3) is
   read by templates that rows 2 and 9 also edit; the `is-admin` body class (row 1) is what rows 9
   and 10 hang their visibility off. Nothing downstream may start beside them.
2. **Row 11 lands before rows 12–14.** All three render the same control.
3. **Row 15 is independent of every other row** — it touches `images.py` and the dependency set,
   nothing in the UI vocabulary — but it is scheduled last so the two UI milestones stay adjacent.

### `/photo` is paginated for the visitor and whole for the owner

`_board.html` is the swap target of six mutating endpoints, and `album_reorder`
(`app/routers/photos.py:657-663`) applies the posted ids against the **global** row list through
`_reorder_from_ids`. Slicing that list would make drag-reorder mean something different on page 2
than on page 1, and would put a page parameter into six endpoints that do not have one today.

So the owner's board keeps every album — it is an editing surface over a global order, and the
whole reason it exists is an interaction that a page boundary breaks. The visitor's `/photo` is
paginated. The difference is the same one the site already draws for drafts, unpublished albums and
failed photos, and it costs zero change to the reorder path. Recorded as **ADR-022**.

### Tests whose expectations change

Only these, and each is a behaviour change the owner is approving with the feature:

- **e2e selectors naming `.badge` / `.photo-badge` / `.post-flag`** — renamed to `.status-chip` by
  row 2. The assertion is unchanged; only the selector moves.
- **Any assertion that `/blog` or `/photo` lists every item** — rows 12 and 13 bound it. Tests that
  seed fewer items than a page hold unchanged; a test that seeds more must state the page it means.
- **`tests/api/test_photo.py` rejection assertions for HEIC**, if any assert that `.heic` is refused.
  Row 15 inverts that, which is the point of R-10.

No other existing test may be edited. A red test outside this list is a regression, not an
expectation to update.

**One more was found during the build.** `e2e/test_login.py:61` located the login error with an
unscoped `get_by_role("alert")`. Row 5 gives the toast host a permanent `role="alert"` region on
every page, so that locator resolves to two elements everywhere and Playwright's strict mode refuses
it. The assertion is unchanged; it is now scoped to `.login`. The alternative — leaving the region
out of the DOM until an error arrives — is the thing the finding warns against: a live region
created at the same moment as its content may never be announced.

## What the build corrected in the audit

### F-015: the prescribed fix is half of one (T107)

`docs/UI-AUDIT.md` prescribes `padding-block-end` on the admin page, and T107 was written to put it
on `.page__main`. Two failing runs of the new focus sweep showed that is not enough and that the
element it names is the wrong one.

- **Wrong element.** The footer is `.page__main`'s sibling, and the control the audit itself found
  under the bar — «Изменить ссылки» — lives in it. Padding on main opens a gap in the middle of the
  page and moves the last control in the document by nothing. Measured: `bottom: 744` against a bar
  top of `708`. The rule went on `.page`.
- **Missing half.** Document length lets a control *be* scrolled clear; it does not make the browser
  scroll it clear. Chromium scrolls a tabbed-to control just far enough to touch the viewport edge,
  which is underneath a fixed bar: measured `bottom: 780` on every surface with the padding in place
  and nothing else. `scroll-padding-block-end` is the property that moves that edge, and it belongs
  on the scroll container — `:root`, not `<body>`, where it parses and does nothing.

Both halves are now in `admin.css` and both were watched failing alone before being kept. The audit
line stays as a finding; its remedy column understates the fix.

### F-011: the overhang does not reproduce (T112)

The audit reads `.nav__capsule` as statically positioned and concludes that the open menu resolves
against `.nav`'s full-viewport padding box. The reasoning is right and the conclusion is not:
`backdrop-filter` on the capsule already makes it a containing block for absolutely positioned
descendants, so the menu has been aligned all along in every browser that supports the property.

Measured three ways at 360 px: as shipped, `−1 px` per side (the capsule's own border, which is
where `inset-inline: 0` resolves). With `position: relative` alone removed, unchanged. With
`backdrop-filter` removed as well, `−20 px` per side — exactly the audit's overhang, and exactly one
gutter.

`position: relative` is kept anyway. Alignment of the one control that appears on every page should
not depend on a visual effect that a browser, a user setting or a later edit can withdraw. The new
test measures the result rather than the mechanism, so it holds whichever of the two is doing the
work. This is the second finding in Phase B whose written evidence did not survive being measured
(F-016 was the first, in I1).

### What the sweep does not assert

`#post-body` is a 22-row textarea, taller at 360 px than the fold. Chromium leaves a partially
visible element where it is, so its lower half sits off-screen — hidden by the viewport edge, not by
author-created content. WCAG 2.4.11 is about the latter, so the check skips any control whose box
does not fit in the viewport. Asserting on it would be asserting that the editor be short.

## Exit criteria

- [ ] Every P2 finding is closed, or has an ADR (F-016 → ADR-020).
- [ ] `/blog`, `/photo` and `/search` bound what they render, and say so in the page.
- [ ] A `.heic` file uploads and appears; a `.tiff` is still refused before a byte is sent.
- [ ] Contrast re-measured after the `.label` split; no sample below threshold.
- [ ] The forced-colors pass is recorded in `docs/qa/` with what was done, on what, and when.
- [ ] Unit/API ≥ **233**, e2e ≥ **60**, lint and format clean, all on the final tree.
- [ ] Each in-scope item has a check that fails without the change.
