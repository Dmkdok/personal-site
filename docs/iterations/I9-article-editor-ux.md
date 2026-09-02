# Iteration I9 — Article editor UX: a discoverable photo control, and the shared editor gets the blog editor's toolbar

- **Source:** owner request in chat, 2026-09-01 — inserting a photo into an article feels
  drag-and-drop/paste-only, phone use is painful, and the shared-article editor lacks the
  formatting toolbar the blog editor has.
- **Opened:** 2026-09-01
- **Milestone:** `M21` in `docs/TASKS.md`
- **Baseline:** unit/API 399 passed, e2e 112 passed / 3 failed (pre-existing, environment-local —
  see `docs/STATUS.md` Baseline I9), lint clean, format clean 130 files, at 2026-09-01, branch
  `iteration/I9-article-editor-ux`

## What the code already does, found before scoping

- The blog editor's toolbar already has a photo action: `editor.js`'s `image` handler
  (`ACTIONS.image`) calls `picker.click()`, which opens the OS file picker — camera or gallery on
  a phone, no drag-and-drop or paste required. It has worked since F51/T121. The button is drawn
  identically to the nine markdown-snippet buttons beside it (`![]`, same glyph styling), which is
  why the owner did not find it.
- `shared_editor.html`'s missing toolbar is not an ADR-042 constraint — ADR-042 is about the
  token/capability-URL architecture, not the editor's feature set. It is an implementation choice
  made during T147 that was never written down as its own decision (T147's own impact map row
  said "modelled on blog/editor.html — full editor with live preview", i.e. the toolbar was the
  original intent). ADR-044 below records the actual, narrower line: toolbar yes, image pipeline
  no.

## In scope

| Item | Why now |
|------|---------|
| F72 — the photo control in the blog editor is visually its own thing, not one glyph among ten | Owner asked directly; confirmed root cause is discoverability, not a missing feature |
| F73 — each photo gets its own upload progress row, not one shared toast | Owner asked for it; the album uploader already has this pattern (`uploader.js`, `.upload-item`) and the article editor never got it |
| F70 (amended) — the shared-article editor carries the same Markdown toolbar and cheat sheet as the blog editor | Owner asked to reuse the interface; T147's own plan already intended this |
| F75 — on a narrow viewport, source and preview are reachable by a tab switch instead of a scroll past a 22rem textarea | Owner asked for general mobile-writing polish |

## Out of scope this round

| Item | Reason | Recorded as |
|------|--------|-------------|
| Image upload for shared articles | New capability — needs its own storage association (`shared_article` has no image pipeline today) and its own security pass; not what the owner asked to fix this round | ADR-044 |
| Word count / read-time estimate | Not selected at intake | This table (no ADR — never in scope, not a reversal of anything) |
| "Mobile toolbar layout" as its own task | Investigated: `.md-toolbar` already `flex-wrap`s and buttons already meet the 44 px touch target (`blog.css:301-321`); nothing to build beyond F72's own restyle | This table |
| The three pre-existing e2e failures found at Baseline I9 (upload-limit string, two `/dev` board drag tests) | Local-environment drift (`.env`'s `MAX_UPLOAD_MB`, accumulated local dev-DB rows) — not this iteration's surface, not caused by it | `docs/STATUS.md` Baseline I9 |

## Impact map

| Item | Touches | SPEC: changes / preserves | Existing coverage | Class | Regression proof |
|------|---------|---------------------------|-------------------|-------|------------------|
| T148 — shared toolbar primitive | `app/templates/blog/editor.html`, `app/templates/pages/shared_editor.html` (toolbar markup made identical), `app/static/css/blog.css` → `app/static/css/editor.css` (new, shared — toolbar + textarea + preview-pane rules move out of `blog.css` so both pages load one definition instead of two), `app/static/css/shared.css` (drops its now-redundant pane rules), `app/i18n/ru/shared.json` (gains the `md.*`/`toolbar_label` keys `blog.json` already has, or the page reads `blog.json`'s — implementer's call, DoD requires one source of truth, not a copy) | Changes F70's acceptance line in place (adds the toolbar/cheat-sheet clause); preserves F38 (size vocabulary cheat sheet, unchanged content), F50 (unsaved-guard script, already generic via `data-editor-*`) | `e2e/test_editor_guard.py` already parametrizes F50 over both `draft` and `shared_draft` — must keep passing unmodified, it is the regression rail for "touching `editor.js`/either editor template did not break the other's guard" (the exact class of bug `docs/STATUS.md`'s I8 record warns about) | Shared primitive | `test_editor_guard.py`'s 7 tests pass unmodified on both fixtures; new e2e case: every `.md-toolbar__button` present in `blog/editor.html` is also present, with a working action, in `shared_editor.html`, image excepted |
| T149 — discoverable photo control + per-file progress (deps: T148) | `app/static/js/editor.js` (`ACTIONS.image`, `upload`/`uploadOne` rewritten to per-file `XMLHttpRequest` with progress, modelled on `uploader.js`'s `send`/`addRow`/`setState`/`setError`/`addRetry`), `app/templates/blog/editor.html` (photo control gets its own markup outside `.md-toolbar__button`'s glyph row; a queue `<ul>` near it, modelled on `_uploader.html`'s `#upload-queue-wrap`), `app/static/css/editor.css` (new photo-control style; reuses `.upload-item*` from `photo.css` rather than duplicating it — extracted to a shared partial if the two pages that need it, `photo/_uploader.html`'s page and `blog/editor.html`, do not already share a stylesheet) | Adds F72, F73; preserves F51 (server-side validation and HEIC intake unchanged), F40 (article-scoped storage unchanged), the drop/paste paths (`area` listeners, untouched), and `insertAtCursor`'s drop-order guarantee — DoD must state explicitly whether concurrent per-file uploads still insert markdown in drop order or in completion order, since XHR concurrency (album uploader runs 3 at once) can reorder completions | None — `e2e/test_upload_guard.py` covers only the album uploader (`album_page` fixture); the blog editor's image path has zero e2e coverage today | Local (shares `editor.js`/`blog/editor.html` with T148 and T150 — serial after T148, see ordering) | New e2e test: drop two images on the blog editor's textarea, assert two progress rows with distinct states, assert both markdown insertions land in the textarea in the order dropped; existing `test_editor_guard.py` still passes (F50 unaffected by the upload rewrite) |
| T150 — narrow-viewport text/preview switch (deps: T148, T149) | `app/static/css/editor.css` (new tab-switch styles, scoped under the existing `< 60rem` breakpoint), `app/templates/blog/editor.html` + `app/templates/pages/shared_editor.html` (two small tab controls, `aria-controls` the two panes), `app/static/js/editor.js` (small generic toggle, keyed off `data-editor-*` the way the guard already is, so one script serves both pages) | Adds F75; preserves the `@media (min-width: 60rem)` two-column desktop layout untouched, F55 (view/edit mode is orthogonal to this) | None | Local (deps on T148's shared CSS file existing; shares `editor.js`/both templates with T149, hence serial) | New e2e test at a narrow viewport (`e2e/conftest.py`'s existing narrow sizes, e.g. 360/480): typing in the source pane and pressing the switch shows the live-rendered preview without a page scroll; at ≥60rem the switch either does not render or is a no-op and both panes stay visible as today |

**Ordering:** T148 first and alone (shared primitive — both editor templates and the CSS file they
load). T149 then T150, serially, not in parallel — both touch `editor.js` and both editor templates,
so the paths-ownership rule makes them one lane, not two.

## Expectations that change

None. Every existing assertion (`test_editor_guard.py`'s F50 coverage, `test_upload_guard.py`'s
album coverage, `test_authz_sweep.py`) keeps its current meaning; this iteration only adds coverage
where there was none (the blog editor's image path, the shared editor's toolbar).

## Exit criteria

- [x] The blog editor's photo control reads as its own action, distinct from the markdown-snippet
      buttons, and still opens the native file picker via `picker.click()`
- [x] Each photo dropped, pasted or picked gets its own progress row (uploading → done/failed, with
      retry on failure), not a single shared toast
- [x] `shared_editor.html` renders the same `.md-toolbar` (every button but the photo action) and
      the same F38 cheat sheet as `blog/editor.html`, sourced from one shared definition
- [x] On a viewport narrower than 60rem, a switch reaches the live preview without scrolling past
      the full-height textarea; at ≥60rem the existing two-column layout is unchanged
- [x] Baseline suites green at their Phase 0 counts or better: unit/API ≥399, e2e ≥112 passed (the
      3 pre-existing failures are not this iteration's to fix, but not to make worse either), lint
      clean, format clean

**Closed 2026-09-02.** All three tasks (T148, T149, T150) implemented, tested and reviewed on
`iteration/I9-article-editor-ux`; see `docs/STATUS.md` "Resume here" for the closing gates and the
independent review's findings.
