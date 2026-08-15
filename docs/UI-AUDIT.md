# UI Quality Audit Plan — Portfolio (dmkdok)

## Meta

- **Product type:** server-rendered Russian-language portfolio site (FastAPI + Jinja2 + htmx 2), with the
  owner's admin surfaces layered *onto* the public pages rather than into a separate panel.
- **Scope audited:** `app/templates/**` (58 templates), `app/static/css/**` (10 sheets, ~2.4k lines),
  `app/static/js/**` (7 first-party files), plus the view helpers in `app/routers/{pages,photos,blog,projects}.py`
  and `app/services/search.py` that decide what the templates get. Routes: `/`, `/dev`, `/dev/{slug}`,
  `/photo`, `/photo/{slug}`, `/blog`, `/blog/{slug}`, `/blog/{slug}/edit`, `/search`, `/login`, 404/500.
- **Assumptions:**
  - The non-goals in `SPEC.md:211` are binding — nothing below proposes tags, reading time, counters,
    comments, RSS, a contact form, analytics, an English UI, or a separate admin panel.
  - ADR-010 (F12 amended from 44×44 to WCAG 2.5.8's 24×24) is a settled decision, not an open defect.
  - Single admin user; no concurrent editing to design for.
- **Method:** Serena project activation + symbol/pattern navigation, full read of the UI layer, cross-read
  of the existing QA artefacts in `docs/qa/` and the e2e suite. Read-only: **no application file was changed.**
- **Authorities used:** Nielsen 10 usability heuristics (NN/g) · WCAG 2.2 AA · WAI-ARIA APG (toolbar,
  disclosure, modal dialog) · Laws of UX (Fitts, Hick, Doherty, Von Restorff, Jakob) · Apple HIG / Material 3
  touch-target guidance · MDN/W3C `forced-colors` guidance.

## What has since been built — read this before planning from the findings below

**The findings are kept exactly as they were written.** They were an audit, not a
backlog entry, and rewriting them in place would destroy the record of what was
seen. This register says which of them are closed, so nobody re-does the work; it
is the only part of this document that is edited after the fact.

| Finding | State | Where |
|---|---|---|
| **F-001 … F-004** (P1) | Closed | Iteration **I1**, M10 (T102–T105) |
| **F-005, F-006** (P2, taken early) | Closed | Iteration **I1**, M10 (T106) |
| **F-007 … F-015, F-017, F-018** (P2) | Closed | Iteration **I2**, M11 (T107–T116) |
| **F-014** (P2) | Closed | Iteration **I2**, M12 (T120, T123) — built where the control it needed already existed |
| **F-016** (P2) | **Closed as not-a-defect**, ADR-020 | Zero targets failed 2.5.8 at 360 px as admin; its useful half is F-017, which was built |
| **F-023** (P3, cheap) | Closed | Iteration **I2**, M11 (T108) |
| **F-019 … F-022, F-024 … F-026** (P3) | **Open** | Deferred by ADR-017; still the backlog |

Four findings did not survive being measured, and the corrections matter more
than the findings did:

- **F-001** found **no** admin accessibility failures at all — 0 contrast
  samples under threshold, 0 focus stops without an indicator, 0 targets under
  2.5.8. The gap in coverage was real; the defects it predicted were not.
- **F-011**'s overhang does not reproduce. `backdrop-filter` on the capsule
  already makes it a containing block, so the menu has been aligned in every
  browser that supports the property. The declaration was added anyway, as
  insurance rather than as a fix.
- **F-012** was already closed when the audit was written — `markdown.py` has
  emitted named, focusable scroll regions since `2a986ca` (2026-08-08), with
  three unit tests. The audit did not check.
- **F-015**'s prescribed remedy is half a fix on the wrong element. It needs
  `padding-block-end` on `.page` (not `.page__main` — the footer is its sibling
  and carries the very control the finding names) **and**
  `scroll-padding-block-end` on the scroll container, without which the browser
  still scrolls a tabbed-to control to an edge that sits under the bar.

Details of all four: `docs/iterations/I1-ui-audit-p1.md` and
`docs/iterations/I2-pagination-media-phaseb.md`.

## Executive verdict

This is a well-made front end, not a template. The token layer is real (one accent, one focus treatment, a
fluid type scale, `light-dark()` for both themes in a single declaration), the contrast work has been
*measured* rather than asserted, the lightbox does focus trapping and return properly, drag ordering has a
button-based keyboard equivalent, and every mutation reports its outcome. It would survive a senior review
today for the **public** site.

The gap is on the other side of the login. Every automated accessibility gate in `e2e/test_a11y.py` runs
against anonymous pages, so the surfaces the owner actually lives in — the editor, the photo tile tools, the
upload queue, the boards — have never been contrast-checked, focus-swept or target-measured. Underneath that
sit four concrete defects the gate would have caught: focus is dropped whenever an action disables or removes
the control that was pressed, `.button:disabled` has no styling at all, the editor has no unsaved-work guard,
and uploads are validated only after the bytes have already crossed the wire. None of it is a WCAG A/AA
exclusion, so there are **no P0 findings** — but four P1s, and the top three are a day's work between them.

## Scorecard

| Area | Score (1–5) | Notes |
|------|-------------|-------|
| Visual hierarchy & craft | 4 | Confident and restrained. Weak spot: `.label` does ten different jobs at one size and one colour. |
| Interaction & controls | 3 | Toolbar follows APG properly; but no `:disabled`, no `:active`, no pre-upload validation, no upload cancel. |
| Usability (Nielsen + Laws of UX) | 4 | Feedback coverage is unusually complete. Loses points on silent no-ops and silent search truncation. |
| Accessibility (WCAG 2.2 AA) | 4 public / 2 admin | Public side is measured and clean. Admin side is unmeasured, and F-002 is a real keyboard defect. |
| States & feedback | 3 | default/hover/focus/loading/empty/error all present; **disabled** and **active** essentially missing. |
| IA / navigation | 4 | Four sections, one capsule, correct `aria-current`, good empty states. Search truncation is the hole. |
| Architecture fitness for UI | 4 | Layers, tokens and fragment boundaries are disciplined. Some duplicated primitives (chips, error boxes, rows). |
| Ethics (no deceptive patterns) | 5 | Nothing to report. No urgency, no obstruction, no tracking, no forced anything. |

## Critical user journeys

| # | Journey | Steps observed | Friction | Severity |
|---|---------|----------------|----------|----------|
| 1 | Visitor: land → pick a section → read an article | `/` hero + three entry rows → `/blog` → card → article | None material. Cards carry cover/title/excerpt/date and nothing else, by design. | — |
| 2 | Visitor: browse an album | `/photo` → album → contact sheet → lightbox → ←/→ → Esc | Lightbox is solid. On touch there is no swipe; arrows are the only path. | P3 (F-020) |
| 3 | Visitor: search | capsule field → `/search?q=` → grouped results | Each group is silently capped at 12 (`search.py:24`). No count, no "more". | P2 (F-014) |
| 4 | Owner: publish an article | `/blog` → «Новая статья» → editor → type → autosave → «Опубликовать» | Autosave is 2.5 s after the last keystroke; a close/navigate inside that window loses work silently. | P1 (F-003) |
| 5 | Owner: upload an album | album → drop 50 files → watch queue → set cover → set alt → publish | Oversize/wrong-type files are rejected only after upload; no cancel; no retry per row. | P1 (F-004) |
| 6 | Owner: reorder a project or photo by keyboard | Tab to ↑/↓ → Enter → board swaps | Moving to an end disables the pressed button → focus falls to `<body>`. Next Tab restarts at the top of the page. | P1 (F-002) |
| 7 | Owner: edit home copy / footer links | hover the block → «Изменить» appears → edit → save | The affordance is invisible until hover; there is no way to see everything editable at once. | P2 (F-018) |

---

## Findings (ordered P0 → P3)

**P0: none.** No WCAG A/AA exclusion was demonstrated and no deceptive pattern exists on this site.

### F-001 — Every automated a11y gate skips the signed-in UI

- **Severity:** P1
- **Where:** `e2e/test_a11y.py:101` (`PAGES`), `:169`, `:262`, `:456` — all use the anonymous `page` /
  `browser.new_context()` fixtures; `admin_page` appears only in the two keyboard-flow tests.
- **Evidence:** Contrast is sampled on `/`, `/dev`, `/photo`, `/blog`, `/search?q=`, `/login`, a 404 and one
  published album. The focus sweep covers five anonymous paths. Target sizes are measured at 360 px on five
  anonymous paths. The alt-text sweep is anonymous. Nothing measures `/blog/{slug}/edit`, the photo tile
  toolbar, the upload queue, the album/project forms, the admin bar or the site-links editor — i.e. the
  entire surface the product exists to provide.
- **Principle:** WCAG 2.2 conformance applies to all states of a page, not the logged-out one; Nielsen H1.
- **Change:** add (tests only — no app change required to close this finding).
- **Target state:** the four sweeps run over an admin session as well, and either pass or produce a recorded,
  argued exception in `docs/qa/`.
- **Implementation notes for coding agent:**
  1. Parametrise the four tests over `(page, admin_page)` or add an `ADMIN_PAGES` list: `/blog/{slug}/edit`,
     `/photo/{slug}` (as admin, upload zone visible), `/dev` (as admin, board with a form open), `/` (as admin).
  2. The contrast walker already skips `[aria-hidden="true"]` and 1-px clipped text; the hover-only
     affordances (`.editable__edit`, `.photo-item__admin`) are `opacity: 0` and will be filtered by the
     existing `parseFloat(style.opacity) === 0` guard — force them visible first
     (`page.emulate_media(...)` will not do it; add a temporary class or hover the parent).
  3. Expect real failures from `.photo-item__alt-input` and `.upload-item__state` over the translucent
     `.photo-item__admin` scrim — that scrim is `color-mix(... 55%, transparent)` over a photograph, which the
     walker will class as `unmeasurable`, not as a pass. Decide that case explicitly.
  4. Do **not** relax `_threshold()` to make admin text pass.
- **Effort:** M
- **Dependencies:** informs F-005, F-009, F-016.

### F-002 — Focus is dropped when an action disables or removes the control that was pressed

- **Severity:** P1
- **Where:** `app/templates/dev/_project_card.html:77-97` (`#project-{id}-up|-down`),
  `app/templates/photo/_photo_tile.html:67-99` (`#photo-{id}-up|-down`, `#photo-{id}-cover`),
  `app/templates/photo/_album_card.html` (`#album-{id}-up|-down`).
- **Evidence:** htmx captures `document.activeElement` before a swap and restores focus by `id` afterwards
  (confirmed in `app/static/js/vendor/htmx.min.js`, `_e()`), which is exactly why these ids exist — the
  comment in `_album_form.html` says so. But when a move lands an item at an end, the returned button carries
  `disabled`, and a disabled element cannot take focus: the restore silently fails and focus falls to
  `<body>`. The next Tab restarts from the skip link at the top of the document. The ★ "set cover" button is
  worse: `{% if ready and not is_cover %}` deletes it outright, so pressing it always drops focus.
- **Principle:** WCAG 2.4.3 Focus Order (A); Nielsen H3 (user control); APG — a control that acts must leave
  focus somewhere predictable.
- **Change:** alter
- **Target state:** after any board/grid mutation the caret is on a control adjacent to the action taken,
  never on `<body>`. Pressing ↑ on the first item, or ★ on the cover, leaves focus on that same tile.
- **Implementation notes for coding agent:**
  1. Preferred: stop using `disabled` for the end-of-list case. Keep the button enabled, let the endpoint
     no-op (it already does), and pair it with F-006's status message. This fixes F-002 and F-006 together.
  2. If `disabled` must stay: keep the ★ button rendered but `disabled` when the photo *is* the cover, and add
     a fallback in `app/static/js/ui.js` next to the existing `data-autofocus` handler — on
     `htmx:afterSettle`, if `document.activeElement === document.body`, focus the swapped scope's first
     enabled `[id^="photo-"], [id^="project-"], [id^="album-"]` control, else the scope itself.
  3. Do **not** put `tabindex="0"` on disabled buttons — that reintroduces a focusable control with no action.
- **Effort:** S (option 1) / M (option 2)
- **Dependencies:** pairs with F-005 and F-006.

### F-003 — The article editor has no unsaved-work guard

- **Severity:** P1
- **Where:** `app/templates/blog/editor.html:27-34` (`hx-trigger="submit, input delay:2500ms"`),
  `app/static/js/editor.js:42-52` (`setStatus("dirty")`), `app/static/js/ui.js:16-25` (4 s toast).
- **Evidence:** The save-state region correctly flips to «не сохранено» on every keystroke, but nothing stops
  the tab closing, the Back link at `editor.html:20` firing, or a navigation inside the 2.5 s debounce. If the
  autosave *fails*, the only signal is a toast that removes itself after 4 000 ms — and the page then sits
  there looking normal with unsaved text in it. This is the single highest-cost failure mode in the product.
- **Principle:** Nielsen H5 (error prevention), H1 (visibility of system status); Tesler's Law — the
  complexity of "did that save?" belongs in the system.
- **Change:** add
- **Target state:** navigating away with unsaved changes raises the browser's own confirmation; the
  save-state region distinguishes «не сохранено» from «не удалось сохранить» and the failed state persists
  until the next successful save.
- **Implementation notes for coding agent:**
  1. In `editor.js`, hold a `dirty` boolean beside the existing `setStatus` calls — set on `form` `input`,
     clear on a successful `htmx:afterRequest` whose `elt` is the form or `[data-role="save"]`.
  2. `window.addEventListener("beforeunload", (e) => { if (dirty) e.preventDefault(); })`. No custom string —
     browsers ignore it.
  3. Add a `data-failed` attribute to `#save-state` in `_editor_meta.html` (alongside `data-dirty` /
     `data-saving`) with a string from `app/i18n/ru/blog.json`, and call `setStatus("failed")` from an
     `htmx:responseError` / `htmx:sendError` listener scoped to the form. Keep the Russian in the catalogue —
     ADR-007.
  4. Do **not** raise the confirm on the «Опубликовать» / «Открыть» links; both are same-document htmx or an
     intentional exit. Guard on `beforeunload` only.
- **Effort:** S
- **Dependencies:** none.

### F-004 — Uploads are validated only after the bytes have arrived

- **Severity:** P1
- **Where:** `app/static/js/uploader.js:142-157` (`enqueue`), `:171-217` (`send`);
  `app/templates/photo/_uploader.html:5-19` (only `data-max-files` is published to the client);
  `app/static/js/editor.js:293-316` (same for in-article images).
- **Evidence:** The only client-side gate is `maxFiles` (50) and the `accept` attribute — and `accept` does
  not apply to drag-and-drop at all. A 60 MB file, or a HEIC/TIFF dropped on the zone, is uploaded in full
  and then rejected by the server; the owner watches a real progress bar reach 100 % before being told it was
  never going to work. Per `docs/STATUS.md` the cap is 50 MB and the proxy allows 55, so this is a live
  scenario for the owner's own export sizes. There is also no way to cancel an in-flight batch — `pending`
  and the three live `XMLHttpRequest`s have no abort path — and a failed row cannot be retried without
  re-picking the file.
- **Principle:** Nielsen H5 (error prevention) and H9 (recover from errors); Doherty (fail in 400 ms, not in
  90 seconds); Postel's Law.
- **Change:** add
- **Target state:** a file that cannot succeed is rejected before a single byte is sent, with its own reason
  on its own row; a running batch can be stopped; a failed row has a retry button.
- **Implementation notes for coding agent:**
  1. Publish the limits to the client: add `data-max-bytes` and `data-accept` to `#upload-zone` in
     `_uploader.html`, sourced from the same config constant the server validates against — do not hard-code
     50 MB twice.
  2. In `enqueue`, before `addRow`, check `file.size` and `file.type` and push a pre-failed row via the
     existing `setError` path with a specific message from `app/i18n/ru/photo.json`. The row machinery,
     counters and the throttled `announce()` all work unchanged.
  3. Keep each `XMLHttpRequest` on its job object and add a «Отменить» button to `.upload-queue__head` that
     empties `pending` and calls `.abort()` on the active ones — the `abort` listener already exists at
     `uploader.js:211`.
  4. Add a retry button to failed rows that re-pushes the job (the `File` object is still held).
  5. Mirror the size/type pre-check in `editor.js:293` for drag/paste of in-article images.
  6. Do **not** move validation off the server. This is a second, earlier gate, not a replacement.
- **Effort:** M
- **Dependencies:** none.

### F-005 — `.button:disabled` has no styling anywhere

- **Severity:** P2
- **Where:** `app/static/css/components.css:327-379` (`.button` and its modifiers — no `:disabled` rule).
  Only `photo.css:67` (`.photo-icon-button:disabled`) and `photo.css:642` (`.lightbox__control:disabled`)
  define one.
- **Evidence:** The move buttons on `/dev` (`_project_card.html:83,94`) are `.button.button--quiet` with a
  `disabled` attribute and no matching CSS. Because `.button` sets `color` explicitly, the browser's default
  greying never applies: a disabled ↑ on the first project is pixel-identical to a working one. The owner
  clicks it and nothing happens, with no explanation.
- **Principle:** WCAG 1.4.1 (state not conveyed by appearance at all, let alone by colour alone); Norman —
  signifier must match affordance; Nielsen H1.
- **Change:** add
- **Target state:** one `:disabled` treatment shared by every button in the system.
- **Implementation notes for coding agent:**
  1. Add to `components.css` inside `@layer components`, next to `.button--quiet`:
     ```css
     .button:disabled {
       opacity: 0.4;
       cursor: not-allowed;
     }
     .button:disabled:hover {
       color: inherit;
       border-color: var(--line-strong);
       background-color: var(--surface-raised);
     }
     ```
  2. Then delete `.photo-icon-button:disabled` from `photo.css:67` — it becomes redundant.
  3. If F-002 is closed by removing `disabled` from the move buttons, this rule still earns its place: file
     inputs, the lightbox controls and any future disabled state need it.
- **Effort:** S
- **Dependencies:** F-002.

### F-006 — A reorder that cannot happen reports nothing

- **Severity:** P2
- **Where:** `app/routers/photos.py:633` and `:849` (`headers = toast_headers(...) if moved else None`),
  `app/routers/projects.py:432-435` (the toast is inside the `if` that performs the swap);
  `app/templates/photo/_album_form.html` — the ↑/↓ buttons there carry **no** `disabled` attribute at all.
- **Evidence:** Every other mutation in this codebase sends an `HX-Toast` header, and that discipline is one
  of its best features. The no-op branch is the one exception: press ↑ on the first album from inside the
  album edit form and the server swaps the header back identically, sends no toast, and the owner has no way
  to know whether the click registered, the request failed, or the item was already first.
- **Principle:** Nielsen H1 (visibility of system status), H9 (diagnose).
- **Change:** alter
- **Target state:** an impossible move answers with a quiet informational toast («уже первый») rather than
  silence.
- **Implementation notes for coding agent:**
  1. Add `photo.already_first` / `photo.already_last` / `dev.already_first` / `dev.already_last` to the i18n
     catalogues and return them via `toast_headers(..., "info")` on the `not moved` branch. `ui.js` already
     maps an arbitrary `HX-Toast-Kind` onto `toast--{kind}`; add a `.toast--info` rule or reuse the default.
  2. Alternatively — and better — close this with F-002 option 1: keep the buttons enabled, always answer
     with a status. One change, two findings.
- **Effort:** S
- **Dependencies:** F-002.

### F-007 — Error toasts are polite, undismissable and gone in four seconds

- **Severity:** P2
- **Where:** `app/static/js/ui.js:16-25`, `app/templates/base.html:75-84`
  (`aria-live="polite" aria-atomic="false"`), `app/static/css/components.css:677-687`
  (`pointer-events: none`).
- **Evidence:** A failed save, an expired session and a stale CSRF token all surface through the same
  4 000 ms auto-removing toast in a `polite` region with pointer events disabled — so it cannot be dismissed,
  cannot be re-read, and a screen reader that is mid-utterance when it appears may never announce it before
  it is removed from the DOM. `msgFailed` is the message that tells the owner their article did not save.
  Separately, the host sits at `z-index: calc(var(--z-nav) + 1)` = 101 while the lightbox is at 500, so a
  toast raised while the lightbox is open renders behind it.
- **Principle:** WCAG 4.1.3 Status Messages (AA) — errors warrant `role="alert"`; WCAG 2.2.1 Timing
  Adjustable; Nielsen H9.
- **Change:** alter
- **Target state:** error toasts are assertive, persist until dismissed or replaced, and carry a close
  button; success toasts keep the current 4 s behaviour.
- **Implementation notes for coding agent:**
  1. Give the host a second child region with `role="alert"` and route `kind === "error"` into it; keep the
     existing `aria-live="polite"` region for successes. Do not put `role="alert"` on the shared host — every
     success would then interrupt.
  2. Drop the `setTimeout` for errors. Add a «×» button inside `.toast--error` (labelled from the catalogue)
     and give `.toast` `pointer-events: auto` while leaving `.toast-host` at `none`.
  3. Raise `--z-nav + 1` to `calc(var(--z-overlay) + 1)` on `.toast-host`.
  4. Do **not** cap the number of stacked toasts below 3 — losing an error to make room is this finding again.
- **Effort:** S
- **Dependencies:** none.

### F-008 — Form errors are announced once at the top but never bound to the field

- **Severity:** P2
- **Where:** `app/templates/dev/_project_form.html:17-24` and `app/templates/photo/_album_form.html:17-25`
  — a single `role="alert"` paragraph, then `data-autofocus` unconditionally on the *title* field.
  Contrast with `app/templates/partials/site_links_form.html:20-31`, which does it correctly with
  `aria-invalid="true"` + `aria-describedby` per field.
- **Evidence:** Reject a project on its `repo_url` and the caret lands on «Название», the error text lives
  three fields away, and nothing marks which input is at fault. `ui.js:142-150` already contains machinery to
  focus `[aria-invalid='true']` after a swap — these two forms simply never emit the attribute, so the
  handler has nothing to find and the `data-autofocus` fallback wins.
- **Principle:** WCAG 3.3.1 Error Identification (A), 3.3.3 Error Suggestion (AA), 1.3.1 Info and
  Relationships; Nielsen H9.
- **Change:** alter
- **Target state:** the offending field carries `aria-invalid="true"` and `aria-describedby` pointing at its
  own message; focus lands on it; the summary paragraph stays for sighted scanning.
- **Implementation notes for coding agent:**
  1. Change the form-context builders in `app/routers/projects.py` and `app/routers/photos.py` to return the
     error keyed by field name, the way `pages.py` already does for the footer links.
  2. Copy the markup shape from `site_links_form.html` verbatim — it is the house pattern.
  3. Drop the unconditional `data-autofocus` on the title field for the *rejected* render only; `ui.js`'s
     `afterSwap` handler will take over. Keep it for the fresh-form render.
- **Effort:** M
- **Dependencies:** none.

### F-009 — `.label` carries ten different jobs at one size and one colour

- **Severity:** P2
- **Where:** `app/static/css/components.css:7-14` (`.label`), `admin.css:42-48` (`.field__label` — the same
  recipe again), plus `photo.css:271` `.upload-item__state`, `photo.css:412` `.photo-item__state`,
  `blog.css:303` `.editor__summary`, `blog.css:80` `.post-card__date`, `blog.css:157` `.article__date`.
- **Evidence:** Mono + uppercase + `--tracking-label` + `--step--1` + `--text-faint` is currently the visual
  costume for: the home eyebrow, every form field label, the search group headings, the editor pane headings
  (`«Источник»`, `«Просмотр»`), the publication panel heading, the cover heading, upload queue state, photo
  pipeline state, article dates, the settings disclosure summary and the reorder hints. On the editor screen
  seven of those appear at once and rank identically, so the eye gets no structure from them. Separately,
  uppercase Cyrillic at ~13 px with +0.09em tracking is the least legible combination available in this
  system, and it is the one carrying every form label the owner reads.
- **Principle:** Nielsen H8 (aesthetic and minimalist design); Von Restorff (nothing can stand out if
  everything is styled the same); typographic hierarchy.
- **Change:** alter
- **Target state:** three distinct roles, visually separable at a glance — structural eyebrow, form label,
  inline metadata.
- **Implementation notes for coding agent:**
  1. Keep `.label` for the structural eyebrow only (home hero, search group headings, panel headings). Move
     it to `--text-muted` so headings are not the faintest text on the page.
  2. Give `.field__label` sentence case (drop `text-transform` and `--tracking-label`), keep mono, keep
     `--step--1`. Cyrillic form labels become materially easier to read and stop competing with headings.
  3. Introduce `.meta` for dates and pipeline/queue state: mono, `--step--1`, no uppercase, `--text-faint`.
     Point `.post-card__date`, `.article__date`, `.upload-item__state`, `.photo-item__state` at it.
  4. Re-run the contrast sweep afterwards — `--text-faint` currently measures 4.65:1 on `--bg`
     (`docs/qa/contrast-light.json`), i.e. AA with 0.15 of margin. Moving `.label` to `--text-muted` (5.95:1)
     increases the margin; do not move anything the other way.
- **Effort:** M
- **Dependencies:** re-verify with F-001's extended sweep.

### F-010 — Three draft chips and four error boxes for one concept each

- **Severity:** P2
- **Where:** draft markers — `dev.css:127` `.badge`, `photo.css:25` `.photo-badge`, `blog.css:89`
  `.post-flag`. Error boxes — `admin.css:16` `.login__error`, `dev.css:155` `.project-form__error`,
  `photo.css:165` `.album-form__error`, `components.css:600` `.site-links__error`.
- **Evidence:** «Черновик» renders as an accent outline on `/dev`, an accent *wash* on `/photo`, and an
  accent outline with a green `--live` variant on `/blog` — three appearances of one status, on three pages
  of one site. Three of the four error boxes are byte-for-byte identical (`--space-xs var(--space-s)`,
  `--radius-m`, `--danger-wash`, `--danger-ink`, `--step--1`); the fourth differs only in vertical padding.
- **Principle:** Nielsen H4 (consistency and standards); Jakob's Law applied internally — the owner learns
  one site, not three.
- **Change:** rewrite (consolidate)
- **Target state:** one `.status-chip` with `--draft` / `--live` modifiers, and one `.form-error`, both in
  `components.css`; the three section sheets carry no copies.
- **Implementation notes for coding agent:**
  1. Promote `.post-flag` (the most developed of the three — it already has a `--live` variant) into
     `components.css` as `.status-chip` / `.status-chip--live`, and delete `.badge` and `.photo-badge`.
  2. Promote `.project-form__error` into `components.css` as `.form-error`; point all four call sites at it.
     `.login__error` keeps its slightly larger padding only if that is deliberate — otherwise unify.
  3. Update the four templates and `e2e/` selectors that name these classes.
  4. Do **not** touch `.card-grid--posts` while doing this — see F-011's sibling note in the rewrite map.
- **Effort:** M
- **Dependencies:** none.

### F-011 — The mobile nav dropdown positions against the viewport, not the capsule

- **Severity:** P2
- **Where:** `app/static/css/components.css:19-28` (`.nav` — `position: fixed; inset-inline: 0;
  padding-inline: var(--gutter)`), `:30-42` (`.nav__capsule` — no `position`), `:196-208`
  (`.nav__links` — `position: absolute; inset-inline: 0`).
- **Evidence:** `.nav__capsule` is statically positioned, so the absolutely positioned `.nav__links` resolves
  against `.nav`'s **padding box**, which spans the full viewport. The capsule spans the *content* box —
  narrower by `2 × --gutter` (2.5–5 rem). Below 768 px the open menu therefore extends past both edges of the
  capsule it hangs from, with `--radius-l` corners flush to the screen edges. The vertical offset
  (`calc(100% + …)`) is correct because `.nav` has no block padding, which is why this reads as a
  half-finished rule rather than a deliberate full-bleed.
- **Principle:** Visual alignment / common region (Gestalt) — the panel must read as belonging to its trigger.
- **Change:** alter
- **Target state:** at 360 px the open dropdown aligns exactly with the capsule's left and right edges.
- **Implementation notes for coding agent:**
  1. Add `position: relative;` to `.nav__capsule`. Nothing else needs to change — the capsule is
     `inline-size: 100%` below 768 px, so `inset-inline: 0` then resolves to exactly its own edges.
  2. Verify at 360, 480 and 767 px in both themes before and after; capture a screenshot pair into
     `docs/qa/screenshots/` since the existing set is desktop-only.
- **Effort:** S
- **Dependencies:** none.

### F-012 — Scrollable prose regions are neither keyboard-reachable nor named

- **Severity:** P2
- **Where:** `app/static/css/prose.css:91` (`.prose pre { overflow-x: auto }`), `:165`
  (`.prose .table-scroll { overflow-x: auto }`), `blog.css:268` (`.editor__preview { overflow-x: auto }`).
  Emitted by `app/services/markdown.py`.
- **Evidence:** A wide code block or table becomes its own horizontal scroller — which is the right call, and
  `SPEC.md:203` requires it. But the wrapper is a plain `div`/`pre` with no `tabindex`, so in browsers that
  do not auto-focus scroll containers a keyboard user cannot reach the content that is off-screen, and in
  browsers that do, the stop arrives unnamed and unannounced.
- **Principle:** WCAG 2.1.1 Keyboard (A); 4.1.2 Name, Role, Value; 1.3.1.
- **Change:** alter
- **Target state:** every horizontal scroller in prose is `tabindex="0"`, `role="region"` and carries an
  accessible name; it gets the standard focus ring when tabbed to.
- **Implementation notes for coding agent:**
  1. In `app/services/markdown.py`, emit `tabindex="0" role="region" aria-label="…"` on the `.table-scroll`
     wrapper and on `pre` elements. Names come from `app/i18n/ru/blog.json` (ADR-007) — «Таблица», «Код».
  2. Only add `tabindex` when the content actually overflows if you want to avoid dead stops; the simplest
     honest version adds it always, which is what most implementations do and what the WCAG technique
     describes.
  3. The global `:focus-visible` ring already covers the visual side — no new CSS needed.
  4. Do **not** set `display: block` on `<table>` to make it scroll; the comment at `prose.css:160` already
     records why.
- **Effort:** S
- **Dependencies:** none.

### F-013 — No Windows High Contrast support; hover and focus rims vanish

- **Severity:** P2
- **Where:** no `@media (forced-colors: active)` block exists in any of the ten sheets (verified by grep).
  Affected: `photo.css:382-394` (`.photo-item__link::after` — an inset `box-shadow` is the *only* hover and
  focus indicator on every thumbnail), `photo.css:82` (`.photo-drag-chosen`), `components.css:69`
  (`.nav__link:hover` — a `color-mix` background), `components.css:269` (`.entry:hover`).
- **Evidence:** Forced-colors mode discards `box-shadow` and overrides `background-color`. The contact
  sheet's warm rim — the site's entire hover/focus language for photographs — disappears, leaving the thumbnails
  with no focus indicator at all. The global `:focus-visible` outline survives, but `photo.css:396` sets
  `outline-offset: -2px` expecting the rim to carry the weight.
- **Principle:** WCAG 1.4.1 Use of Color / 2.4.7 Focus Visible under forced colours; Microsoft Fluent and
  MDN `forced-colors` guidance.
- **Change:** add
- **Target state:** in forced-colors mode every hover/focus/selected state is expressed with a property that
  survives — `outline`, `border`, or a system colour keyword.
- **Implementation notes for coding agent:**
  1. Add one block per sheet that needs it, e.g. in `photo.css`:
     ```css
     @media (forced-colors: active) {
       .photo-item__link:hover,
       .photo-item__link:focus-visible {
         outline: 2px solid Highlight;
         outline-offset: -2px;
       }
       .photo-drag-chosen { outline: 3px solid Highlight; }
     }
     ```
  2. In `components.css`, give `.nav__link[aria-current="page"]` a `border` under forced colours — the accent
     background that currently marks it will be repainted by the system.
  3. Test in Edge with Settings → Accessibility → Contrast themes. This cannot be automated by the existing
     Playwright sweep; record the result in `docs/qa/` as a manual check.
- **Effort:** S
- **Dependencies:** none.

### F-014 — Search silently truncates each group at twelve

- **Severity:** P2
- **Where:** `app/services/search.py:24` (`DEFAULT_LIMIT = 12`), `:121` (`.limit(DEFAULT_LIMIT)`);
  `app/templates/pages/search.html:36-59` renders the groups with no count and no continuation.
- **Evidence:** A visitor searching a site with thirty articles sees twelve, with no indication that there
  were more and no way to reach them. The page announces truncation of the *query* (`search.too_long`,
  `role="status"`) but never truncation of the *results* — so the site is careful about one and silent about
  the other. There is no result count anywhere on the page.
- **Principle:** Nielsen H1 (visibility of system status); H2 (match the real world — every search UI the
  visitor has used states a count).
- **Change:** add
- **Target state:** the page states how many matches each group has; when a group is capped, it says so.
- **Implementation notes for coding agent:**
  1. Run a `count()` alongside the limited query (cheap — the GIN index is already there) and pass
     `total` per group into the template.
  2. Render it beside the existing `h2.label` group heading: «Статьи · 12 из 27». Strings to
     `app/i18n/ru/common.json`.
  3. Announce the overall count once, in a `role="status"` paragraph next to the existing `.search-note`, so
     a screen-reader user learns the result size without traversing the list.
  4. A "показать ещё" control is optional and larger; the count alone closes the honesty gap. If added, use
     an `hx-get` with an `offset` param and swap the group's `ul` — do not build client-side pagination.
- **Effort:** S (count) / M (with continuation)
- **Dependencies:** none.

### F-015 — The admin bar overlays the bottom of every admin page

- **Severity:** P2
- **Where:** `app/static/css/admin.css:80-97` (`.admin-bar` — `position: fixed; inset-block-end:
  var(--space-s)`), against `layout.css:31-35` (`.page__main` reserves top clearance for the nav but nothing
  for the bar) and `components.css:564-572` — a one-off `margin-block-end: calc(var(--space-s) + 4rem)` on
  `.site-links__edit` below 640 px, whose comment explicitly names the collision.
- **Evidence:** The fix exists once, for one button, at one breakpoint. Everything else at the bottom of an
  admin page sits under the bar: the last row of the contact sheet, the delete button in the publication
  panel, the cancel button of a form scrolled to the bottom. The bar is centred, so it lands on content
  rather than in a margin.
- **Principle:** WCAG 2.4.11 Focus Not Obscured (Minimum, AA) — a focused control under a fixed bar fails it;
  Nielsen H4.
- **Change:** alter
- **Target state:** admin pages reserve bottom clearance globally; the per-component hack is deleted.
- **Implementation notes for coding agent:**
  1. `base.html:52-55` already supports `body_class`. Emit `is-admin` on it when `is_admin` is truthy.
  2. In `admin.css`: `body.is-admin .page__main { padding-block-end: calc(var(--space-3xl) + 4rem); }` — or
     put the clearance on `.site-footer` if the footer should also clear.
  3. Delete `components.css:568-572` once the global rule lands. Leaving both double-spaces that button.
  4. Verify by tabbing to the last control on `/photo/{slug}` as admin at 360 px and confirming the focus
     ring is fully visible.
- **Effort:** S
- **Dependencies:** verified by F-001's extended focus sweep.

### F-016 — Photo tile controls can be clipped on narrow portrait tiles

- **Severity:** P2
- **Where:** `app/static/css/photo.css:342-346` (`--photo-row: 52vw` below 700 px), `:348-358`
  (`.photo-item { aspect-ratio: var(--ratio); overflow: hidden }`), `:452-511`
  (`.photo-item__admin` / `__tools` / `__alt` stacked inside that box), `:514-522`
  (`@media (hover: none)` pins them permanently visible on touch).
- **Evidence:** A 9:16 tile at 360 px is ≈187 px tall and ≈105 px wide. Inside it, `.photo-item__admin` must
  fit a four-button toolbar (each `min-inline-size: 1.9rem` ≈ 30 px, plus padding and a border) *and* a
  full-width alt-text input. The toolbar wraps to two or three rows, the tile clips with
  `overflow: hidden`, and on touch this is the permanent state — the owner cannot hover to reveal a larger
  surface. The existing target-size artefact was captured anonymously (see F-001), so this has never been
  measured.
- **Principle:** WCAG 2.5.8 Target Size and 2.4.11 Focus Not Obscured; Fitts's Law.
- **Change:** alter
- **Target state:** at 360 px every owner control on a portrait tile is fully visible and ≥24×24, or the
  controls move somewhere that can hold them.
- **Implementation notes for coding agent:**
  1. Measure first — reproduce at 360 px with a 9:16 photo before changing anything.
  2. Preferred fix: below 700 px, move `.photo-item__alt` out of the overlay and render it under the tile
     (the grid is a flex contact sheet; a per-tile caption row breaks the ratio maths, so instead render the
     alt inputs as a separate list below the sheet, keyed by tile, when `is_admin` and the viewport is narrow).
  3. Cheaper fix: below 700 px reduce `.photo-item__tools` to two controls (delete, cover) and move ↑/↓ into
     the alt row, or collapse the toolbar behind a single «…» disclosure.
  4. Do **not** solve it by shrinking the buttons below 24 px.
- **Effort:** M
- **Dependencies:** F-001.

### F-017 — Every photo without an owner-written alt gets the same sentence

- **Severity:** P2
- **Where:** `app/routers/photos.py:119-121` (`photo_alt` → `photo.alt or translate(
  "photo.photo_alt_fallback", title=album.title)`), consumed at `_photo_tile.html:22,32` and by the lightbox
  via `data-alt`.
- **Evidence:** The fallback is correct as a floor — `SPEC.md:159` asks for alt on photos and the a11y test
  enforces that none is empty. But a fifty-photo album where the owner has not filled the fields ships fifty
  identical alt strings. For a screen-reader user traversing the contact sheet that is fifty repetitions of
  «Фотография из альбома «…»» — measurably worse than useful, and nothing in the UI tells the owner how many
  photos are still undescribed. The alt input exists (`_photo_tile.html:114-131`) but is inside a hover-only
  overlay with no prompting.
- **Principle:** WCAG 1.1.1 Non-text Content — a name that does not distinguish the image does not describe
  it; W3C alt decision tree; Nielsen H6 (recognition rather than recall).
- **Change:** add
- **Target state:** the owner can see at a glance how many photos lack a description and reach them directly.
- **Implementation notes for coding agent:**
  1. In `_grid.html`, when `is_admin`, render a count beside the existing `.photo-actions__hint`:
     «12 из 50 фото без описания». String to `app/i18n/ru/photo.json`.
  2. Mark undescribed tiles: add a modifier class when `not photo.alt` and give it a dashed accent rim in
     `photo.css`, visible only to the owner (the whole `.photo-item__admin` block is already admin-only).
  3. Leave the server-side fallback exactly as it is — it is the floor, and removing it would reintroduce
     empty alts.
  4. Do **not** auto-generate alt text.
- **Effort:** S
- **Dependencies:** F-016 (same overlay).

### F-018 — In-place edit affordances are hover-only, with no way to see them all

- **Severity:** P2
- **Where:** `app/static/css/admin.css:121-145` (`.editable__edit { opacity: 0 }`, revealed by
  `.editable:hover` or `:focus-visible`), `components.css:527-555` (`.site-links__edit`, same pattern),
  `photo.css:452-483` (`.photo-item__admin`, same pattern).
- **Evidence:** The design decision is sound and deliberate — the admin surface stays invisible until reached,
  which is what "no separate admin panel" (`SPEC.md:211`) buys. The cost is that the owner must already know
  what is editable to discover that it is: on the home page there is nothing to indicate that the eyebrow and
  the intro paragraph are two separate editable blocks, or that the footer links are a third. `@media
  (hover: none)` correctly pins them on touch, so this is a desktop-only gap.
- **Principle:** Nielsen H6 (recognition rather than recall); Norman — a signifier that only appears after
  you have already found the thing signifies nothing.
- **Change:** add
- **Target state:** the owner can reveal every editable region on the current page in one action, without
  changing the resting appearance of the site.
- **Implementation notes for coding agent:**
  1. Add a toggle to `partials/admin_bar.html` — «Показать правки» — that sets a class on `<html>`.
  2. In `admin.css`, `:root.show-edits .editable__edit, :root.show-edits .site-links__edit { opacity: 1 }`
     and the equivalent for `.photo-item__admin`. Persist the choice in `localStorage` the way `theme.js`
     does, and read it in the pre-paint script in `base.html:12-19` so it does not flash.
  3. Give the toggle `aria-pressed` and keep it in sync — and do not repeat F-019 while doing so.
  4. Do **not** make revealed-by-default the resting state; that is the separate-admin-panel outcome the
     brief rejects.
- **Effort:** M
- **Dependencies:** none.

### F-019 — The theme toggle's `aria-pressed` goes stale, and there is no way back to "follow system"

- **Severity:** P3
- **Where:** `app/static/js/theme.js:57-68` (the `prefers-color-scheme` change listener deletes
  `data-theme` but never updates `aria-pressed`), `:51-55` (the click handler only ever writes `light` or
  `dark`).
- **Evidence:** With no explicit choice stored, the OS flipping from dark to light correctly removes
  `data-theme` and repaints the chrome — but the button keeps `aria-pressed="true"`, so the icon says one
  thing and the accessibility tree says another. Separately, once the visitor clicks the toggle even once
  they are pinned to a manual theme forever; `localStorage` is never cleared.
- **Principle:** WCAG 4.1.2 Name, Role, Value; Nielsen H3 (user control and freedom).
- **Change:** alter
- **Target state:** `aria-pressed` always reflects the resolved theme; the visitor can return to following
  the system.
- **Implementation notes for coding agent:**
  1. Extract the `querySelectorAll("[data-theme-toggle]")` loop at `theme.js:70-72` into a `syncButtons()`
     function and call it from the `media` change listener as well as from `apply()`.
  2. For the reset: cycle system → light → dark → system on click, or add a long-press/context action. The
     cycle is simpler but makes `aria-pressed` the wrong ARIA property for a tri-state control — switch to
     `aria-label` reflecting the current mode, or keep two states and put the reset elsewhere. Decide before
     implementing; do not ship a tri-state `aria-pressed`.
- **Effort:** S
- **Dependencies:** none.

### F-020 — Lightbox: no closing transition, background not inert, no swipe

- **Severity:** P3
- **Where:** `app/static/js/lightbox.js:237-254` (`close()` removes `lightbox--open` and sets
  `overlay.hidden = true` in the same frame), `:34-43` (`aria-modal="true"` with no `inert` on `.page`),
  `:322-332` (click-delegated open; no touch handlers).
- **Evidence:** Opening fades in over `--dur` and scales the figure from 0.985; closing snaps, because
  `hidden` applies `display: none` before the transition can start. `aria-modal="true"` is honoured by
  current screen readers, so the missing `inert` is belt-without-braces rather than a defect. On a phone the
  only way between photographs is two 44 px buttons at the bottom corners — no horizontal swipe, which is the
  gesture every photo viewer the visitor has used supports.
- **Principle:** Jakob's Law (swipe); APG Modal Dialog (inert background); Peak-End (the close is the last
  thing the visitor feels).
- **Change:** alter
- **Target state:** the overlay fades out symmetrically; the page behind is `inert`; a horizontal swipe moves
  between photographs and is disabled under reduced motion only if it animates.
- **Implementation notes for coding agent:**
  1. Close: remove `lightbox--open`, then set `overlay.hidden = true` from a `transitionend` listener (with a
     `setTimeout` fallback at `--dur` + 50 ms). Under `reducedMotion()` keep the current immediate path.
  2. `inert`: `document.querySelector(".page").inert = true` on open, `false` on close. `.toast-host` sits
     outside `.page`, so it is unaffected — but see F-007 about its z-index.
  3. Swipe: `pointerdown`/`pointerup` on `.lightbox__figure`, threshold ~50 px horizontal and less than half
     that vertical, calling the existing `show(index ± 1)`. Do not pull in a gesture library — the CSP
     forbids external hosts and the whole site is dependency-light on purpose.
  4. SC 2.5.7 is already satisfied by the buttons, so the swipe is an enhancement, not a requirement.
- **Effort:** M
- **Dependencies:** F-007 (z-index).

### F-021 — External links open in a new tab with no notice

- **Severity:** P3
- **Where:** `partials/site_links.html`, `partials/site_contacts.html`, `dev/_project_card.html:48,53`,
  `dev/detail.html:36,41` — every one is `target="_blank" rel="noopener noreferrer"` with a bare label
  («GitHub», «Открыть репозиторий»).
- **Evidence:** `rel` is correct; the omission is only the warning. Nothing in the accessible name or the
  visible text says the link leaves the site, so Back does not work as the visitor expects.
- **Principle:** WCAG 3.2.5 Change on Request (AAA — advisory at AA); WCAG technique G201; Nielsen H3.
- **Change:** add
- **Target state:** every `target="_blank"` link carries a visually-hidden suffix and, on the chips, a small
  arrow glyph.
- **Implementation notes for coding agent:**
  1. Add `<span class="visually-hidden">{{ t("common.opens_in_new_tab") }}</span>` inside each such anchor;
     the string goes in `app/i18n/ru/common.json`.
  2. Optional visual cue: an `↗` in `.link-chip::after` scoped to `[target="_blank"]`, `aria-hidden` by
     virtue of being generated content.
  3. Five call sites; consider a small Jinja macro rather than five copies.
- **Effort:** S
- **Dependencies:** none.

### F-022 — `.stack` names both a layout utility and the tech-chip component

- **Severity:** P3
- **Where:** `layout.css:47-49` (`.stack > * + * { margin-block-start: var(--flow, var(--space-s)) }`) versus
  `dev.css:106-124` (`.stack` — the dot-separated tech run) used at `dev/_project_card.html:39` and
  `dev/detail.html:27`.
- **Evidence:** No visible bug today: `.stack__item` is `display: inline`, and `margin-block-start` does
  nothing on an inline box. But `layout.css` ships on every page and `dev.css` only on `/dev`, so the utility
  is silently applying to the component wherever both load, and any future change to `.stack__item`'s
  `display` turns it into a layout bug with a non-obvious cause.
- **Principle:** CSS naming hygiene; predictable cascade.
- **Change:** alter
- **Target state:** one name, one meaning.
- **Implementation notes for coding agent:** rename the `/dev` component to `.tech-stack` /
  `.tech-stack__item` in `dev.css` and its two templates. Leave the `layout.css` utility alone — it is the
  more generic claim on the name. Note `e2e/test_a11y.py:448` references `li.stack__item`; update it.
- **Effort:** S
- **Dependencies:** none.

### F-023 — No `:active` state on any button

- **Severity:** P3
- **Where:** `components.css:327-379` — `.button` defines `:hover` and inherits the global `:focus-visible`,
  but no `:active`. Grep across all ten sheets finds `:active` only at `photo.css:52`
  (`.photo-handle:active { cursor: grabbing }`).
- **Evidence:** Pressing a button produces no press feedback in the ~100–300 ms before the htmx response
  lands. The `.htmx-indicator` machinery exists but is opacity-only and no template applies it to a button.
- **Principle:** Doherty Threshold; Norman — feedback must be immediate, not merely eventual.
- **Change:** add
- **Target state:** every button visibly depresses on pointer-down.
- **Implementation notes for coding agent:** one rule — `.button:active:not(:disabled) { scale: 0.97; }`
  plus a `@media (prefers-reduced-motion: reduce)` override setting `scale: 1` and using a background shift
  instead. Keep it under the 250 ms ceiling `e2e/test_a11y.py:211` enforces.
- **Effort:** S
- **Dependencies:** F-005 (`:disabled` must exist for `:not(:disabled)` to mean anything).

### F-024 — The 404 page offers only "home"

- **Severity:** P3
- **Where:** `app/templates/pages/404.html`.
- **Evidence:** Code, title, one sentence, one button to `/`. The nav capsule above carries the four sections
  and the search field, so the visitor is not stranded — but the page itself makes no attempt to recover the
  intent, and a mistyped article slug is the most likely way to arrive here.
- **Principle:** Nielsen H9 (help users recover from errors).
- **Change:** add
- **Target state:** the 404 offers the four sections as entry rows and a prompt to search.
- **Implementation notes for coding agent:** reuse the `.entries` / `.entry` block from
  `pages/home.html:47-64` — it is already a component in `components.css:237-322` and needs no new CSS.
  Keep the primary button.
- **Effort:** S
- **Dependencies:** none.

### F-025 — The mobile nav can flash open before `nav.js` runs

- **Severity:** P3
- **Where:** `base.html:88` (`nav.js` is `defer`red), `app/static/js/nav.js:21-28,53` (`sync()` sets
  `links.hidden = true` only once the script executes), `components.css:196-211` (the dropdown has no
  default hidden state in CSS below 768 px).
- **Evidence:** Deferred scripts run after parsing but the browser may paint first. On a slow first load at
  mobile width, the dropdown can render open — as an absolutely positioned panel over the page — before
  `sync()` hides it.
- **Principle:** Nielsen H1; the theme script at `base.html:12-19` already solves exactly this class of
  problem for the theme, so the pattern exists in-house.
- **Change:** alter
- **Target state:** the mobile menu's resting state is closed from first paint, without JavaScript.
- **Implementation notes for coding agent:** add `hidden` to `.nav__links` in `partials/nav.html` and have
  `nav.js`'s `sync()` clear it above 768 px (which it already does). Because `[hidden]` would then also hide
  the desktop nav for a no-JS visitor, guard it in CSS instead:
  `@media (min-width: 768px) { .nav__links[hidden] { display: flex; } }` — placed in `components.css` so the
  no-JS desktop case still works. Verify the no-JS path on both widths; `SPEC.md:205` requires navigation to
  work without JavaScript.
- **Effort:** S
- **Dependencies:** none.

### F-026 — Six render-blocking stylesheets on an article page

- **Severity:** P3
- **Where:** `base.html:42-48` (base, tokens, layout, components, + admin when signed in) plus each page's
  `head_extra` (`blog.css` + `prose.css` on an article; `photo.css`; `dev.css` + `prose.css`).
- **Evidence:** Six separate render-blocking requests on `/blog/{slug}`. Over HTTP/2 behind Caddy this is
  cheap and the files are small, so this is a note rather than a problem — but it is the one place the site
  pays for its own tidiness, and `docs/qa/perf-article.json` is where the answer lives if it ever matters.
- **Principle:** Doherty Threshold; measured, not assumed.
- **Change:** none unless measured
- **Target state:** LCP stays under the `SPEC.md:143` target of 2.5 s; if it does not, concatenate
  base+tokens+layout+components into one `core.css` at container build time.
- **Implementation notes for coding agent:** check `docs/qa/perf-article.json` first. Do not restructure the
  sheets for a hypothetical gain — the current split is what makes the `@layer` discipline legible.
- **Effort:** S (if ever needed)
- **Dependencies:** none.

---

## Recommended rewrite map

| Module / screen | Action | Replace with / converge to | Priority |
|-----------------|--------|----------------------------|----------|
| `e2e/test_a11y.py` sweeps | refactor | parametrise over anonymous **and** admin sessions | P1 |
| Board/grid reorder controls (`dev`, `photo`, `album`) | refactor | always-enabled buttons + status message; no `disabled`-at-the-end | P1 |
| `app/static/js/editor.js` | refactor | add a `dirty` flag + `beforeunload` + a persistent failed state | P1 |
| `app/static/js/uploader.js` | refactor | pre-flight size/type check, abort path, per-row retry | P1 |
| `.badge` / `.photo-badge` / `.post-flag` | rewrite | one `.status-chip` in `components.css` | P2 |
| `.login__error` / `.project-form__error` / `.album-form__error` / `.site-links__error` | rewrite | one `.form-error` in `components.css` | P2 |
| `.label` family | refactor | split into `.label` (eyebrow) / `.field__label` (sentence case) / `.meta` | P2 |
| `dev/_project_form.html`, `photo/_album_form.html` | refactor | adopt `site_links_form.html`'s per-field `aria-invalid` pattern | P2 |
| `.card` + `.card-grid--posts .post-card` + `.project` | keep for now | three implementations of one media-row idiom; unify only after P1/P2 land | P3 |
| `.stack` (dev) | refactor | rename to `.tech-stack` | P3 |
| Everything else | keep | tokens, layers, lightbox, htmx fragment boundaries, feedback discipline | — |

## Design-system / token actions

**Missing primitives**
- `.button:disabled` — the single largest gap in the component set (F-005).
- `.button:active` — no press feedback anywhere (F-023).
- `.status-chip` — currently three copies (F-010).
- `.form-error` — currently four copies (F-010).
- `.meta` — dates and pipeline state are borrowing `.label` (F-009).

**Token work**
- `--text-faint` is at 4.65:1 on `--bg` in the light theme — AA with 0.15 to spare
  (`docs/qa/contrast-light.json`). Treat it as frozen: any future darkening of `--bg` or lightening of
  `--text-faint` breaks AA, and it currently carries every form label, every eyebrow and every date. Consider
  moving structural labels to `--text-muted` (5.95:1) as part of F-009 to open the margin.
- No `forced-colors` token story at all (F-013).
- The rest of the token layer is genuinely good: one accent with a separately-tuned ink per theme, a single
  focus treatment, a fluid scale with named steps, `light-dark()` so the theme switch is one property. Do not
  restructure it.

**Consistency rules to enforce**
1. One status chip, one error box, one disabled treatment — sheet-level components live in `components.css`,
   section sheets carry only what is genuinely local.
2. Every form that can reject input marks the offending field with `aria-invalid` + `aria-describedby`.
   `site_links_form.html` is the reference implementation.
3. Every mutation answers with a toast — including the no-op branch.
4. Uppercase + `--tracking-label` is reserved for structural eyebrows, never for text the owner must read
   quickly.

## Accessibility remediation queue

Ordered. **A** = closable by extending the existing Playwright sweeps; **M** = manual verification required.

| # | Finding | WCAG SC | Verify |
|---|---------|---------|--------|
| 1 | F-002 focus dropped on disable/removal | 2.4.3 Focus Order (A) | A — extend the focus sweep over admin boards |
| 2 | F-001 admin surfaces unmeasured | 1.4.3, 2.4.7, 2.5.8, 1.1.1 | A — the whole point of this item |
| 3 | F-005 no disabled affordance | 1.4.1 (A) | A — assert a computed style delta on `[disabled]` |
| 4 | F-012 unreachable scroll regions | 2.1.1 (A), 4.1.2 (A) | A — tab into a wide `<pre>` in an article |
| 5 | F-008 errors not bound to fields | 3.3.1 (A), 3.3.3 (AA) | A — submit an invalid `repo_url`, assert `aria-invalid` |
| 6 | F-007 error toasts polite + transient | 4.1.3 (AA), 2.2.1 (A) | M — screen-reader pass (NVDA) |
| 7 | F-015 admin bar obscures focus | 2.4.11 (AA) | A — tab to the last control at 360 px as admin |
| 8 | F-016 clipped tile controls | 2.5.8 (AA), 2.4.11 (AA) | A — measure at 360 px with a 9:16 photo |
| 9 | F-013 forced-colors | 1.4.1 (A), 2.4.7 (AA) | M — Edge contrast theme, cannot be automated |
| 10 | F-017 identical alt across an album | 1.1.1 (A) | M — judgement, not a boolean |
| 11 | F-019 stale `aria-pressed` | 4.1.2 (A) | A — flip `prefers-color-scheme` mid-session |
| 12 | F-021 unannounced new tab | 3.2.5 (AAA, advisory) | A — assert the hidden suffix exists |

Already passing and worth protecting: contrast in both themes (76 samples, zero failures), the focus sweep
across five public paths, reduced-motion (zero surviving animations), motion under 250 ms, alt presence,
skip link → `main`, keyboard login, keyboard article publish, WCAG 2.5.8 at 360 px.

## Architecture actions (UI-enabling only)

1. **Emit `is-admin` on `<body>`** (`base.html:52-55` already plumbs `body_class`). It unblocks F-015 and
   F-018 and removes the need for further per-component hacks like `components.css:568`.
2. **Publish upload limits to the client as data attributes** from the same server constant (F-004). The
   30-vs-50 MB divergence between `Caddyfile` and the app, recorded in `docs/STATUS.md`, is the same class of
   problem one number in one place prevents.
3. **Keep the fragment boundaries as they are.** Every mutation returning the whole surface it changed —
   `#editor-meta`, `#album-head`, `#photo-grid`, `#project-board` — is why state cannot drift here, and the
   comments say so. Do not decompose these into finer swaps to "optimise".
4. **Do not introduce a client-side framework or a build step.** The self-hosted, CSP-strict, no-external-host
   posture is a stated requirement (`SPEC.md:152,192`), and every finding above is closable inside it.

## Phased execution plan

### Phase A — Stop the bleeding (P1)
1. **F-001** — extend the four a11y sweeps to an admin session. Do this *first*: it will confirm or refute
   F-016 and F-015 with numbers instead of arithmetic, and it turns the rest of the phase into a checklist.
2. **F-002** — stop dropping focus. Take option 1 (always-enabled buttons + status), which also closes F-006.
3. **F-003** — `beforeunload` guard and a persistent failed state in the editor. Smallest change, largest
   downside removed.
4. **F-004** — pre-flight upload validation, abort, per-row retry.

Exit criterion: the extended sweeps are green, and a keyboard-only owner can reorder, publish and upload
without losing focus or work.

### Phase B — Coherent product UI (P2)
5. **F-005** + **F-023** — `:disabled` and `:active` on `.button`; delete the `photo.css` duplicate.
6. **F-008** — per-field error binding in the project and album forms, following `site_links_form.html`.
7. **F-010** — consolidate the three chips and four error boxes.
8. **F-009** — split `.label` into three roles; re-run contrast afterwards.
9. **F-007** — assertive, dismissable error toasts; fix the z-index against the lightbox.
10. **F-011** — `position: relative` on `.nav__capsule`; capture mobile screenshots.
11. **F-012** — named, focusable scroll regions in prose.
12. **F-014** — result counts on `/search`.
13. **F-015** — global admin bottom clearance; delete the one-off.
14. **F-016** + **F-017** — tile controls at 360 px, and an undescribed-photo count.
15. **F-013** — a `forced-colors` block per affected sheet.
16. **F-018** — «Показать правки» toggle in the admin bar.

Exit criterion: one chip, one error box, one disabled treatment; every form binds its errors; the admin UI
measures as well as the public one.

### Phase C — Craft & scale (P3)
17. **F-019** theme toggle state · **F-020** lightbox close/inert/swipe · **F-021** new-tab notice ·
    **F-022** `.stack` rename · **F-024** richer 404 · **F-025** no-JS mobile menu state ·
    **F-026** stylesheet count *(only if `docs/qa/perf-article.json` says so)*.

## Definition of done (for a later coding agent)

- [ ] All P1 findings closed; all P2 findings closed or explicitly deferred with a reason in `docs/DECISIONS.md`.
- [ ] `e2e/test_a11y.py` sweeps run over an authenticated session and pass, with any exception argued in
      `docs/qa/` rather than asserted.
- [ ] No control anywhere loses focus to `<body>` after an htmx swap — verified by a keyboard pass over
      `/dev`, `/photo/{slug}` and `/blog/{slug}/edit` as admin.
- [ ] `.button:disabled` and `.button:active` exist and are the only implementations of those states.
- [ ] One `.status-chip` and one `.form-error`; `grep -c` finds no duplicates in the section sheets.
- [ ] Every rejecting form marks the offending field with `aria-invalid` + `aria-describedby`.
- [ ] Every mutation — including a no-op reorder — produces a user-visible outcome.
- [ ] Closing the editor with unsaved text raises the browser confirmation.
- [ ] A 60 MB file and a `.tiff` are rejected before upload begins, each with its own message.
- [ ] The mobile nav dropdown aligns with the capsule at 360, 480 and 767 px, in both themes.
- [ ] A `forced-colors` pass in Edge shows a visible focus indicator on every contact-sheet thumbnail.
- [ ] Contrast re-measured after the `.label` split; no sample below its threshold.
- [ ] `docker compose run --rm tests` and the e2e suite green (never piped through `tail` — see `CLAUDE.md`).
- [ ] No deceptive patterns introduced; no non-goal from `SPEC.md:211` implemented.

## Out of scope / non-issues

Do not spend review time re-litigating these. They are either settled decisions or genuinely good.

- **Target sizes of 34×34 on the nav and theme toggles.** F12 was amended from 44×44 to WCAG 2.5.8's 24×24 by
  **ADR-010**; `docs/qa/target-size-360px.json` records everything between the two bars deliberately, and
  `under_wcag_2_5_8` is empty. Apple HIG's 44 pt and Material's 48 dp remain *comfort* recommendations, not
  conformance — raise them only as an explicit owner decision, not as a defect.
- **The token layer.** `light-dark()` for both themes in one declaration, `color-scheme` as the switch, a
  named fluid scale, one focus treatment site-wide. This is better than most production design systems.
- **The pre-paint theme script** in `base.html:12-19` — correct, nonce'd, and the right shape.
- **Cards carrying no tags, reading time or counters.** Explicit non-goals (`SPEC.md:211`) and stated as a
  requirement in the template comments. Their absence is the design.
- **The contact sheet's ratio-driven flex layout** (`photo.css:325-366`). Unusual, deliberate, well
  documented, and the arithmetic is correct.
- **The Markdown toolbar's keyboard model** (`editor.js:186-219`) — roving tabindex, arrows, Home/End. This is
  the APG toolbar pattern implemented properly, which is rare.
- **`document.execCommand("insertText")`** at `editor.js:71`. Deprecated, but it is the only way to keep the
  browser's native undo stack alive in a textarea, and the fallback path is present.
- **The lightbox's `sizes` arithmetic** (`lightbox.js:128-134`, `:182-192`). Someone thought hard about
  portrait shots and neighbour preloading; leave it alone.
- **`aria-live="off"` on the upload queue** (`_uploader.html:49`) with a throttled `role="status"` sentence
  beside it. This is the correct trade and the comment explains why.
- **`aria-hidden` + `tabindex="-1"` on redundant cover links** (`_post_card.html:12`,
  `_album_card.html`, `_project_card.html:10`). Passes axe's `aria-hidden-focus` rule and is the right way to
  de-duplicate a link. The only nit is `href="{{ target_url or '#' }}"` at `_project_card.html:8`, which
  scrolls to top when a project has neither a detail page nor a repo — render a `<span>` in that branch if
  you happen to be in the file.
- **Ethics.** No forced continuity, no sneak-into-basket, no confirmshaming, no fake urgency or scarcity, no
  obstruction, no roach motel, no disguised ads, no privacy zuckering, no analytics, no third-party requests
  at all. Nothing to report, and the non-goals list is why.
