# Iteration I7 — A video embeds directly; the click facade is retired

- **Source:** owner request, made live in chat while looking at a published article
  (`docs/STATUS.md` session 2026-08-25, after I6's close). Approval word "утверждаю" given in
  chat for the plan below, before this document existed.
- **Opened:** 2026-08-25
- **Milestone:** `M19` in `docs/TASKS.md`
- **Baseline:** unit/API **370** exit 0, e2e **113** exit 0, `ruff check` clean, `ruff format --check`
  **124 files** exit 0 — recorded 2026-08-25 on `iteration/I7-direct-video-embed`, cut from `main` at
  `ce8cc84`. Tree was clean before the branch. Same counts as I6's closing tree; nothing regressed
  between the two sessions.

## In scope

| Item | Why now |
|------|---------|
| A video paragraph renders a real `<iframe>` immediately, not a `<button>` facade a reader must press first | The owner found the facade cost *two* presses to actually watch — their own button, then YouTube's own paused state inside the iframe it built — and asked for the ordinary one-click embed every other site uses, having weighed and accepted ADR-035's original privacy reasoning |

## Out of scope this round

| Item | Reason | Recorded as |
|------|--------|-------------|
| Self-hosted video / a real lite-embed proxy that keeps the click-to-load privacy property another way | Not asked for; the owner explicitly accepted the third-party-on-load cost rather than asking to avoid it a different way | not recorded — no live proposal exists to defer |
| Using the video's own oEmbed thumbnail (F66's fetch) as a fallback poster | A live iframe already shows the host's real thumbnail before any click; a second, separately-fetched image would be pure duplication | ADR-041, "Alternatives rejected" |

## Impact map

| Item | Touches | SPEC: changes / preserves | Existing coverage | Class | Regression proof |
|------|---------|---------------------------|--------------------|-------|-------------------|
| Render an `<iframe>` directly instead of a `<button>` facade | `app/services/markdown.py`: `_ProseRenderer.link_open`, `link_close` (video branch), `ALLOWED_TAGS`, `ALLOWED_ATTRIBUTES` (`button` → `iframe`) | **changes F63** (its "no request until the press" / "no `iframe`" clauses invert); preserves the renderer-closed-URL invariant (the `src` can only ever be a `_VIDEO_SERVICES`-matched value) and F66 (oEmbed caption fetch, untouched) | `tests/unit/test_markdown.py` video block (~15 tests); `e2e/test_video.py` (3 tests) | **Cross-cutting policy** (CSP/sanitiser allow-list) — `secure-review` in Phase 6 regardless of size | Unit test rewritten to assert an `<iframe src="…">` is present on render and a hand-typed `<iframe>`/`<button>` in the Markdown source still cannot survive as an element (raw HTML stays off at the parser); e2e rewritten to assert the iframe and its network request are present on page load, before any interaction |
| Retire the poster-picture affordance | `app/services/markdown.py`: `_figure_paragraphs` (`poster.meta["in_figure"]` → `poster.meta["video_poster"]`), `_ProseRenderer.image` (skip render when `video_poster`); `figure_caption` fallback widened from `title` only to `title` or `alt` | changes nothing in `SPEC.md` directly (F63's picture-as-poster clause was acceptance detail, not a numbered sub-requirement); preserves the caption ending up in `<figcaption>` either way | `tests/unit/test_markdown.py::test_a_picture_from_our_own_media_becomes_the_poster`, `test_a_posters_markdown_title_becomes_the_caption`; `e2e/test_video.py::test_a_picture_from_our_own_media_is_the_poster` | Local | Rewritten tests assert the picture is never in the output HTML while its `title` or, failing that, `alt` still reaches the `<figcaption>` |
| Remove the click-to-build script and its styling | `app/static/js/video.js` (deleted); `app/templates/blog/post.html`, `dev/detail.html`, `blog/editor.html` (drop the `<script>` tag); `app/static/css/prose.css` (`.prose-video__play/__glyph/__label` rules and their `forced-colors` block deleted) | preserves nothing new; F63 already covers the player itself | none directly — covered by the e2e rewrite above | Local | e2e rewrite confirms the page plays without any script beyond native iframe behaviour; `ruff format`/lint stay clean |
| Drop the now-dead excerpt special-case | `app/services/markdown.py`: `excerpt_from`, `_VIDEO_PLAY_BUTTON` (deleted) | preserves ADR-038's outcome (no control label in an excerpt) by construction — there is no more control label to strip | `tests/unit/test_markdown.py::test_excerpt_of_a_bare_video_is_empty_not_the_buttons_label`, `test_excerpt_of_a_captioned_video_keeps_the_caption_and_the_prose` | Local | Both tests simplified to prove the same outcome now falls out of ordinary tag-stripping, no special-casing needed |
| Cheat sheet and forced-colors coverage catch up | `app/i18n/ru/blog.json` (`sheet_video_poster_code`/`_text` removed), `app/i18n/ru/common.json` (`video_play` removed, unused) | preserves F38's cheat-sheet acceptance in the form I5 left it, minus the retired poster row | `e2e/test_a11y.py` editor sweep (open/closed) — unaffected by a removed row | Local | Editor sweep still passes with the sheet open and closed |
| `e2e/test_forced_colors.py::test_the_video_facade_keeps_its_plates` | deleted, not rewritten | preserves nothing — the glyph disc and label plate it checks no longer exist; a plain `<iframe>` needs no bespoke forced-colors treatment | itself | Local | test suite still green without it |

**Ordering:** one task. Everything above is one symbol's worth of change (`app/services/markdown.py`'s
video-rendering path) with the templates, CSS, i18n and tests that follow from it — splitting it
into two tasks would only recreate the merge conflict the impact map exists to avoid.

## Expectations that change

Every one of these is a deliberate consequence of the owner's approved plan, not a defect found in
review:

1. **F63 itself inverts its two sharpest clauses** — "no request reaches the video host until the
   reader presses play" and "the page's HTML contains no `iframe`" both become their opposite. This
   is the whole point of the round and is edited into `SPEC.md` directly (never renumbered).
2. **`iframe` re-enters `ALLOWED_TAGS`/`ALLOWED_ATTRIBUTES`.** The renderer-closed-URL invariant
   ADR-035 built for `button`'s `data-video` carries over unchanged: nh3 filters attribute *names*,
   never values, so `iframe.src` can only ever be a value this module already matched against
   `_VIDEO_SERVICES`'s anchored per-host patterns — never an arbitrary string reflected off author
   input. `secure-review` re-verifies this specifically in Phase 6.
3. **The poster-picture affordance (`[![заставка](url)](videourl)`) stops rendering a picture.** An
   iframe already shows the video host's own live thumbnail before any click, so a second,
   separately-uploaded, staler image drawn behind a button that no longer exists has nothing left to
   do. The picture's `title`, or its `alt` if there is no `title`, still becomes the `<figcaption>` —
   widened from `title`-only so the author's words are not silently dropped, since the image itself
   no longer carries them to the page.
4. **ADR-038's excerpt fix becomes dead code, not a still-needed guard.** The button label it stripped
   («Смотреть видео») no longer exists to leak. The special-casing is deleted; the two tests it
   justified are simplified to prove the same outcome falls out of ordinary tag-stripping.
5. **The editor's live preview will contact the video host on every htmx-triggered refresh** while
   the owner is actively editing a video paragraph, not only once on a manual click as today. This is
   admin-only traffic (the owner's own session, never a reader's) and moves no CSP directive beyond
   what ADR-035 already opened — disclosed here, not a security regression.
6. **Focus-, target-size- and contrast-sweep counts shift** (`docs/qa/focus-sweep.json` and the
   admin/anonymous target and contrast sweeps mentioned in `docs/STATUS.md`): one button and the two
   plates behind it (glyph, label) leave the swept pages; a cross-origin `<iframe>`'s own internals
   are outside every sweep's reach either way. New counts are recorded fresh at Phase 5, not
   predicted here.

## Exit criteria

- [ ] A published article with a bare video link shows a live, playing-capable `<iframe>` immediately
      on load — no button, no separate click to reveal it — and a network request to the video host
      is observed at load, not only after an interaction
- [ ] A hand-typed `<iframe>` or `<button>` in an article's Markdown source still cannot survive as an
      HTML element — raw HTML stays off at the parser, proven the same way the existing button test
      proves it
- [ ] A video link wrapping one of this site's own photos no longer renders that photo, and the
      photo's `title` (or `alt`, if it has none) still reaches the `<figcaption>`
- [ ] `app/static/js/video.js` is gone and no template references it
- [ ] The editor's cheat sheet no longer describes the retired poster-before-click behaviour
- [ ] Baseline suites green at their Phase 0 counts or better: unit/API ≥ 370, e2e ≥ 113 (with the
      video- and forced-colors-facade tests rewritten or removed per "Expectations that change," not
      simply deleted from the count), lint clean, format clean
- [ ] `secure-review` has looked at the `iframe`-allow-list change specifically, per this document's
      point 2
