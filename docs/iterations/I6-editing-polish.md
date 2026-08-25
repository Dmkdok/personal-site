# Iteration I6 — Editing polish

- **Source:** owner request, three findings made during I5's own exit-criterion-8 pass (write an
  article with a sized picture and a video by the cheat sheet alone, publish it, read it in both
  modes) — the pass that closed M17.
- **Opened:** 2026-08-25
- **Milestone:** `M18` in `docs/TASKS.md`
- **Baseline:** unit/API 353 passed, e2e 110 passed, lint clean, format clean over 122 files, at
  2026-08-25, branch `iteration/I6-editing-polish`, cut from `main` at `d90ec48`

## In scope

| Item | Why now |
|------|---------|
| Album edit mode: the photograph itself reads blurred under the owner's tools | Found on the exit-criterion-8 pass; the owner cannot tell which photo a tile is without opening it |
| `/me/media`: «Файлы на диске» crowds the empty state's frame above it | Found on the same pass; a layout bug in the room I5 just built |
| The editor gives a video no identifying information until it is played | Found on the same pass; the owner asked for a poster or a name and confirmed it is worth doing properly, not just documented |
| ADR-038's deferred fix — a video's own control label leaks into the auto-generated excerpt and meta description | Already found by I5's review run 7 and explicitly deferred to "the next intake as its own item" (ADR-038); this is that intake and the topic is the same one |

## Out of scope this round

| Item | Reason | Recorded as |
|------|--------|-------------|
| VK Video gets an automatic title too | No public, unauthenticated oEmbed exists for it — only `video.getOembed`, which needs a registered VK application and an `access_token` to hold and rotate. Not proportionate to one caption field on one of three services. | ADR-040 |
| Live title lookup on every render (preview keystrokes, published page) | Would make the site's own latency and uptime depend on YouTube's and Rutube's, and reintroduces the reader-facing external request F63 was written to rule out | ADR-040 |
| Scraping a VK page's Open Graph tags as a substitute for an API | No documented contract, and the page refused this session's own fetch attempt | ADR-040 |
| Archiving M17's full task text to `docs/tasks-archive.md` the way M0–M14 are archived | Housekeeping unrelated to this delta; M15 and M16 are still open in the same file, so a partial archive would be inconsistent | not recorded — left for whenever M15/M16 close too |

## Impact map

| Item | Touches | SPEC: changes / preserves | Existing coverage | Class | Regression proof |
|------|---------|---------------------------|--------------------|-------|-------------------|
| T140 blurred photo | `app/static/css/photo.css` → `.photo-item__admin` (460–474) | changes none; preserves F55/ADR-032 (owner-only visibility marker) | `e2e/test_show_edits.py`, `test_view_parity.py`, `test_a11y.py` contrast sweep — none assert the scrim's own background or blur | Local | Contrast sweep passes at its current sample count (children carry their own opaque background, never depended on the scrim); manual check — photograph under the tools is sharp in «Правка», both themes |
| T141 disk section overlap | `app/static/css/me.css` → `.cabinet__group + .cabinet__group` (line 53) | changes none; preserves F64 | none — `e2e/test_me.py` covers the non-empty cabinet only | Local | New e2e case: `/me/media` with `groups` empty, assert `.cabinet__disk`'s top edge clears `.empty`'s bottom edge by the `--space-l` gap, watched failing first |
| T142 editor teaches the captioned form | `app/static/js/editor.js` → `videoAction()`; `app/i18n/ru/blog.json` | changes none; preserves F63 (the caption/poster form already specified, now discoverable) | none for the toolbar's inserted text | Local | New e2e case: press the video toolbar button, assert the textarea holds a captioned link, not a bare one, watched failing first |
| T143 YouTube/Rutube auto-title | new route in `app/routers/blog.py`; oEmbed fetch (stdlib `urllib`); `app/static/js/editor.js` wiring | adds F66; preserves F63 (no request reaches the video host on a reader's behalf — this one is server-to-provider, at edit time, admin-gated) and ADR-001 (no over-engineering — no new runtime dependency) | none — new capability | Contract | Unit test with the outbound call patched: request target is always a `_VIDEO_SERVICES`-shaped YouTube/Rutube URL, never arbitrary; anonymous access answers the same as every other `/blog/admin/*` route; a timeout/failure case leaves the caption untouched rather than raising. `secure-review` in Phase 6 regardless of size (new outbound dependency, admin input builds a fetch target) |
| T144 ADR-038 fix | `app/services/markdown.py` → `excerpt_from` (503) | changes none new; closes the gap ADR-038 named against F8's card excerpt and the meta description | `tests/unit/test_markdown.py:152,160,167` (unrelated cases, unaffected) | Local | New unit test: a body that is only a bare video link excerpts to `""`, not the button's label; a captioned video followed by prose still contributes the caption's and the prose's words |

**Ordering.** T140, T141 and T144 touch disjoint files and share nothing — any order, safely
parallel. T142 before T143: T143 fills the caption slot T142 creates. Nothing here is a shared
primitive; nothing lands serially for that reason. T143 alone carries the Contract class and the
mandatory security-review flag.

## Expectations that change

**One, found during implementation and not by this intake.** T142's own DoD requires `videoAction()`
to stop inserting a bare address — which is exactly what
`e2e/test_editor_sheet.py::test_the_video_button_writes_a_paragraph_of_its_own` asserted
(`text.endswith("\n\n" + ru("blog.md.ph_url"))`, plus the selection). The impact map's own T142 row
said the toolbar's inserted text had no existing coverage; it had one, missed at Phase 2. Run 8's
review judged the fix correct rather than a quiet edit: the assertion could not survive the approved
DoD, the replacement (`test_the_video_button_writes_a_captioned_paragraph_of_its_own`) is the same
strength — exact inserted shape *plus* the selection — and the rename and reason are in both the
test's own docstring and its commit (`109c38a`). No ADR needed: nothing was decided that SPEC or an
ADR already governed: a plan was under-described, and this line is the correction.

Every other existing test named in the impact map passes unchanged; each remaining new behaviour
ships with its own new test, watched failing first.

## Exit criteria

- [x] A photograph in «Правка» reads sharp under the owner's tools, in both themes
- [x] `/me/media` with nothing to flag shows «Файлы на диске» clear of the empty state's frame
- [x] The video toolbar button and the cheat sheet produce a captioned link, not a bare one
- [x] A YouTube or Rutube link inserted through the toolbar fills its own caption from that host's
      title, editable before save; a VK link is unaffected
- [x] An article opening with an uncaptioned video and no written excerpt no longer carries the
      player's own label in its card or its `<meta name="description">`
- [x] Baseline suites green at their Phase 0 counts or better (unit/API ≥ 353, e2e ≥ 110, lint and
      format clean) — unit/API 367, e2e 111, both clean, at implementation's close
