# Iteration I1 — UI audit, Phase A (the four P1 findings)

- **Source:** `docs/UI-AUDIT.md` (read-only audit, 26 findings, 0 × P0 / 4 × P1 / 15 × P2 / 7 × P3)
- **Opened:** 2026-08-10
- **Milestone:** `M10` in `docs/TASKS.md`
- **Baseline:** unit/API 224 passed (exit 0), e2e 40 passed (exit 0), `ruff check` + `ruff format
  --check` clean, at 2026-08-10, branch `session/2026-08-06-m3-fixes-and-e2e`

## In scope

| Item | Why now |
|------|---------|
| **F-001** — every automated a11y gate skips the signed-in UI | Test-only, and it turns the rest of this round into a checklist instead of arithmetic. The surface the product exists to provide has never been contrast-checked, focus-swept or target-measured. |
| **F-002** — focus is dropped when an action disables or removes the control that was pressed | WCAG 2.4.3 (A). A keyboard-only owner reordering a board lands on `<body>` and restarts from the skip link. The only P1 that is an outright keyboard defect. |
| **F-003** — the article editor has no unsaved-work guard | The highest-cost failure mode in the product: a close or a navigation inside the 2.5 s autosave debounce loses the text silently, and a failed autosave is a toast that removes itself after 4 s. |
| **F-004** — uploads are validated only after the bytes have arrived | The owner exports up to 50 MB (ADR-014). A rejected file today costs a full upload first. Nielsen H5 + Doherty. |
| **F-006** — a reorder that cannot happen reports nothing | Not separately chosen: it is closed by the same change as F-002 and cannot be left open once the buttons stop being `disabled`. |
| **F-005** — `.button:disabled` has no styling anywhere | Rider, P2. F-002's fix removes `disabled` from the move buttons, but file inputs and the lightbox controls still need one shared treatment, and `photo.css` already carries a private copy. Six lines of CSS, and it stops the divergence growing. |

## Out of scope this round

| Item | Reason | Recorded as |
|------|--------|-------------|
| Phase B — the remaining thirteen P2 findings (F-007…F-018) | Owner's cut line. Several are consolidations of shared primitives (`.status-chip`, `.form-error`, the `.label` split) that would land on top of the P1 work and make a regression hard to attribute. | ADR-017 |
| Phase C — all seven P3 findings (F-019…F-026) | Craft, not defect. F-026 explicitly says "no change unless measured". | ADR-017 |
| F-023 `.button:active` | Depends on F-005 landing first, which it now does — but it is press feedback, not a defect, and it belongs with Phase B's other polish. | ADR-017 |
| Relaxing `_threshold()` so admin text passes the contrast sweep | The audit forbids it, and it would make the gate meaningless. | This document; the sweep keeps its thresholds. |

## Impact map

| Item | Touches | SPEC: changes / preserves | Existing coverage | Class | Regression proof |
|------|---------|---------------------------|-------------------|-------|------------------|
| **F-001** admin surfaces unmeasured | `e2e/test_a11y.py` → `test_text_meets_aa_contrast_in_both_themes`, `test_every_focus_stop_shows_a_visible_indicator`, `test_target_sizes_at_360px`, `test_every_image_is_described_or_marked_decorative`, module constant `PAGES`; `e2e/conftest.py` fixtures `admin_storage_state`, `admin_context`, `admin_page`, `published_album` | changes none; preserves the Accessibility block (`SPEC.md:155-161`), F11 (contrast both themes), F12 (2.5.8 at 360 px per ADR-010) | the four sweeps themselves — all anonymous. `admin_page` appears only in the two keyboard-flow tests. | **Local** (tests only), but scheduled first: it is the measurement the other rows are judged by | The four sweeps run over an admin session and pass, or the exception is argued in `docs/qa/` with the sample that caused it. No threshold moves. |
| **F-002 + F-006** reorder drops focus / no-op is silent | templates `dev/_project_card.html:83,94`, `photo/_photo_tile.html:73,84,89-99`, `photo/_album_card.html:51,62`; routers `projects.py::project_move`, `photos.py::album_move`, `photos.py::photo_move`, `photos.py::photo_set_cover`, helper `photos.py::_swap`; catalogues `app/i18n/ru/dev.json`, `app/i18n/ru/photo.json` | changes none; **adds F49**; preserves F25 (photo management), F34 (project ordering), `SPEC.md:156` (full keyboard operation of every admin control) | **none.** `grep disabled` finds no match in `tests/` or `e2e/` — no test asserts the end-of-list `disabled`, and no test reorders by keyboard. That is how the defect survived. | **Contract** — the button `id` is what htmx's focus restoration keys on, so template and router change together, in one task | New `e2e/test_admin_keyboard.py`: as admin, focus `#project-{id}-up` on the first project, press Enter, assert `document.activeElement` is that same button and a toast is present. Same for an album and a photo. |
| **F-003** editor has no unsaved-work guard | `app/static/js/editor.js` → the `form` `input` listener, `setStatus`, new `dirty` flag and `beforeunload`/`htmx:responseError`/`htmx:sendError` listeners; `app/templates/blog/_editor_meta.html` → `#save-state` (`data-failed`); `app/i18n/ru/blog.json` | changes none; **adds F50**; preserves flow 9 (`SPEC.md:45`), edge case 5 (`SPEC.md:200`), and the `#save-state` live region contract `_save_state.html` swaps into | `e2e/test_a11y.py::test_an_article_can_be_written_and_published_without_a_mouse` and `e2e/test_article_publish.py` drive the editor but never leave it dirty | **Local** — one script and one fragment. *Risk, not radius:* a `beforeunload` guard changes what happens when Playwright navigates away from a dirty editor. Named below. | New `e2e/test_editor_guard.py`: type, then assert a `beforeunload` dialog is raised on navigation and is **not** raised after a successful save. Plus: the two existing editor tests pass unchanged. |
| **F-004** uploads validated after the bytes arrive | `app/static/js/uploader.js` → `enqueue`, `send`, new abort/retry paths; `app/templates/photo/_uploader.html` → `#upload-zone` data attributes and the queue head; `app/templating.py` → one new Jinja global publishing the limits; `app/static/js/editor.js::upload`; `app/i18n/ru/photo.json`; `app/static/css/photo.css` (retry/cancel controls). Reads, does not change: `app/config.py::Settings.max_upload_bytes`, `app/services/images.py::ALLOWED_CONTENT_TYPES` | changes **F24** (amended in place: the browser refuses what it can already tell will fail); preserves F22 (batch upload, per-file state), edge case 2 (`SPEC.md:197`), and the Security block's "Upload hardening" line — the server gate is untouched | `tests/unit/test_photo_pipeline.py` (oversize rejected server-side), `tests/api/test_photo.py`. Client-side: **none** | **Cross-cutting policy** (upload limits) — forces `secure-review` in Phase 6 regardless of size. Also **Contract** (the data attributes are the server↔client agreement) | A unit/API check that the rendered `#upload-zone` carries `data-max-bytes` equal to `settings.max_upload_bytes` — the 30-vs-50 divergence class one number in one place prevents. New `e2e/test_upload_guard.py`: a 60 MB file and a `.tiff` each produce a failed row with **zero** requests to the upload URL. Existing server-side rejection tests unchanged and passing. |
| **F-005** `.button:disabled` unstyled | `app/static/css/components.css` → `@layer components`, next to `.button--quiet`; `app/static/css/photo.css:67` → delete `.photo-icon-button:disabled` | changes none; preserves F12 and the token layer (no token is added or moved) | none | **Shared primitive** — `components.css` ships on every page. Lands **first and serially**, before the templates that stop emitting `disabled`. | A computed-style delta: a `[disabled]` control differs from its enabled sibling in `opacity`. `grep -c ":disabled" app/static/css/photo.css` finds only the lightbox rule. |

### Ordering constraints

1. **T102 (F-005) first, alone.** `components.css` is a shared primitive; everything else in this
   milestone renders through it.
2. **T106 (F-001) before the fixes it measures** — that is the audit's own argument, and it is the
   only way F-002's proof is a number rather than an assertion. It is test-only, so it cannot break
   the product; it can only reveal.
3. **T104 (F-003) and T105 (F-004) both edit `app/static/js/editor.js`.** Different functions —
   `setStatus`/the form listener versus `upload` — but the same file, so they are **serial**, never
   parallel. T105 depends on T104.
4. T103 (F-002/F-006) is disjoint from the rest and may run alongside T104.

### Architecture note (UI-enabling only)

The upload limits reach the client through **one** new Jinja global in `app/templating.py`, sourced
from `settings.max_upload_bytes` and `images.ALLOWED_CONTENT_TYPES`. `app/services/images.py`
imports `translate` from `app/templating.py`, so the import must be **deferred inside the function**
— the pattern `templating.render` already uses for `app.security`. Publishing the numbers twice, by
hand, is the thing this iteration exists to stop.

## Expectations that change

Two, and both are behaviour changes wearing a test's clothes.

1. **No existing assertion breaks.** `grep disabled` across `tests/` and `e2e/` returns nothing, and
   no test drives a keyboard reorder. Removing `disabled` from the six move buttons and rendering
   the ★ button unconditionally is therefore invisible to the current suite — which is precisely the
   coverage gap F-001 and F-002 describe. Recorded as **ADR-016** because the visible behaviour does
   change for the owner: a button at the end of a list is no longer greyed out, it answers.
2. **`beforeunload` may change how Playwright leaves the editor.** No current test navigates away
   from a dirty editor, so the expectation is that nothing changes. If a test does start raising a
   dialog, the fix is a dialog handler in that test — **not** weakening the guard. Any such edit is
   reported before it is made.

## Exit criteria

- [x] The four a11y sweeps in `e2e/test_a11y.py` run over an authenticated session; each either
      passes or carries an argued, recorded exception in `docs/qa/`. No threshold was moved.
- [x] Pressing ↑ on the first project, the first album and the first photo leaves focus on the
      button that was pressed — never `<body>` — and produces a visible message.
- [x] The ★ button exists on every ready photo, including the current cover, and pressing it on the
      cover reports that it already is one.
- [x] Navigating away from an editor with unsaved text raises the browser's own confirmation; doing
      so after a successful save does not.
- [x] A failed autosave shows a distinct «не удалось сохранить» state that persists until the next
      successful save.
- [x] A 60 MB file and a `.tiff` are each refused with their own message before any byte is sent —
      asserted by counting requests to the upload URL, not by reading the screen.
- [x] A running batch can be cancelled, and a failed row can be retried without re-picking the file.
- [x] `#upload-zone`'s `data-max-bytes` equals `settings.max_upload_bytes`, asserted by a test.
- [x] `.button:disabled` exists once, in `components.css`; `photo.css` no longer defines its own.
- [x] Baseline suites green at their Phase 0 counts or better: unit/API ≥ 224, e2e ≥ 40, lint clean.

## Outcome — closed 2026-08-10

**Gates:** unit/API **226 passed** (baseline 224), e2e **57 passed** (baseline 40), lint and format
clean over 118 files. Every suite run in this session, none through a pipe.

**The prediction that mattered held.** No existing test was edited, and none broke. `grep disabled`
had found no assertion on the old end-of-list behaviour, so removing it was invisible to the suite;
and the `beforeunload` guard disturbed nothing, because no existing test navigates away from a dirty
editor. Both risks named at the gate came to nothing, and both were checked rather than assumed.

**F-001 found no failures.** This is the notable result. The audit expected the admin sweeps to
surface real contrast problems on the tile overlay, and possibly to confirm F-016's clipped controls
with numbers. Neither happened: 83 contrast samples per theme with **zero failures and zero
unmeasurable**, 120 focus stops with **zero** missing an indicator, and **zero** targets under WCAG
2.5.8 at 360 px. No exception needed to be argued in `docs/qa/`, and no threshold was moved. The
admin surface now measures as well as the public one — it simply had never been asked.

The reason the overlay produced nothing to measure is worth writing down, because the next reader
will wonder whether the sweep is really looking: the text inside `.photo-item__admin` is either
`aria-hidden` glyphs or `.visually-hidden` labels, both of which the walker correctly skips, and an
`<input>`'s value is not a child text node. F-016 therefore remains an open *comfort* question about
the 44 px bar, not a conformance one — exactly where ADR-010 already put it.

**One real defect found by the new tests.** `.button` sets `display: inline-flex`, which outranks the
user agent's `[hidden] { display: none }` — so the new «Отменить» control stayed on screen while
carrying `hidden=""`. Latent since the button component was written, and caught within a minute by
`test_a_running_batch_can_be_stopped`. Fixed in `components.css`.

**Five files were touched beyond the task list**, all named here because the tasks did not name them:

- `dev/_board.html`, `photo/_board.html`, `photo/_grid.html` — carried the `is_first`/`is_last`
  plumbing that existed solely to drive the `disabled` attribute this iteration removes. Leaving it
  would have left dead variables and a comment describing behaviour that no longer exists.
- `dev/_project_form.html`, `blog/_editor_meta.html` — held the third and fourth hardcoded copies of
  the accepted MIME list. A list written down four times is one that eventually disagrees with
  itself, which is the exact failure F-004 exists to prevent. Both now read `upload_limits()`, and
  `_editor_meta.html` looks it up itself rather than inheriting it, because publish, unpublish and
  both cover routes return that fragment standalone.

**Left undone, deliberately:** the two cover forms still have no *size* pre-check. They are plain
htmx multipart forms with no script behind them, so a 60 MB cover still travels the whole way up
before the server refuses it. F-004's target state named the album uploader and in-article images;
both are done. Extending the gate to the cover forms means giving them JavaScript they do not have,
and that is its own task.

## After the close — the nav search field

Found by the owner, in the browser, after M10 was committed: not an audit finding, not in scope, and
not something any of the four sweeps would have caught. Fixed on the same branch as one small
follow-on commit rather than reopening the milestone.

**Three faults, one control.** The search field in the nav capsule is on every page.

1. **Two focus rings.** `.search-field:focus-within` painted its border in `--accent` while the
   site-wide `:focus-visible` outline sat 3px inside it in `--accent-ink`: two concentric rings, in
   two different oranges. The comment above the rule already said the border was decoration and had
   to stay under 3:1 — the code had stopped agreeing with it. Now `--accent-ink`, once.
2. **The ring crossed the text.** With the ring on the inner `<input>` and `outline-offset: -3px`
   against 2px of inline padding, the stroke landed between the field's edge and the first letter.
   The ring moved to the label — the box the eye reads as the control, icon and clear button
   included — at `outline-offset: -1px`, so it sits on the field's own border and focus does not
   change the field's footprint. `outline: none` on the input is the only one on the site, and it is
   only allowed because the label one box out paints the ring the moment the input takes focus.
3. **The clear button was the user agent's.** `type="search"` draws a glyph the token layer never
   saw: white on the dark theme, blue on the light one. `appearance: none` plus a `data:` mask paints
   it in `--text-faint`, which follows both themes. `img-src` already allows `data:`, so the CSP is
   untouched. Firefox draws no clear button at all and cannot be made to; the field works without it.

**Tests:** `e2e/test_search.py` gained three cases (40 → 57 → **60**). The ring test is parametrised
over both themes and asserts one contract in four parts — the ring exists, it is on the field, it
stays out of the box the text lives in, and focus does not move the field. It was proved by putting
the old rules back and watching both parametrisations go red before the fix was restored.

**One trap it cost time on.** `border-color` on `.search-field` is transitioned (`--dur-fast`,
130ms), so a `getComputedStyle` taken in the same tick as `.focus()` reads the *resting* colour and
a failure prints a border that looks impossible. The test waits the transition out. The outline is
not transitioned, which is why the assertions that matter were never affected.

**One finding out of scope, reported and not fixed:** `ASSET_VERSION` in `app/templating.py` is
`Path(__file__).stat().st_mtime` — **templating.py's own** mtime, not the static tree's. The comment
above it claims it is "bumped whenever the process restarts"; it is not bumped by a restart, and it
is not bumped by editing CSS or JS either. Combined with `Caddyfile`'s
`header @static Cache-Control "public, max-age=604800"`, a release that changes only static assets
serves the old ones to returning visitors for up to a week — which is precisely the shape of this
change. Left for the owner to schedule; `static_url` already receives the path, so keying `?v=` on
the requested file's own mtime is the small version of the fix.
