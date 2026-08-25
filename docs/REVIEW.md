# Review

Eight Phase 6 runs. **Run 8 is the current one and is below**; the earlier seven
are kept underneath it because their findings are the reason half of M9 exists,
and a reviewer arriving later should be able to see what was already looked at.

---

# Run 8 — Phase 6 against I6 (M18), 2026-08-25

Scope is the I6 delta only: `d90ec48..HEAD` (`8c4f0db`) on
`iteration/I6-editing-polish`, judged against the impact map, the non-negotiables
(there are none new this round beyond "no task changes a test that passes
today" — see M-4) and the six exit criteria in
`docs/iterations/I6-editing-polish.md`.

**Independent of the implementing session**: run by a separate reviewer agent
with no write access to application code, in its own context, with `secure-review`
applied to T143 specifically per ADR-040's own instruction. Every count below
was produced by commands that agent ran in this session, on this tree; no claim
in `docs/TASKS.md` or in the iteration record was taken on trust. Semgrep is not
installed on this host; the checklist was applied by hand plus direct runtime
probes (a stubbed `urlopen`, a real browser with the route stubbed, and one live
call to YouTube's own oEmbed endpoint from inside the `web` container).

## Verdict

**PASS with findings, all resolved same day, same branch.** No Critical. One
**High** (H-1) — the button's own next gesture produced a dead link instead of
a player on the most direct path a user would take, defeating T143 entirely on
that path — found by probing the actual browser interaction rather than reading
the code, together with four Mediums and six Lows. All four gates re-run met or
beat their claimed counts before any fix; the security review of T143 found the
SSRF surface provably closed by construction, not merely absent of an example
attack. Every finding below was fixed in this same session before the branch
moved on — see **Resolution**.

## High — fixed

**H-1 — The video button's own next gesture now produces a dead link, and it
defeats T143.** `app/static/js/editor.js:234-238` (pre-fix) left the **caption**
selected; `maybeFillVideoCaption` only fired when the URL landed in the
**address** slot with the caption still untouched. The two halves of this round
fought each other: press «видео», then paste the clipboard's video link
immediately — the ordinary, most direct thing to do — and the paste replaces
the *selected caption*, producing `[https://youtu.be/…](адрес)`, a dead
relative link, not a player. Probed in a real browser with the route stubbed;
nothing in the suite as shipped caught it, because `e2e/test_editor_sheet.py`
asserted only the button's own output and selection, never a subsequent paste,
and T143's client wiring had no e2e case at all. The code matched T142's DoD
exactly ("with the caption words selected first") — the defect was in the plan,
written before T143's trigger was designed, not a deviation from it.

## Medium — fixed

**M-1 — The lookup could steal focus back to the textarea up to 3 s after the
paste.** `replaceRange` calls `area.focus()` unconditionally; the only guard was
that the caption text was unchanged, not that the owner was still in the field.
Probed with a stubbed delay: focus elsewhere before the response, caret pulled
back into `#post-body` with the fetched title selected after it — silently, no
toast, no live region (F-002).

**M-2 — The fetched title reached Markdown source unescaped and uncapped.** No
XSS (`ALLOWED_URL_SCHEMES` and the video-paragraph recogniser both hold), but a
title containing `](` could restructure the link a third party's own text
becomes, and nothing capped its length.

**M-3 — `docs/STATUS.md` contradicted the tree.** Still read "gate approved,
Phase 4 implementation" with Phase 4/5 unticked while `docs/TASKS.md` and the
iteration doc ticked all five tasks and all six exit criteria. Run 7's M-1
recurring, on the one file `CLAUDE.md` sends every resuming session to first.

**M-4 — "Expectations that change: None" was false when it was written.**
T142's own DoD requires `videoAction()` to stop inserting a bare address, which
is exactly what `test_the_video_button_writes_a_paragraph_of_its_own` asserted.
**The rewrite itself was judged the right call and is not undone by this
review** — the old assertion could not survive the approved DoD, the
replacement is the same strength (exact shape *plus* the selection), and the
implementer named the change in the docstring and the commit rather than doing
it quietly. What needed fixing was the record, not the code.

## Low — fixed or carried

- **L-1 fixed** — `response.read()` had no size cap; a trickling host could hold
  a thread-pool worker past the per-operation timeout. Capped at 64 KiB.
- **L-2 fixed** — `url` reaching the route was unbounded; a large value did
  cheap-but-needless regex work and produced a multi-megabyte outbound request.
  Capped at 2048 chars before any pattern match.
- **L-3 carried** — `app/templates/blog/editor.html` moved under T142 but is not
  in that task's declared paths list in `docs/TASKS.md`. Unavoidable (`data-ph-*`
  and the cheat-sheet loop both live there; T139 listed the same file for the
  same reason) — an under-declared plan, not a scope breach. Left as recorded
  here rather than rewriting an already-approved DoD.
- **L-4 fixed as a side effect of H-1's fix** — two pastes into the same slot
  inside the response window could race; the rewritten handler compares the
  *whole line* against what it was when asked, which a second paste always
  changes, so a stale response now always no-ops correctly.
- **L-5 carried** — `e2e/test_me.py`'s empty-state assertion depends on no photo
  anywhere in the shared test database being in flight or failed. True under
  this project's serial e2e run; still an assertion on global state, not a
  regression from this round.
- **L-6 carried** — `app/static/css/photo.css` still calls `.photo-item__admin`
  "the scrim" in its comments although T140 removed what it painted. Cosmetic;
  left for whoever next touches that block.

## Resolution — same day, same branch

Written by the session that acted on this run, appended rather than editing the
findings above, so what was found and what was done about it stay separable.

| | Finding | Disposition |
|---|---|---|
| **H-1** | button's next gesture produced a dead link | **Fixed** — `maybeFillVideoCaption` now recognises either half of the skeleton receiving the paste, resolves the correct address either way, and rebuilds `[title](url)` in the right order regardless of which slot was pasted into |
| **M-1** | fetched title could steal focus back | **Fixed** — `document.activeElement !== area` guards the write-back, alongside the existing unchanged-content check |
| **M-2** | fetched title unescaped and uncapped | **Fixed** — `video_title.py`'s new `_as_caption`: whitespace collapsed, `[`/`]`/`(`/`)` backslash-escaped, capped at 200 chars with an ellipsis |
| **M-3** | `docs/STATUS.md` contradicts the tree | **Fixed** — rewritten at the close of I6 (Phase 7, this session) |
| **M-4** | changed-expectations list was falsely empty | **Fixed** — `docs/iterations/I6-editing-polish.md` "Expectations that change" and the `docs/TASKS.md` M18 preamble both now name the T142 test rename and why |
| **L-1** | unbounded response read | **Fixed** — `response.read(64 * 1024)` |
| **L-2** | unbounded input before regex work | **Fixed** — `len(href) > 2048` refused before any pattern match |
| **L-3** | `editor.html` not in T142's declared paths | **Carried, recorded** — DoD text not rewritten after approval |
| **L-4** | race between two pastes | **Fixed** — subsumed by H-1's whole-line staleness check |
| **L-5** | global-state assumption in `test_me.py` | **Carried, unchanged, as recorded** |
| **L-6** | stale "scrim" comment in `photo.css` | **Carried, unchanged, as recorded** |

**Two new e2e cases, watched failing first against the pre-fix code**, added
alongside the fix in `e2e/test_editor_sheet.py`: pasting the address over the
selected caption (H-1's exact reproduction) and pasting it into the address
slot (the flow T142 was written for) both now resolve to the same fetched,
captioned link — proven with the route stubbed, no real network call, no native
clipboard needed (the paste is simulated by setting the textarea's value and
dispatching a `paste` event, the same technique this suite already uses for
drop events in `e2e/test_upload_guard.py`).

Nine new unit tests in `app/services/video_title.py`'s test file cover the
escaping, the length cap and the read cap directly.

## Gates, re-run after the fix

| Suite | Command | Before fix (this run) | After fix (same session) |
|-------|---------|------------------------|---------------------------|
| unit/API | `docker compose run --rm tests` | **367 passed**, exit 0 | **370 passed**, exit 0 |
| e2e | `uv run pytest e2e -q` | **111 passed**, exit 0 | **113 passed**, exit 0 |
| lint | `uv run ruff check .` | clean | clean |
| format | `uv run ruff format --check .` | **124 files** | **124 files** |

Baseline I6 (Phase 0) was 353 / 110 / clean / 122. Nothing regressed and no
count was overstated. Sweeps re-run after the fix, unchanged from both the
pre-fix run and the Phase 0 baseline: focus **207 / 0** without an indicator
(admin), **88 / 0** (anonymous); contrast **141 / 0** failures (admin, both
themes), **85 / 0** (anonymous, both themes); target-size **171 / 0** and
**65 / 0** under WCAG 2.5.8.

## Exit criteria

| | Criterion | Status |
|---|---|---|
| 1 | a photograph in «Правка» reads sharp under the owner's tools, both themes | **Pass** — verified by grep, not assumption: `.photo-item__tools` and `.photo-item__alt-input` carry their own opaque `--surface-raised` background; nothing rested on the removed scrim |
| 2 | `/me/media` with nothing to flag clears «Файлы на диске» of the empty state's frame | **Pass** — `.empty + .cabinet__group` matches in exactly the one place it needs to (`pages/me_media.html`), verified by grepping every `.empty`/`.cabinet__group` pairing in `app/templates/` |
| 3 | the video toolbar button and the cheat sheet produce a captioned link, not a bare one | **Pass** — and, after H-1's fix, produce one regardless of which slot a follow-up paste lands in |
| 4 | a YouTube or Rutube link inserted through the toolbar fills its own caption from that host's title, editable before save; VK unaffected | **Pass** — live-probed against YouTube's real oEmbed endpoint from inside the `web` container; VK and unrecognised hosts provably never fetched (SSRF probes below) |
| 5 | an uncaptioned-video-first article no longer carries the player's own label in its card or meta description | **Pass** — probed directly: a literal `</button>` typed into an article is escaped and survives (parser has `html: False`); bare video excerpts to `""`; captioned video + prose keeps both sets of words |
| 6 | baseline suites green at Phase 0 counts or better | **Pass** — 370 ≥ 353, 113 ≥ 110, lint and format clean |

## Security

**T143 reviewed specifically, per ADR-040's own instruction.**

- **SSRF — closed, proved not argued.** Eight inputs driven through
  `video_title()` with `urlopen` stubbed: the fetched target's host is always
  `www.youtube.com` or `rutube.ru`, scheme always `https`, regardless of a
  second URL, a redirect parameter or a fragment carried in the submitted
  link's own query string. `file://`, a foreign host wrapping a real video path,
  a VK link and an over-long id all produce **no call at all**. Two independent
  locks: `video_host()` gates on the anchored per-host patterns first, and
  `quote(href, safe="")` percent-encodes `:`, `/`, `?`, `&`, `#`, so the
  submitted link can only ever be a query *value* against a literal host.
- **Authz** — `admin: CurrentAdmin` on the new route; `test_authz_sweep.py`
  walks the whole route tree and would fail on an unguarded mutating route.
- **CSRF** — the route is a POST (not the GET the original DoD sketched — see
  the T143 commit message for why: a GET failing auth redirects to `/login`
  under this project's own 401 handler, which is written for page navigation
  and would hand a JSON-expecting caller a login page's HTML instead of a 401);
  it is therefore correctly inside `_csrf_guard`'s scope, and the client sends
  `csrfHeaders()`.
- **Timeout / blocking** — 3.0 s per socket operation, response body capped at
  64 KiB after this session's fix (L-1); the route is a plain `def`, so FastAPI
  runs it in the thread pool, per ADR-040.
- **XSS** — none: the title reaches the browser as JSON into a textarea value;
  published output still goes through `nh3.clean` with the existing allow-list.
  The residual (Markdown-structure injection via `[`/`]`/`(`/`)` in a title) is
  closed by this session's fix (M-2).
- **Secrets** — none introduced; not holding a VK `access_token` is ADR-040's
  whole point.
- **CSP** — untouched by this delta; the new `fetch` is same-origin.

## What was checked and found clean

- **T144 cannot be defeated from prose.** The renderer's `html: False` means a
  literal `<button class="prose-video__play">…</button>` typed into an article
  is escaped and survives the excerpt rather than being stripped as if it were
  the real control; the regex in `excerpt_from` runs only on the renderer's own
  output, never on raw input.
- **The `video_host` refactor loosened nothing.** `_VIDEO_SERVICES`'s five
  patterns are byte-identical to before T143; `video_embed` and `video_host`
  both still `fullmatch` on the stripped input.
- **Ordering held and scope held.** T140/T141/T144 touch disjoint files; T142
  precedes T143; the only file outside a declared task path is `editor.html`
  (L-3, carried).

## Carried, with reasons

- **T140 has no automated proof and cannot have one.** "Reads sharp in both
  themes" is not measurable by the contrast sweep — the CSS half was verified
  by grep, the visual half is the owner's, per the impact map's own plan.
- **The route has no rate limit**, consistent with every route on this site
  except login; admin-gated.

Scope is the I5 delta only: `5bd408f..HEAD` (`33381b5`) on
`iteration/I5-authoring`, judged against the impact map, the non-negotiables and
the eight exit criteria in `docs/iterations/I5-authoring.md`.

**Independent of the implementing sessions.** Every number below was produced by
commands run in this session, on this tree; no claim in `docs/TASKS.md` or in the
iteration record was taken on trust.

## Verdict

**PASS.** All five tasks in M17 are implemented, all three gates re-run green at
or above the counts the tasks claim, and the six things the intake called
non-negotiable hold. One **High** finding and four Mediums are open; none is a
security finding, and none of them is a reason to send the branch back to
implementation — but **H-1 should be closed, or given an ADR, before M17 is
ticked**, because it is the one place where «Просмотр» is not the page a visitor
reads.

## Resolution — same day, same branch

Written by the session that acted on this run, appended rather than editing the
findings above, so what was found and what was done about it stay separable.

| | Finding | Disposition |
|---|---|---|
| **H-1** | `/dev` draggable in «Просмотр» | **Fixed**, `app/templates/dev/_project_card.html`, `app/static/css/dev.css`, `app/static/js/dev-sortable.js` |
| **M-1** | `docs/STATUS.md` contradicts the tree | **Fixed** — rewritten at the close of I5 |
| **M-2** | a video's label opens the meta description | **Deferred, recorded** — **ADR-038** |
| **M-3** | a facade can render where `video.js` is not loaded | **Deferred, recorded** — **ADR-039** |
| **M-4** | uncommitted `docs/qa/*` artefacts | **Fixed** — regenerated by the closing runs and committed |
| Low ×5 | listed above | Carried, unchanged, as recorded |

**H-1 took the alternative this run named second, not the one it named first.**
A drag handle now exists as an element of its own — `<span class="project__handle"
data-drag-handle>` inside `.project__admin owner-only` — and `dev-sortable.js`
drags from `[data-drag-handle]`, the hook `photo-sortable.js` already uses. The
first suggestion, teaching the script to read `show-edits`, was rejected because
ADR-032's decision is that **one** mechanism decides the mode: a second reader in
JavaScript would have to be re-evaluated on every mode change and after every
htmx swap, and would be the only place in the product where the marker is not
what takes an affordance away. The chosen shape needs no mode logic at all — in
«Просмотр» the row has no box, so there is nothing to grab. `.project__handle` is
restated in `dev.css` rather than shared with `.photo-handle`, which lives in
`photo.css` and is not loaded on `/dev`; unifying the two is a candidate for the
next intake, not a review fix.

**Three checks, watched failing first**, all in `e2e/test_view_parity.py`:
`[data-drag-handle]` joins the named owner surfaces; a drag from where it used to
work must post nothing to `/dev/admin/order` and must leave the order unchanged
after a reload; and the handle in «Правка» must still reorder the board, so the
fix cannot pass by breaking dragging altogether.

**Two things about that red run are worth keeping.** The first version passed on
the broken tree twice, for two different wrong reasons: `bounding_box()` is
viewport-relative, so cards below the fold handed back coordinates the mouse
could not reach and the drag never started; and once it did start, `reload()`
immediately after `mouse.up()` aborted the htmx POST before it landed, so the
server order was read as unchanged. A drag test that asserts «nothing happened»
is a test that passes when nothing happened *for any reason at all* — this one
now asserts on the request, which exists if and only if a drop did.

Gates after the fix, none piped: unit/API **353** exit 0, e2e **110** exit 0
(107 before, `+3`), `ruff check` clean, `ruff format --check` **122 files** exit 0.
Admin sweeps re-run and unchanged: focus **207 stops / 0** without an indicator,
targets **171 under 44 px / 0** under WCAG 2.5.8, contrast **141 samples / 0
failures** in both themes — the new handle is `aria-hidden`, not focusable, and
its 1.7 rem box clears 24 px.

**Exit criterion 8 is still outstanding and M17 is not ticked.**

## Gates, re-run in this session

| Suite | Command | Result | Claimed by T139 |
|-------|---------|--------|-----------------|
| unit/API | `docker compose run --rm tests` | **353 passed**, exit 0 | 353, exit 0 ✔ |
| e2e | `uv run pytest e2e` | **107 passed**, exit 0 | 107, exit 0 ✔ |
| lint | `uv run ruff check .` | `All checks passed!`, exit 0 | clean ✔ |
| format | `uv run ruff format --check .` | **122 files** already formatted, exit 0 | 122 files, exit 0 ✔ |

Baselines were 289 / 92 / clean / 118. Nothing regressed and no count was
overstated.

## Exit criteria

| | Criterion | Status |
|---|---|---|
| 1 | baseline counts or better, exit 0 | **Pass** — 353 ≥ 289, 107 ≥ 92 |
| 2 | `ruff check` and `ruff format --check` exit 0 | **Pass** |
| 3 | each of A–F has a check watched failing first | **Pass on the record** — every red run is written up in the iteration doc, including the three that were worthless and why (T136 n2, T137 n9, T139 n7). Not re-derivable in review; taken as recorded because the record is specific about what failed and on what assertion |
| 4 | «Просмотр» presents the same **rendered boxes** as a visitor on five pages | **Pass** — `e2e/test_view_parity.py`, plus four named-surface checks. See **H-1**: the criterion is about boxes and a drag target is not a box |
| 5 | visitor guard finds no owner markup / `admin.css` / `edits.js` / `owner-only` | **Pass** — `owner-only` joined `ADMIN_MARKERS` (`tests/api/test_authz_sweep.py:136`); the list only grew |
| 6 | a video article carries no `iframe` and reaches no host until the press | **Pass** — `e2e/test_video.py` watches requests against six hosts; independently probed: raw `<iframe>` is escaped, `youtube.com.evil.example/watch?v=…` stays an ordinary link, a video link among text stays a link |
| 7 | both a11y sweeps over all three rooms, both themes | **Pass** — `/me`, `/me/stats`, `/me/media` all in `admin_surfaces` (`e2e/conftest.py:260-268`); artefacts: contrast 141 samples / 0 failures both admin themes, 85 / 0 both anonymous; focus 207 stops / 0 without an indicator (admin), 88 / 0 (anonymous); targets 171 under 44 px / **0** under WCAG 2.5.8 |
| 8 | **the owner writes an article with a sized picture and a video from the cheat sheet alone, publishes it, reads it in both modes** | **Outstanding.** No test stands in for it, by the criterion's own wording. It is the owner's, and M17 is not finished without it |

## Non-negotiables

1. **A visitor's HTML is unchanged** — holds. `owner-only` joined the marker list rather than replacing anything.
2. **The CSP stays strict** — holds, and is now asserted directive by directive rather than by substring (`test_the_policy_names_three_frame_hosts_and_widens_nothing_else`). `frame-src` is the only line naming a foreign host; `img-src` is still `'self' data:`.
3. **Raw HTML off at the parser, `iframe` never in `ALLOWED_TAGS`** — holds, probed directly. `ALLOWED_TAGS` gained `button` only; `span` gained `aria-hidden`; the `data-video` value is built by `video_embed()` from anchored per-host patterns whose groups are `[A-Za-z0-9_-]{6,24}`, 32 hex, or digits.
4. **Every mutating route keeps `CurrentAdmin`; nothing joins the allow-list** — holds. I5 added four routes, all `GET`, all reads, all behind `me._require_owner` → 404 without a session. `test_authz_sweep.py`'s allow-lists are untouched.
5. **No migration, no new model** — holds. Every figure in «Сводка» is a `count()`/`sum()` over existing tables.
6. **F-002 for every new control** — holds: the video facade hands the caret to the `<iframe>` that replaces it (asserted in e2e), «Проверить» answers into a separate region so the caret stays on the button, and the two new toolbar buttons add no focus stop because the toolbar is one stop with arrow keys inside.

## High

**H-1 — In «Просмотр», `/dev` can still be reordered by dragging.**
`app/static/js/dev-sortable.js:20` uses `handle: ".project__body"` — the card
body itself, which is present and laid out in both modes and carries no
`owner-only`. The script is loaded whenever `is_admin`
(`app/templates/dev/index.html:22-25`) and nothing in it reads the mode, so in
«Просмотр» the owner can drag a project card by its summary text and the drop
silently `POST`s `/dev/admin/order`, changing the public order of the project
list from the page that claims to be the visitor's page.

Verified in a browser, not inferred. A temporary probe against the running app
in «Просмотр» on `/dev` returned:

```
{'sortable_initialised': True, 'sortable_lib_loaded': True, 'project_count': 3,
 'body_boxes': 1, 'board_actions_boxes': 0, 'editing': False}
```

— the board's own action row is correctly gone (0 boxes) while the drag target
is live. The same probe on `/photo` returned `handle_boxes: 0`, so the album
board and the photo grid are **correct**: `photo-sortable.js:54` uses
`handle: "[data-drag-handle]"` and that handle sits inside
`.album-card__admin owner-only` / `.photo-item__admin owner-only`, so
`display: none` takes the grab target away with everything else.

`/dev` is the one surface where the handle is not an element of its own, which
is exactly why the marker could not reach it. Intake item **A**'s acceptance
says "no drag handle"; exit criterion 4 measures boxes, and a drag target is not
a box, so nothing in the suite could have caught this.

Smallest honest fix: give `dev-sortable.js` the same mode read `edits.js`
already performs — refuse to initialise, or `option("disabled", true)`, unless
`document.documentElement.classList.contains("show-edits")`, re-evaluated on
mode change and after an htmx swap. The alternative is a real handle element
inside `.project__admin`, which is the shape the other two boards already have
and would need no JavaScript mode logic at all. Either way it needs an e2e check
that asserts the drag cannot start in «Просмотр» — a box check will not do it.

## Medium

**M-1 — `docs/STATUS.md` contradicts the tree.** The handoff says
"**T135 is done** — … T136–T139 are no longer blocked", and its progress block
still shows `- [ ] 4 implementation`, while T136–T139 are committed
(`584e561`, `ea3e1bf`, `c59260a`, `33381b5`) and ticked in `docs/TASKS.md`.
`CLAUDE.md` makes STATUS.md the one document a resuming session reads first, so
a stale one is the specific failure that instruction exists to prevent. It also
still carries I4's "Resume here" as if current.

**M-2 — a video at the top of an article poisons its meta description.**
`excerpt_from` strips tags and keeps text, and the facade's own label is text.
Probed:

```
excerpt_from('https://youtu.be/…\n\nОстальной текст статьи.')
  → '▶Смотреть видео Остальной текст статьи.'
```

so the `<meta name="description">` and the card note on `/blog` open with a
control's label. Named honestly in the iteration record (T138 n10) as
"a known wart… it belongs in the next intake", and it is not a regression — the
same article used to get the raw URL there. But it is **not recorded in
`docs/DECISIONS.md`**, and the review checklist's rule is that an in-scope item
left undone is deferred in DECISIONS.md, not in a narrative. Either an ADR or a
line in the next intake's "Out, with reasons"; the fix itself is one branch in
`excerpt_from` that skips a `figure.prose-video`.

**M-3 — a facade can render where `video.js` is not loaded.**
`video.js` is included by `blog/post.html:66`, `dev/detail.html:68` and
`blog/editor.html:226` only. The home page's editable blocks go through the same
block-level `render_markdown` (`app/routers/pages.py:45,108`), so an editable
block whose paragraph is nothing but a supported video link renders a
`<button class="prose-video__play">` with an accessible name and no listener —
a control that does nothing when pressed. Unlikely content for the hero or the
intro, and harmless if it never happens; the DoD's wording is "loaded only on
pages that render prose", and the home page is one. Fix is one script tag, or a
guard that keeps `_figure_paragraphs` from making a facade outside article prose.

**M-4 — the working tree is not clean.** Twelve `docs/qa/*.json` artefacts and
`docs/qa/screenshots/forced-colors-photo.jpg` are modified and uncommitted; they
were already modified before this review ran anything. Every headline number is
**identical** to what is committed — checked field by field: 207/0, 88/0,
171/0, 65/0, 141/0 ×2, 85/0 ×2 — so the churn is `recorded` dates and per-run
identifiers only. Commit or `git restore` before the milestone closes, so the
next baseline is taken on a clean tree.

## Low / polish

- **`video.js:31` sets `iframe.src` from `data-video` with no check of its own.** The value is renderer-closed and `frame-src` names three hosts, so this is defence in depth rather than a hole — but a one-line prefix test against the three embed roots would make the script safe to read in isolation, which is how it will be read.
- **`app/services/search.py:179,186` reuses the name `prefix`** for the prefix `tsquery` and then for `URL_PREFIXES[kind]`. Correct, since the first is consumed before the second is bound, and confusing in a function whose subject is a prefix.
- **The orphan list is unbounded** (`partials/orphan_scan.html:9`) while the empty-directory list is capped at ten with a "and N more" line. On the storage this room exists to describe, the unbounded list is the one that can be long.
- **`storage.empty_directories()` reports one level per run.** A parent holding only an empty child is not empty at walk time, so nested shells need repeated `--prune` runs. Behaviour is byte-identical to the pre-I5 script (the function moved unchanged), so it is not a finding against this iteration — recorded because the docstring's "so a parent empties in turn" reads like a promise it does not make.
- **`show-edits` survives in three CSS rules, not the two T135's DoD predicted.** Not a defect: the third is `.photo-item--undescribed`, a modifier on the tile, and the iteration record states the narrower true claim ("one mechanism decides visibility, and two decorations read the mode") rather than the DoD's. Verified: `admin.css:22`, `admin.css:287`, `photo.css:349`.
- **Carried forward, unchanged by I5:** M16 is still open (T128 and T129 need the appliance), and I4's exit criterion 7 — the owner's own pass through a publishing flow — is still outstanding alongside I5's criterion 8.

## What was checked and found sound

- **Sanitiser and CSP.** `iframe` absent from `ALLOWED_TAGS`; a hand-written `<iframe>` comes back escaped; `button` reachable from the renderer only (raw HTML off at the parser, `attrs_plugin` restricted to images and `class`); CSP built in one place (`app/main.py:142-160`) and stamped on 500s too.
- **The prefix search cannot 500 the page.** `_TSQUERY_SYNTAX` strips `&|!()<>:*'"\`. Fourteen hostile single-token queries were pushed through the real `to_tsquery('russian', …)` in the project's Postgres — `-`, `--`, `.`, `_`, `+`, `~`, `@`, `#`, `%`, `^`, `=`, `/`, `\`, `a-`, each with `:*` appended — and every one returned the harmless "contains only stop words" notice, not `syntax error in tsquery`. The union shape means no existing search assertion changed, which the unchanged `e2e/test_search.py` confirms.
- **Every i18n key resolves.** A sweep over all six catalogues against every `t(...)`/`translate(...)` in `app/**/*.html` and `app/**/*.py`, including the five dynamic prefixes (`blog.md.sheet_`, `blog.md.size_`, `me.room_`, `me.panel_`, `me.` for group and figure keys) and all four `PhotoStatus` members, found **no missing key** — so nothing on a new surface can render as its own dotted name.
- **The cabinet's authorisation.** Four routes, one `_require_owner` written once and called by each; 404 rather than a redirect, so no address confirms itself. `Disallow: /me` (`app/routers/seo.py:36`) covers all three rooms by prefix; `pages/me_base.html` carries `noindex, nofollow` structurally, so a fourth room inherits both.
- **The rooms as UI.** `partials/cabinet_nav.html` is a real `<nav>` of links with `aria-current="page"`, not a button row; `forced-colors` gets a border where the accent is dropped; «Сводка» is `auto-fit` grid with no breakpoint of its own; `.cabinet__stem` uses `overflow-wrap: anywhere` for paths; the scan answers into an `aria-live="polite"` region so the caret stays on «Проверить».
- **The script move is faithful.** `scripts/media_orphans.py` keeps its own byte ladder and its `--prune`; the walk moved to `app/services/storage.py` with the empty-directory pass deliberately left outside `scan()` so a prune still reports and removes in one run. Printed output order is unchanged.
- **Diffs are surgical.** No drive-by refactors; no `TODO`, `FIXME` or placeholder text anywhere in `app/`, `scripts/`, `e2e/` or `tests/`; no secret in the diff. The two tail commits in the range (`4ae4559` tooling, `52ee292` QA artefacts) touch **no** application code, confirmed by `git diff 5bd408f 534958d -- app/ tests/ e2e/ scripts/` returning empty.
- **Dependency hygiene.** `pyproject.toml`, `uv.lock`, both compose files and the Dockerfiles are untouched by the whole range — I5 introduces no new package and no new image. The video player is 45 lines of vendorless JavaScript precisely so that it would not.
- **`secure-review` scope.** Run as the manual checklist; Semgrep is not installed on this host and no scan was fabricated. Secrets, authorisation, injection (SQL and tsquery), XSS through the sanitiser, CSRF on the new routes (none mutate), risky defaults and dependency hygiene were each checked and are listed above. **No Critical or High security finding.** H-1 is a correctness and product finding, not a security one: `/dev/admin/order` still requires `CurrentAdmin`, so nobody but the owner can reach it.

---

# Run 6 — Phase 6 against I4 (M16), 2026-08-16

Scope is the I4 delta only: `a0d1ecf..HEAD` on `iteration/I4-editing-mode`,
judged against the impact map in `docs/iterations/I4-editing-mode.md`.

**Like Run 5, this is a self-review and not an independent one.** It was written
by the session that implemented T132 and T133, so it can check that the diff
stayed inside its owned paths — and did — but it cannot catch what the
implementer did not think to look for. An independent pass before this branch
merges is a reasonable call and nothing below depends on one having been done.

## Verdict

**PASS.** All four tasks in M16 are implemented, each with a check watched
failing first, and both baseline suites are above their baseline counts. The one
exit criterion no test can stand in for — the owner's own pass through a full
publishing flow using only the new menu and the new mode — is outstanding and
is his by definition.

## Regression against the impact map

| Item | Proof named in the map | Status |
|------|------------------------|--------|
| **A** bar → capsule menu | visitor HTML carries no owner marker; focus sweep still finds every stop; the page reserves no bottom clearance | Pass — T131, `cc403a5`; the clearance check compares the document's tail, 88 px → 0 |
| **B** mode replaces hover | on «Просмотр» the three families are absent from the accessibility tree, not transparent; on «Правка» all three visible with no pointer | Pass — `e2e/test_show_edits.py` rewritten, watched failing on *"Locator expected to have count '0'; Actual value: 1"* against the unchanged tree |
| **C** the cabinet at `/me` | anonymous gets 404; the page appears in both admin sweeps; every existing suite unchanged | Pass — `tests/api/test_me.py` (8) and `e2e/test_me.py` (4), `/me` in `admin_surfaces`, contrast · focus · target-size all green in both themes |
| **D** `docs/` out of ruff | `ruff format --check .` exits 0 and the I3 excerpt is untouched | Pass — T134, `1eec8cb` |

**Paths that moved and were not on a task's list, each declared rather than
discovered here:**

- `e2e/test_home_editing.py`, `e2e/test_site_links.py`, `e2e/test_album_upload.py`
  — seven in-place editing flows that clicked an affordance «Просмотр» now
  removes. One idempotent `switch_mode(page, "edit")` each, in the helper those
  files already shared. Written up as T132 landed §3.
- `tests/api/test_authz_sweep.py` — beyond T131's marker line, the guard was
  parametrized over four public pages and gained `admin.css` and `edits.js`,
  because **exit criterion 4 asks for all four pages and both assets and the
  guard checked one page and neither asset.** That is Phase 5 closing a
  criterion, not Phase 4 widening scope; it is its own commit (`c5fba5b`).
- `app/static/css/me.css` — a new file no task listed. CONVENTIONS asks for one
  stylesheet per feature area; the alternative was reusing search's `.results`
  primitives and coupling two pages through a third area's file.

**Nothing else moved.** `app/routers/photos.py` in particular is untouched: the
cabinet reuses the retry endpoint exactly as it is, which is what forced the
`hx-swap="none"` decision recorded in the iteration page.

## Security

**Tooling:** manual — `semgrep` is not installed on this host, so the checklist
below was carried by hand over the diff.

| ID | Severity | Issue | Where | Fix |
|----|----------|-------|-------|-----|
| S-101 | Low (informational) | `Disallow: /me` names in a world-readable file the very path the 404 is designed not to confirm. The two requirements are in mild tension and **both** come from ADR-029. | `app/routers/seo.py` | Not changed. The route answers 404 without a session, so knowing the path exists gains nothing, and this repository is public — the route list is already public. `noindex` alone would in fact suffice, since no crawler can fetch the page at all. |
| S-102 | Low | The cabinet's retry can be pressed repeatedly, re-queueing a photograph that is already `PENDING`. | `app/templates/partials/cabinet_group.html` | Not changed. The endpoint is `CurrentAdmin`, the work is one photograph, and the tile this control was taken from behaves identically — it is the shape of the existing action, not something the cabinet introduced. |

**No critical or high findings in the scoped review.** What was checked and
found clean:

- **Authorisation.** `/me` takes `OptionalAdmin` and raises 404, deliberately
  not `CurrentAdmin` — which answers 401 and is turned into a redirect to
  `/login` by `main.py`, telling a stranger the page is there. No mutating route
  was added, nothing joined an allow-list, and
  `test_every_mutating_route_rejects_anonymous` passes unchanged. There is no
  IDOR surface: the only id in the diff is the retry's `photo_id`, on an
  endpoint that already required a session, on a site with exactly one account.
- **Injection and XSS.** Every query in `app/routers/me.py` is an ORM select
  with no request input in it — the route takes no parameters at all. Jinja
  autoescape is on and **neither new template uses `|safe`**, so `photo.error`
  (the one string on the page that comes from the pipeline rather than the
  catalogue) is escaped.
- **CSP.** The new page adds no inline `<script>` and no inline `style=`. The
  retry is htmx, so it carries the CSRF token from `hx-headers` on `<body>`
  exactly as every other admin action does.
- **What a visitor receives.** Strengthened rather than merely preserved: the
  sweep now proves across `/`, `/dev`, `/photo` and `/blog` that no owner
  marker, no `admin.css` and no `edits.js` reaches an anonymous request, and a
  companion test proves the owner's own page still carries all of them — so a
  marker naming a renamed asset cannot satisfy the guard for free.
- **Secrets and supply chain.** No dependency changed; `uv.lock` untouched;
  `.env` is gitignored and `.env.example` still carries placeholders. The
  cabinet states *where* the password lives and shows no value, and no form on
  it posts a credential (ADR-029).

## Notes — recorded, not fixed

1. **The undescribed list is unbounded and its rows are indistinguishable.** On
   the owner's real data it renders 24 rows all reading «Снимок в альбоме «X»»,
   told apart only by where they lead. Nothing in the delta asked for
   thumbnails, grouping or a cap, so nothing was added — and it is evidence for
   the trigger ADR-029 records: if a pain appears, it will be photographs at
   scale. A line for the next intake.
2. **ADR-029's consequences say `/me` joins the parametrized admin-read case in
   `test_authz_sweep.py`. It does not, and must not** — that case asserts
   redirect-to-login semantics, which this route deliberately does not have. The
   impact map said so first; both statements are in the record.

## Gates at the time of this verdict

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **289 passed**, exit 0 (277 at baseline) |
| e2e | `uv run pytest e2e` | **92 passed**, exit 0 (81 at baseline, 88 after T131) |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | clean, 118 files |

None piped. The baseline's intermittent 500 did not recur, and neither did the
unexplained login failure recorded in I3.

---

# Run 5 — Phase 6 against I3 (M15), 2026-08-15

Scope is the I3 delta only: `8c75582..HEAD` on `iteration/I3-operations`, judged
against the impact map in `docs/iterations/I3-operations.md`.

**This run is weaker than the four below it, and the difference is worth
stating.** Runs 1–4 used reviewers that had not written the code. This one was a
single pass by the session that implemented the work, so it can catch a diff that
strayed outside its owned paths — and did check that — but it cannot catch what
the implementer did not think to look for. If the owner wants Run 5 redone
independently before this branch merges, that is a reasonable call; nothing below
depends on it having been done.

## Verdict

**PASS on what was run. Three of the six tasks are not finished and are not
ticked** — their remaining halves are owner actions on the appliance and on
GitHub, and no part of this review claims them.

## Regression against the impact map

| Item | Proof named in the map | Status |
|------|------------------------|--------|
| **T125** dedup race | API test patching `renditions_of` to empty the disk between the two globs; 201 + `PENDING` | Pass — `tests/api/test_photo.py::test_a_known_frame_whose_files_vanish_mid_request_is_re_rendered`, shipped `4255ec4` |
| **T130** stuck after the render | two tests, one per named window, each asserting `FAILED` with a reason rather than a spinning tile | Pass — both watched failing first on `AssertionError: photo N never left the pipeline`, the traceback naming `submit_with_session` swallowing the raise |
| **T126** the log as a file | unset writes nothing and adds no handler; set reaches `app.log`; unwritable still starts and warns | Pass — `tests/unit/test_logging.py`, 3 cases, watched failing on `ImportError` first |
| **T126** mount and ceilings | `docker compose config` renders both files with `max-size`/`max-file` on every service and the log mount on `web` | Pass — both rendered, ceiling on all three services in each, `LOG_DIR: /data/logs` and the `/data/logs` target on `web` |
| **T127** CI gates the image | a red push observed not publishing, then a green one publishing | **Not run** — needs a push to GitHub. What *was* proved: the three gate commands pass against a `.env` generated exactly as the workflow generates it, 277 exit 0 |
| **T128** dump on the server | run both ways, artefact names diffed against a pre-change run, then `restore-check.sh` over the output | Pass for the script — host-checkout and container-name runs both exit 0, names identical, rehearsal passed on 4 albums / 24 photos / 84 files |
| **T128** snapshots | the task exists on the appliance and has taken a snapshot | **Not run** — TrueNAS interface, owner's |
| **T129** external check | the check goes red when `web` is stopped | **Not run** — TrueNAS interface, owner's |

**No existing test was edited**, and no test's expectations changed — the
prediction the map made in Phase 2. The `app/` diff is three files: `photos.py`
(the `try` boundary plus two rollbacks, no logic moved, `recover_stuck_photos`
untouched), `config.py` (one setting), `main.py` (the handler). The development
`docker-compose.yml` is not in the diff, as the DoD required.

## Security

**No secret reaches the log file.** A real `app.log` was produced by running the
API suite with `LOG_DIR` set — 178 lines, including the deliberate 500 and two
photo failures — and grepped for the value of every credential in `.env`.
`SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL` and `ADMIN_USERNAME`: absent.
Nothing matching `password=`, `passwd`, `secret_key=` or a `postgresql+psycopg://`
URL appears anywhere in the file.

`POSTGRES_PASSWORD` reported a match, and it is a false positive worth recording
rather than hiding: the *development* password is literally the word
`portfolio`, which matches the logger tag `[portfolio]` on every line. The three
matches were all log prefixes. On the server the value is a generated random
string, so the same grep there is meaningful in a way it cannot be here.

The CI `.env` generation was checked for the trap the DoD named: it does not copy
`.env.example`, and `ADMIN_PASSWORD=change-me` is still refused by
`app/config.py`. No workflow secret is echoed; the generated values are created
and destroyed inside the job.

## Notes — recorded, not fixed

1. **`RotatingFileHandler` is not multi-process safe.** Two uvicorn workers
   rotating the same `app.log` can interleave badly. Both deployment files run a
   single uvicorn process with no `--workers`, so this is a constraint on a
   future change, not a defect today. Worth knowing before anyone adds workers.
2. **`logging.basicConfig` is a no-op when something has already put a handler on
   the root logger.** That is pre-existing and unchanged by T126 — the file
   handler is added with `addHandler` and is unaffected — but it is why the unit
   test has to set the level itself under pytest.
3. **The `e2e` job in the workflow has never executed.** It is tag-triggered and
   no `v*` tag has been pushed since it was written. It does not gate `publish`,
   so a broken one costs a red job on a release and nothing else — but it should
   be read as untested code until a tag proves otherwise.

## Gates at the time of this verdict

| Gate | Command | Result |
|---|---|---|
| Unit + API | `docker compose run --rm tests` | **277 passed**, exit 0 (baseline 271) |
| End-to-end | `uv run pytest e2e` | **81 passed**, exit 0 — **twice consecutively** |
| Lint | `docker compose run --rm tests ruff check .` | clean, exit 0 |
| Format | `docker compose run --rm tests ruff format --check .` | clean, 53 files, exit 0 |

The baseline's intermittent 500 in the dedup upload path did not recur in either
run. The one unexplained `admin_storage_state` login failure recorded in the I2
close did not recur either.

---

# Run 4 — Phase 6 against I2 (M11–M13), 2026-08-15

Scope is the I2 delta only: `dfc8f92..HEAD` on `iteration/I2-pagination-media-phaseb`.
The contract it was judged against is the impact map in
`docs/iterations/I2-pagination-media-phaseb.md` — in an iteration the question is
"did anything move that was not supposed to", not "is this product good".

Two independent reviewers, neither of which wrote the code. One took
completeness and correctness against the ticked task list; the other carried the
`secure-review` and `web-design-guidelines` checklists and drove a browser
against the running stack. `semgrep` is still not on PATH on this machine, so
the security pass was the manual checklist.

## Verdict

**PASS.** No Critical. One High and five Mediums, **all fixed in this session**,
each with a check that was watched failing first. Eight notes are carried with
reasons rather than fixed, listed below.

The High was found by both reviewers independently, which is the strongest
signal either of them produced.

## High — fixed

**«Показать ещё» became a permanently dead control above 200 hits in one
group.** The button asked for `limit = shown + 12`; `/search/group` clamps at
`MAX_GROUP_LIMIT = 200`. `has_more` is `shown < total`, which stays true above
the cap — so at 210 matching articles the heading froze at «200 из 210», the
button was re-rendered for ever, and each press swapped in the same section byte
for byte. Worse from the keyboard: `data-autofocus` is emitted only on the
exhausted branch, so every press was silent, with the caret parked on a control
that had done nothing.

Fixed in three parts: the button renders only while `group.shown < ceiling`; at
the ceiling the group says so («Показаны первые 200 — уточните запрос»); and the
step and the ceiling now reach the template from the route (`_group_limits()`)
instead of a bare `12` sitting beside a `DEFAULT_LIMIT` it had to match by hand.
`tests/api/test_search_seo.py::test_a_group_at_the_ceiling_stops_offering_more`
moves the ceiling rather than seeding two hundred rows.

## Medium — fixed

1. **A continuation announced nothing.** When more remains the swap replaces the
   list and the count and leaves focus on the button, and neither the `<h2>` nor
   the page's «Найдено: N» is a live region for that change: twelve more results
   arrived and a screen-reader user heard silence. `pages/search.html` now
   carries an empty, permanent `role="status"` region and the continuation fills
   it out of band (`hx-swap-oob="innerHTML"`, so the region itself survives — a
   live region created in the same breath as its content may never be announced).
2. **The error toast could be read over the lightbox and not answered.** F-007
   raised the host above `--z-overlay` and made errors wait for a dismissal, but
   `lightbox.js` trapped Tab over its own three controls and called
   `preventDefault()`. The «×» was on screen and unreachable until the picture
   was closed. `focusable()` now includes `#toasts-alert .toast__close`, queried
   per call because a toast can arrive while the lightbox is already open.
3. **«Показать правки» had no visible pressed state at all** — no
   `[aria-pressed="true"]` rule existed anywhere. On the top of a long article,
   where nothing editable is in view, the press changed an attribute in the
   accessibility tree and not one pixel. One rule in `admin.css`, keyed off the
   attribute so the seen state and the announced one cannot drift, plus a
   `forced-colors` variant.
4. **The Russian copy still refused HEIC.** `photo.drop_note` on the album drop
   zone and `blog.cover_hint` under the cover picker still read «JPEG, PNG или
   WebP» after M13 accepted the format — the owner would have converted his
   iPhone photographs by hand because the page told him to, which is the exact
   cost R-10 exists to remove. Both fixed, and a parametrized test now holds all
   five strings that list formats.
5. **T111's DoD was not implemented.** `data-autofocus` was still unconditional
   on the title field of both forms; the caret only landed correctly because
   `ui.js` returns early when it finds `aria-invalid`. `ProjectInvalid.field` is
   optional by design, so a rejection belonging to the whole form would have sent
   the caret to «Название» with the message about something else. Both templates
   now emit the attribute through `autofocus_unless_rejected()`.

## Low — fixed

- `·` was a user-visible character hardcoded in `search_group.html`, which
  `CONVENTIONS.md` §Language forbids. It lives in `search.group_heading` now.
- The comment in `admin_bar.html` claimed `aria-pressed` was "set here from the
  same storage the pre-paint script reads". It is hardcoded `false` and corrected
  by a deferred `edits.js`; the comment now says so, and says what does not lag
  (the class, applied pre-paint, so there is no visual flash).
- `editor.js` dropped any file whose `type` was empty **in silence** — no row, no
  message. That is exactly the shape a HEIC off a phone arrives in, newly
  reachable because of R-10. Empty types are passed to the server, whose magic
  sniff is the authority; anything that *declares* a non-image type is still
  refused in the browser.
- `tests/unit/test_pagination.py::test_the_page_size_lives_in_one_place` compared
  `page_for` against a second call to itself, so it held for every possible value
  of `PAGE_SIZE`. Rewritten against the constant's two boundaries.
- Four stale coordinates in the contract documents (T115, T119/ADR-022, T111,
  T122) and two DoDs describing something other than what was built (T120's
  `offset`-swapping-the-`<ul>`, T116's "a visitor's HTML is unchanged").

## Carried, with reasons

- **T112's test cannot fail without T112's change.** `backdrop-filter` already
  made the capsule a containing block, so the menu was aligned all along; the
  build measured this and wrote it down. `position: relative` is kept as
  insurance against the effect being withdrawn, and the test measures the result
  rather than the mechanism, so it holds whichever is doing the work. This is the
  one in-scope item with no failing-first evidence, and it is deliberate.
- **T114's manual pass on a real Windows contrast theme is still owed**, by the
  owner, per `docs/qa/forced-colors.md`. The automated Chromium-emulation pass is
  done, recorded, and does fail without the CSS.
- **The counts wrap a full entity `SELECT` in a subquery** (`blog.py`,
  `search.py`) where `photos.py` counts the cheap way. One predicate serving both
  the count and the list is the property being bought; two predicates are free to
  disagree, and that is the drift the search count exists to prevent. Worth
  revisiting at a corpus where it measures.
- **`/search/group` has no rate limit** — nor does any route on this site except
  login. It is the most expensive anonymous route now (a `COUNT(*)` plus a rank
  of up to 200 rows), which is worth knowing before the corpus grows.
- **`_HEIF_BRANDS` accepts the generic MIAF brands `mif1`/`msf1`**, so an AVIF
  still or an image sequence can be stored under a `.heic` suffix. The decode
  still has to succeed and originals are never served over HTTP, so the
  consequence is a mislabelled original, not a bypass.
- **`.toast__close` is exactly 24×24 CSS px** — the WCAG 2.5.8 floor with nothing
  in hand, which ADR-010 already accepts as the site's bar.
- **The expanded state of a search group is not in the URL**, so reloading after
  «Показать ещё» collapses it back to twelve. The paginated indexes do put their
  state in the URL; search deliberately does not, because its address is a query.
- **No QA artefact covers a paginated index or a search with hits.** The sweeps
  in `docs/qa/` predate both. The two samples that matter were measured by hand
  this run — `.pagination__position` resolves to the same token pair as the
  `<time>` sample that passes at 4.65 (light) / 5.31 (dark), and the toast «×»
  measures ≈7.4:1 — but extending the sweeps belongs to the next iteration.

## What the reviewers checked and found clean

- **The forbidden diff of T119 holds.** `_board()`, `album_reorder`,
  `album_move` and `_reorder_from_ids` are outside every hunk; pagination went
  into `photo/index.html`, outside the swap target.
- **T115's server-side alt fallback is unchanged**, the marks and the count are
  inside `{% if is_admin %}`, and no alt text is generated.
- **T108's deletions are deletions** — `.badge`, `.photo-badge`, `.post-flag`,
  `.project-form__error`, `.album-form__error`, `.login__error` and
  `.site-links__error` are gone from the sheets, with every selector moved in the
  same commit. `.login__error` moving into `components.css` also fixed a latent
  unstyled error box on `/login`, which is loaded without `admin.css`.
- **T107 leaves one clearance rule, not two.**
- **Pagination arithmetic**: `?page=` of `0`, `-3`, `abc`, `1e5`, `page[]=2`,
  `%2F%2Fevil` and 4000- and 5000-digit values all answer 200; `offset` agrees
  with `limit`; 24 rows at 12 is two pages; page 1 is the bare path, so the
  canonical is self-referential.
- **The continuation hides exactly what the page hides.** Both go through the one
  `_statement()`, and the total is a `count()` over that same filtered statement,
  so the count cannot leak what the list does not show. Verified live as an
  anonymous client: drafts and unpublished albums are absent at `limit=200` for
  every kind, and a group an admin sees as 2 reports «1 из 1».
- **`kind` is allow-listed before the database is touched**; `limit` clamps to
  `[12, 200]`; an over-long `q` is truncated rather than 422'd.
- **HEIC intake**: `validate_upload` returns the *sniffed* type, never the
  declared one, so `image/heif` cannot reach an extension map that lacks it; the
  120 Mp ceiling is read from the header before any decode; `pillow_heif` does
  override `verify()`, so a truncated file is refused at intake rather than in
  the background pool; `.tiff`, an `ftypmp42` video and a zip named `.heic` are
  all still refused. Every upload route is admin-only.
- **CSP is unchanged and still nonce-based**; the delta adds one external script
  tag and zero inline handlers or `style=` attributes.
- **No admin-only markup in a visitor's HTML**; hostile `q` is escaped in the
  title, `og:title`, the input value and the empty state; `Vary: Cookie` is on
  `/search`, `/search/group` and `/blog`, so no fragment can be cross-cached
  between the owner and a visitor.
- **Scope**: six files sit outside every impact-map row — `search.css`,
  `uploader.js`, `blog.json`, `e2e/test_nav_dropdown.py`, `e2e/test_forced_colors.py`
  and the re-measured `docs/qa/perf-*.json`. Each is a one-line consequence of an
  in-scope row; none is a scope breach.

## Gates at the time of this verdict

| Gate | Command | Result |
|---|---|---|
| Unit + API | `docker compose run --rm tests` | **271 passed**, exit 0 (I2 baseline 233) |
| End-to-end | `uv run pytest e2e` | **81 passed**, exit 0 (I2 baseline 60) |
| Lint + format | `uv run ruff check .` / `ruff format --check .` | clean, 127 files |

One run of the three taken during this phase had a single fixture error — a login that answered
`303` and redirected to an anonymous page — which did not recur and is recorded under «Resume here»
in `docs/STATUS.md` rather than explained away here. Two runs in that batch also had the app
restarting underneath them: a `git stash` cycle over `app/**`, used to watch a test go red, trips
uvicorn's `WatchFiles` reloader mid-suite.

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
