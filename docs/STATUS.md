# Status

phase: review
approved: true
approved_at: 2026-08-04

## Resume here

**Branch `session/2026-08-06-m3-fixes-and-e2e`, tree clean, nothing running.** No remote; merging
into `main` is the owner's call. The dev stack is up (`db`, `web`) — `make down` stops it.

**M9 is 11 tasks of 12 done. The session did not end mid-task: every gate is green and every
change is committed.** T090–T098 and T100/T101 are implemented, tested and ticked. **T099 is the
only thing left in the milestone**, and it is the same half it was: `README.md` and
`scripts/screenshots.py` exist and work, the media section and the screenshots do not.

M0–M8 are complete and Phase 6 is closed (`docs/REVIEW.md`, PASS at `a0c2835`). The review's two
Medium findings became T100/T101 and are now fixed.

### Next three actions, in order

1. **Finish T099 — the last open task in M9.** Two halves, both now unblocked. (a) `make up`, then
   `uv run python scripts/screenshots.py` — the eight shots under `docs/qa/screenshots/` predate
   the favicon (T095) and still show a cover opening an article (T098), so they are wrong on both
   counts. (b) Put the «Обслуживание медиа» section back into `README.md`: it was cut because it
   documented `make media-orphans`, `make media-prune` and the deduplication guarantee, none of
   which existed then and all of which do now. `docs/HANDOFF.md` §5 «Media maintenance» is the
   English source to translate — the README is Russian, unlike everything under `docs/`.
2. **Re-run Phase 6 against M9.** The review that passed was against `a0c2835`; M9 has since
   rewritten the media lifecycle, the upload limit, the CSRF failure path and the security headers
   on a 500. `docs/REVIEW.md` is the format. Two things in this milestone are worth a reviewer's
   attention specifically: `images.release` is the only thing standing between "the owner deleted
   an article" and "the owner broke another article's cover", and `ui.js` now retries a 403 once
   after fetching a fresh token — a retry loop would be a denial of service against our own site,
   so the one-shot guard (`data-csrf-retried`) is the thing to read twice.
3. **`data-autofocus` is belt-and-braces, not a replacement — finish it.** T101 asked for the
   `autofocus` attribute to go, because the HTML spec lets a browser drop it on markup inserted
   after parse. The `[data-autofocus]` handler in `ui.js` is written and both attributes are on the
   five swapped fragments, so behaviour is at least what it was — but with `autofocus` removed,
   `test_an_article_can_be_written_and_published_without_a_mouse` goes red: the handler does not
   fire for the «Новая статья» form. Reproduce it by deleting `autofocus` from
   `blog/_new_form.html` and running `uv run pytest e2e/test_a11y.py`. Suspect the settle event's
   shape before suspecting the selector — `htmx:afterSettle` was tried on both `event.detail.target`
   and `event.target` and neither focused the field, which points at the listener not running at
   all rather than at the wrong element.

**Waiting on the owner:** nothing blocking. **T074, the production deploy, is deliberately not
happening inside a working session** — the owner will run it himself once the site is finished.
That is still the only unticked item on the launch checklist.

**Decided by the owner on 2026-08-08:** «блог» and «статьи» mean the same thing, so one rule for
pictures in text — 1920 px — and it covers project descriptions too; he exports files up to
**50 MB**, so the cap is now 50; `README.md` is **Russian**, unlike everything under `docs/`.

## Checklist
- [x] Phase 0 intake
- [x] Phase 1 elicit (DoR met)
- [x] Phase 2 SPEC.md
- [x] Phase 3 PLAN.md + TASKS.md
- [x] GATE user approved
- [x] Phase 4 implementation (M0–M8 done)
- [x] Phase 5 tests green (unit/API 222/222; e2e 40/40; lint and format clean)
- [x] Phase 6 review clean (`docs/REVIEW.md`, PASS at `a0c2835`; Critical + 6 High fixed, Mediums scheduled as T100/T101)
- [x] Phase 7 handoff (`docs/HANDOFF.md`; the production deploy stays open by the owner's choice)
- [x] **GATE — M9 approved 2026-08-08 («утверждаю»)**
- [x] M9 implementation — T090–T098, T100, T101 done and ticked
- [ ] **T099** — the last open task in M9: the README media section and regenerated screenshots
- [ ] Phase 6 re-run against M9 (the passing review was against `a0c2835`)

## Test report

All five gates run 2026-08-08 at the end of the session, on the tree as committed.

| Gate | Command | Result |
|---|---|---|
| Unit + API | `docker compose run --rm tests` | **222 passed**, exit 0 |
| End-to-end | `uv run pytest e2e` | **40 passed**, exit 0 |
| Six launch flows | `uv run pytest e2e -m launch_flow` | **6 passed**, exit 0 |
| Lint | `uv run ruff check .` | clean, exit 0 |
| Format | `uv run ruff format --check .` | clean, exit 0 |

No failing tests. The suite grew 204 → 222 unit/API and 37 → 40 e2e this session: deduplication of
one frame used twice, deletion of an article that shares a cover with another (asserted in **both**
directions — the survivor keeps its picture, and the last article to go takes the file with it),
release of a picture cut out of an article's text, the `body_html` half of the reference scan, the
whole copyright line, the second editable block on the home page, the cover leaving the article
body while `og:image` and the index card keep it, a query over the 200-character cap, the default
`og:image`, the `/csrf` endpoint, login-attempt pruning and the security headers on a 500.

**Three of the new tests were checked in both directions**, by breaking the fix and watching them go
red: the `body_html` scan, the reference-aware deletion, and the security headers on a 500. A
regression test that cannot fail is the mistake this project has already made twice.

`-q` is set twice, so a passing run prints dots and no summary line. **Read the exit code.** Never
pipe a test run through `tail` or `grep`: you get the pipe's status and a red suite reads as green.

**Nothing is known bad.** The one thing not finished is written into "Resume here" as action 3, and
it is a hardening step whose fallback (`autofocus`, still on all five fragments) is what shipped
before.

## Notes

Entries before M9 are archived in [notes/2026-08.md](notes/2026-08.md).

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
