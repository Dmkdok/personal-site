# Status

phase: iteration I9 in progress, T148 done and pushed, T149 attempted and reverted, T150 not started (M21; M20 done; M16 still open, owner's appliance work only)
approved: true
approved_at: 2026-08-04
i4_delta_approved_at: 2026-08-16
i5_delta_approved_at: 2026-08-17
i6_delta_approved_at: 2026-08-25
i7_delta_approved_at: 2026-08-25
i8_delta_approved_at: 2026-08-29
i9_delta_approved_at: 2026-09-01

## Resume here

**Branch `iteration/I9-article-editor-ux`, tree clean, 1 commit ahead of `main` (0 behind) — pushed
to `origin` this session.** Owner is switching machines; this section exists so the next session
can resume from this file alone.

**Do not trust this session's own numbers at face value — re-verify.** The owner asked explicitly:
before building on top of T148, re-run its gates independently and read the actual diff in
`470215b`, don't just take this file's word that it's clean. Same for anything below marked
"reported by subagent" rather than "independently re-run in this session."

**State: T148 done and committed (`470215b`, independently re-verified this session: unit/API 399,
`ruff check`/`format --check` clean). T149 was attempted, hit a11y test failures under
investigation, was stopped mid-diagnosis and its uncommitted diff was deliberately reverted
(`git restore`) rather than committed half-working — nothing of T149 exists in the tree or history.
T150 not started.**

**Next three actions, in order:**
1. Re-run `docker compose run --rm tests`, `ruff check .`, `ruff format --check .` on this tree
   (should read 399 / clean / clean) — confirm before trusting, per the owner's instruction above.
2. Run `uv run pytest e2e -q` fresh. **The last full e2e run this session was red beyond the three
   known-baseline failures** — see the anomaly below — figure out whether that reproduces on a
   clean start (fresh `docker compose down -v && up`, not just `restart web`) before assuming it's
   still there or was this session's own accumulated state.
3. Re-implement T149 from scratch (`docs/TASKS.md` M21, DoD unchanged) — per-file `XMLHttpRequest`
   upload progress in `app/static/js/editor.js`, modelled on `uploader.js`; the photo control moved
   out of `.md-toolbar__button`'s glyph row in `app/templates/blog/editor.html`. The previous
   attempt's diff is gone (reverted), but its direction (rewrite `ACTIONS.image`/`upload`/
   `uploadOne`, buffer completed uploads to preserve drop-order insertion despite concurrent XHRs)
   is still the right starting shape — just diagnose the a11y regression it hit before repeating it.
   `editor.js` also still carries a stale comment near `maybeFillVideoCaption` claiming the shared
   editor has no toolbar — false since T148; fix it in the same diff, don't spend a separate task on it.

**Anomaly from this session's last full e2e run, unresolved, needs the owner's or next session's
attention before trusting e2e results at all:** on the clean, reverted-to-T148 tree, a fresh
`uv run pytest e2e -q` came back **4 failed + 3 errors**, not the expected 3 known failures. The 3
known ones (upload-limit string, two `/dev` drag tests) are present as before. New, not seen before
this session: **3 setup errors, all in `admin_storage_state`**, all failing the same way — the login
POST returns "Неверный логин или пароль" instead of succeeding, meaning `.env`'s `ADMIN_PASSWORD`
does not match this dev DB's seeded admin password (the fixture reads `ADMIN_USERNAME`/
`ADMIN_PASSWORD` straight from the environment — `e2e/conftest.py:71`). Also new: **one additional
failure**, `test_editor_guard.py::test_publishing_counts_as_saving`, showing an autosave-guard
message in `#editor-meta` instead of the expected "published" status — exact text was unreadable in
this session's terminal (Windows console mojibake on Cyrillic), not diagnosed further. **Working
hypothesis, not confirmed:** three consecutive full e2e runs against the same long-lived local dev
DB in one session (this session's implementer subagent ran it twice, this session once more) —
consistent with the project's already-known pattern of local DB/session state drift under repeated
runs (the two `/dev` drag failures are exactly that). Nothing in T148's diff touches auth, the admin
seed, or the save/autosave path, and unit/API (which exercises the same models) is green — but this
is a hypothesis, not a proof, and the next session should not repeat it as fact until it either
reproduces on a clean DB or is shown to be something else.

**docs/qa/\* screenshots and JSON sweep evidence regenerate as a side effect of running `uv run
pytest e2e` at all** — confirmed twice this session (reverted, ran e2e again, came back dirty again
with fresh LCP timings / JPEG re-encode noise / sweep sample counts). Reverted both times
(`git restore docs/qa/`), not committed — none of it corresponds to a deliberate sweep tied to this
iteration's actual changes. **Any future e2e run will dirty these files again**; that alone is not a
sign of anything wrong, and they should stay reverted until an iteration deliberately takes new
sweep evidence at its review checkpoint. `docker-compose.override.yml` stays untracked by design
(Baseline I9's own record: a host-only port remap, not a code change).

## Baseline I9

Recorded 2026-09-01 on `iteration/I9-article-editor-ux`, cut from `main` at `fdd8c47` (I8's closing
tip, merged/pushed/deployed). Tree was clean before the branch (one untracked, gitignored-by-intent
local file, `docker-compose.override.yml`, self-documented as not tracked — a host-only port remap,
not a code change).

**Three environment gaps found and fixed before any suite would run, none inside this repo's
tracked files:**

1. The local `web` container (docker-compose, 3 weeks old) predated the `pillow-heif` dependency
   and failed to boot (`ModuleNotFoundError: No module named 'pillow_heif'`) — stale image, rebuilt
   with `docker compose up -d --build web`.
2. `uv` was not on this machine's PATH at all (not in the user or machine registry PATH, not in any
   of the usual install directories) despite prior sessions' recorded use of `uv run` — reinstalled
   with the official installer (`irm https://astral.sh/uv/install.ps1 | iex`), owner's choice over
   AskUserQuestion.
3. `C:\Dev\pyproject.toml` — outside this repo, June 2024, unrelated to this project — carried
   invalid TOML (`select = [..., "Q"]`, a literal ellipsis placeholder). `uv`'s workspace discovery
   walks up from the project root and fails hard on any unparseable `pyproject.toml` it meets on the
   way, so every `uv run` in this repo errored before reaching pytest. Fixed the placeholder in
   place (owner's choice over AskUserQuestion) — the file was already unusable by any tool, so this
   could only fix, not regress, whatever that file is for.
4. Playwright's Chromium/headless-shell binaries were not installed under this profile
   (`ms-playwright` cache empty) — installed via `uv run playwright install chromium --with-deps`.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **399 passed**, exit 0 |
| e2e | `uv run pytest e2e -q` | **112 passed, 3 failed**, exit 1 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | **130 files**, exit 0 |

unit/API and lint/format match I8's closing counts exactly — nothing regressed there. **The three
e2e failures are pre-existing, local-environment drift, not a code regression, and not touched by
this iteration's scope:**

- `test_upload_guard.py::test_files_that_cannot_succeed_never_reach_the_network` — asserts the
  50 MB-limit error string; this machine's `.env` has carried `MAX_UPLOAD_MB=25` (vs.
  `.env.example`'s `50`) since before this session. A local config/test-fixture mismatch, not a app
  code defect.
- `test_view_parity.py::test_edit_mode_still_drags_the_project_board` — fails its own precondition
  (`the two cards do not fit the viewport together`): the long-lived local dev DB has accumulated
  enough `/dev` board entries from repeated local e2e runs that the two fixture cards no longer both
  fit one viewport.
- `test_view_parity.py::test_named_owner_surfaces_have_no_box_in_view_mode[chromium-/dev-[data-drag-handle]]`
  — `[data-drag-handle]` absent from `/dev` in view mode; likely downstream of the same accumulated-
  data state as the row above (no draggable card in the fixture's expected position).

None of the three touch `blog`, `shared`, `photos` editor routes or templates — carried forward
unfixed as known-red, not this iteration's concern. Flagged to the owner in the same session.

## Iteration I9 progress

```text
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred) — one AskUserQuestion round (photo-button fix,
      shared-editor image scope, which UX items, budget); all recommended answers accepted
- [x] 2 impact map written — `docs/iterations/I9-article-editor-ux.md`
- [x] 3 docs amended — SPEC F70 edited in place + F72/F73/F75, ADR-044 (+ ADR-042/043 backfilled
      into the index, missing since I8), TASKS M21 (T148, T149, T150)
- [x] GATE approved by the owner — «утверждаю», 2026-09-01
- [ ] 4 implementation — **T148 done**, `470215b`; **T149 attempted, hit a11y failures, reverted
      uncommitted** (see Resume here); T150 not started
- [ ] 5 verification green, baseline suites still green
- [ ] 6 review clean or waived
- [ ] 7 closed (STATUS rewritten, milestone ticked)
- [ ] 8 deploy (optional, only if a real deploy target exists)
```

**T148 landed**, `470215b`. New shared partials `app/templates/partials/md_toolbar.html` and
`md_cheatsheet.html`, included from both `blog/editor.html` and `shared_editor.html`; new
`app/static/css/editor.css` holds the toolbar/pane/textarea/preview rules moved out of `blog.css`
and `shared.css` (`shared_editor.html`'s classes renamed to the shared `.editor__*` names).
`app/i18n/ru/shared.json` untouched by design — the shared editor reads `blog.json`'s `md.*`/
`toolbar_label` keys directly, one source of truth. `editor.js` untouched — it already resolves
targets generically off `data-editor-*`/`.md-toolbar`, so the shared editor's video button now also
gets F66's server-side title autofetch for free (a correct but unplanned side effect of "working
counterpart"). New e2e: `e2e/test_editor_sheet.py::test_the_shared_editor_toolbar_matches_the_blog_editors_but_for_the_photo_button`.

Gates: unit/API **399** exit 0 (matches I9 baseline), `ruff check` clean, `ruff format --check`
**130 files** exit 0, e2e **116** total, **113 passed**, **3 failed** — exactly the three named
pre-existing failures from Baseline I9 (upload-limit string, two `/dev` drag tests); a fourth
failure seen on the first of two full e2e runs
(`test_me.py::test_a_shared_articles_link_survives_only_until_it_is_reissued`) reproduced as a
flake — passed alone, passed again on the second full run, and T148 touches no code on that path.
`test_editor_guard.py`'s 7 F50 tests passed unmodified on both fixtures.

**One stale comment flagged, not fixed here, T149's to pick up:** `editor.js`'s comment near
`maybeFillVideoCaption` — "an editor with no toolbar (the shared-article editor) never puts this
skeleton in front of an owner" — is now false; the shared editor has a toolbar. `editor.js` is in
T149's path list.

## Baseline I8

Recorded 2026-08-28 on `iteration/I8-token-shared-articles`, cut from `main` at `b2318f0`. That tip
is I7's own close (`ce8cc84`..`1a10e72`) plus one chore commit made at this baseline, committing
tooling/doc leftovers (`deploy-product` skill, `RELEASE.template.md`, `CLAUDE.md` conventions
sections) found uncommitted on `iteration/I7-direct-video-embed` — content untouched, just given a
commit. `main` was fast-forwarded to that tip in this session (0 behind, 5 ahead before the merge).
Tree was clean before the branch. Every command below ran in this session, on this tree, none piped.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **371 passed**, exit 0 |
| e2e | `uv run pytest e2e -q` | **112 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | **126 files**, exit 0 |

Same counts as I7's closing tree (unit/API 371, e2e 112) — nothing regressed. Format's file count
moved 124→126 from the two new tooling files committed at this baseline, not from anything this
iteration changes.

## Iteration I8 progress

```text
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred) — agreed in chat plus one AskUserQuestion round
      (URL format, editor scope, rate-limit, iteration budget); formalised in the iteration doc
- [x] 2 impact map written — `docs/iterations/I8-token-shared-articles.md`
- [x] 3 docs amended — SPEC F67–F71 + `shared_article` row + two user flows, ADR-042 + ADR-043,
      TASKS M20 (T146, T147)
- [x] GATE approved by the owner — «утверждаю», 2026-08-29
- [x] 4 implementation — T146, then T147, one commit each
- [x] 5 verification green — unit/API **394** exit 0 (374 at the T146 baseline), e2e **113** exit 0
      (112 at Phase 0, +1 for the new shared-article flow test), lint clean, format clean **130 files**
- [x] 6 review clean or waived — `docs/REVIEW.md` run 10, PASS with findings; one High and two
      Mediums fixed same session (F50 guard generalised onto the shared editor, `share_token`
      redacted from logs, a11y sweep extended to the editor page), one Medium carried (noindex
      without nofollow — matches F69's letter), two Lows fixed. unit/API **399** exit 0 (394 before
      the fix), e2e **115** exit 0 (113 before), lint clean, format clean **130 files**
- [x] 7 closed 2026-08-29 — all seven exit criteria met; see Resume here
- [x] 8 deploy — merged, pushed, deployed to the NAS 2026-08-29, on the owner's instruction; see
      Resume here and `docs/RELEASE.md`
```

Topic: private articles reachable by a secret token link (capability URL), separate from the blog —
friends see hidden articles (trip plans, personal links) without registering. Decision already made
upstream of this session: token grants read-only; editing only via the existing admin session
(SPEC F15–F18); multi-user access control rejected as overbuilt for this scale (ADR-042). No rate
limiter on the token route — entropy is already sufficient (ADR-043). Full intake, impact map and
exit criteria: `docs/iterations/I8-token-shared-articles.md`.

**T147 implemented and verified green this session.** New `app/routers/shared.py`: `GET
/s/{share_token}` is public and admin-unaware by construction (byte-identical 404 for a missing or a
wrong token, normalised only for the per-request CSP nonce and the requested address itself echoed
back in the canonical link — neither reveals which case it was); `/me/shared` is a fourth cabinet room
gated the same way as the other three (`_require_owner`, imported from `app.routers.me` rather than
duplicated); every mutating route (create, save, delete, regenerate, preview) is `CurrentAdmin`, same
as the editor GET route, matching how `blog.py`'s own editor is guarded. `shared_editor.html` reuses
`render_markdown` for its live preview through `POST /me/shared/preview`, the same pattern
`blog.py::preview` uses. New `app/static/css/shared.css` and `app/static/js/shared.js` (a generic
`data-copy-link` clipboard behaviour, not blog-specific). `cabinet_nav.html` gained one additive tuple;
`tests/api/test_me.py::test_the_rooms_name_each_other_and_mark_the_one_being_read` needed its expected
link list extended to match (not in the impact map's file list, but a direct and necessary consequence
of that additive change — flagged here per the project's "Expectations that change" convention rather
than silently patched). `tests/api/test_authz_sweep.py` untouched, confirmed by `git diff --stat`.

## Baseline I7

Recorded 2026-08-25 on `iteration/I7-direct-video-embed`, cut from `main` at `ce8cc84`, which already
carries every I6 commit merged, pushed and deployed. Tree was clean before the branch. Every command
below ran in this session, on this tree, none piped.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **370 passed**, exit 0 |
| e2e | `uv run pytest e2e -q` | **113 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | **124 files**, exit 0 |

Same counts as I6's closing tree — nothing regressed between the two sessions.

## Iteration I7 progress

```text
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred) — agreed in chat, formalised in the iteration doc
- [x] 2 impact map written
- [x] 3 docs amended (SPEC F63 edited in place, ADR-041 supersedes ADR-035, TASKS M19)
- [x] GATE approved by the owner — «утверждаю», 2026-08-25, including the two consequences the
      impact map surfaced beyond chat (poster picture retired, editor preview now reaches the host)
- [x] 4 implementation — T145, one commit
- [x] 5 verification green — unit/API **371** exit 0 (370 at Phase 0, review Run 9 added one test),
      e2e **112** exit 0 (113 at Phase 0, minus the one forced-colors test the impact map named
      "deleted, not rewritten"), lint clean, format clean **124 files**
- [x] 6 review — `docs/REVIEW.md` run 9, PASS with findings; one High and four Mediums fixed same
      session, three Lows fixed alongside them, four carried
- [x] 7 closed 2026-08-26 — all seven exit criteria met; see Resume here
```

Intake, impact map and exit criteria: `docs/iterations/I7-direct-video-embed.md`. Tasks:
`docs/TASKS.md` M19, **T145** — one task; the video-rendering path, its templates, CSS, i18n and
tests all move together.

## Baseline I6

Recorded 2026-08-25 on `iteration/I6-editing-polish`, cut from `main` at `d90ec48` — which already
carries every I5 commit (`iteration/I5-authoring` was fast-forwarded into `main`) plus one test-only
flakiness fix (`d90ec48`, `cover_of` waits for the album's own commit). Tree was clean before the
branch. Every command below ran in this session, on this tree, none piped.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **353 passed**, exit 0 |
| e2e | `uv run pytest e2e -q` | **110 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | **122 files**, exit 0 |

Same counts as I5's closing tree — nothing regressed between the two sessions.

## Iteration I6 progress

```text
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred)
- [x] 2 impact map written
- [x] 3 docs amended (SPEC F66, ADR-040, TASKS M18)
- [x] GATE approved by the owner — «утверждаю», 2026-08-25
- [x] 4 implementation — T140–T144, four commits (T140 landed prior session; T141–T143 plus the
      review fix this session)
- [x] 5 verification green — unit/API **370** exit 0 (353 at Phase 0), e2e **113** exit 0 (110)
- [x] 6 review — `docs/REVIEW.md` run 8, PASS with findings; one High and four Mediums fixed same
      session, six Lows fixed or carried
- [x] 7 closed 2026-08-25 — all six exit criteria met; see Resume here
```

Intake, impact map and exit criteria: `docs/iterations/I6-editing-polish.md`. Tasks: `docs/TASKS.md`
M18, **T140–T144**. T142 lands before T143; T140, T141 and T144 are independent and may land in any
order.

## Baseline I5

Recorded 2026-08-16 on `iteration/I4-editing-mode` at `5bd408f`, which is where `iteration/I5-authoring`
is cut from. Every command was run in that session, on that tree.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **289 passed**, exit 0 |
| e2e | `uv run pytest e2e` | **92 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | **118 files**, exit 0 |

**One inherited finding, not caused by this iteration.** The tree was dirty at the start:
`CLAUDE.md`, `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/TASKS.md`, seven skill files,
`.claude/settings.json` and two untracked files — `docs/status-archive.md`, `docs/tasks-archive.md`.
That is the previous session's split of the documents into live work and history. It touches no
application code. **Correction, 2026-08-17:** the intake claimed it was committed before I5 opened;
it was not — it was still uncommitted when this session started, and it went in at the gate
alongside I5's own amendments, so the two are in one commit rather than two.

## Iteration I5 progress

```text
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred)
- [x] 2 impact map written
- [x] 3 docs amended (SPEC F55/F38/F62 + F63–F65, ADR-032…037, TASKS M17)
- [x] GATE approved by the owner — «утверждаю», 2026-08-17
- [x] 4 implementation — T135–T139, five commits
- [x] 5 verification green, baseline suites still green — 353 / 110 / clean / 122
- [x] 6 review — `docs/REVIEW.md` run 7, PASS; one High fixed, two Mediums to ADR-038/039
- [x] 7 closed 2026-08-25 — exit criterion 8 done, by the owner's confirmation; see Resume here
```

Intake, impact map and exit criteria: `docs/iterations/I5-authoring.md`. Tasks: `docs/TASKS.md` M17,
**T135–T139**. T135 is the shared-primitive change and lands first, alone.

## Resume here

**I8 is closed, 2026-08-29, in the same session that opened it.** Branch
`iteration/I8-token-shared-articles`, cut from `main` at `b2318f0`. Both tasks in M20 are
implemented, tested and reviewed; all seven exit criteria in
`docs/iterations/I8-token-shared-articles.md` are met.

**Merged, pushed and deployed, 2026-08-29, on the owner's instruction.** `main` fast-forwarded
`b2318f0..fb72a75` and pushed to `origin`. **This carries I7 along with it** — I7 was implemented
and reviewed 2026-08-26 but never separately pushed, so `origin/main` had been sitting at I6's tip
(`ce8cc84`) the whole time; this is I7's first time live. The `publish` run on that push
(`33266553668`) is green — `tests` passed, then both images built and `latest`/`sha-fb72a75` pushed
to GHCR. **The NAS stack picked it up via the Portainer API** (stack `id=1` `portfolio`, endpoint 3,
`https://192.168.1.20:31015`): fetched the live stack file and env unchanged, `PUT` back with
`pullImage: true`, HTTP 200. All three containers came up healthy on the new image
(`portfolio-web-1`/`portfolio-caddy-1`/`portfolio-db-1`, all recreated within the same minute);
`/healthz`, `/`, `/blog`, `/photo`, `/dev` and `/sitemap.xml` all answer 200 on
`https://profile.dmkdok.crazedns.ru:8443`, `GET /s/<invalid token>` answers 404 (no existence leak)
and `GET /me/shared` answers 404 anonymous, both against the live production address. Full record,
including the rollback plan (redeploy pinned to `sha-30010b9`, I6's build — safe because
`a37da390e9d0` only adds a table): `docs/RELEASE.md`.

**T146/T147 in one line each.** **T146** gave the site a `shared_article` table, separate from
`post` — same base model pattern, its own Alembic revision, migration proved up and down on the dev
database rather than a fixture. **T147** is a friend opening a shared article by its link and the
owner managing those articles from the cabinet: `GET /s/{share_token}` is public and
admin-unaware by construction — a missing token and a wrong token answer byte-identical 404s, so
neither leaks which case it was; `/me/shared` is a fourth cabinet room gated by `_require_owner`
exactly like the other three; every mutating route (create, save, delete, regenerate, preview) is
`CurrentAdmin`; the article is absent from `/sitemap.xml`, `/search` and every public nav element by
construction, and carries `noindex` unconditionally (ADR-042 records the token-not-multi-user
decision and the read-only guarantee; ADR-043 records why the public route carries no rate limiter —
`secrets.token_urlsafe(32)` is 256 bits, brute force is infeasible regardless of a limiter).

| | | State |
|---|---|---|
| **T146** | a `shared_article` table exists, separate from `post` | **done**, `1e7eb47` |
| **T147** | a friend opens a shared article by its link | **done**, `82deab8` |
| | review run 10's High: the shared editor carried none of F50's unsaved-text guard | **fixed**, `a6b4ffd` |

**Gates on I8's closing tree, none piped, independently re-run this session (not taken on the
record's word):** unit/API **399** exit 0 (371 at the baseline, 394 before the review fix), e2e
**115** exit 0 (112 at the baseline, 113 before the review fix), `ruff check` clean, `ruff format
--check` **130 files** exit 0. Matches the counts `docs/REVIEW.md` run 10 and the review-fix commit
both claim — nothing drifted between what was recorded and what the tree actually does.

**Review: `docs/REVIEW.md` run 10, PASS with findings, all resolved same day, same branch** — run by
an independent reviewer agent, no write access to application code, with `secure-review` mandatory
per the impact map (the first bearer-token capability-URL route in the codebase, and the first new
admin-CRUD surface since I6). Migration reversibility was re-proved independently, not just re-read:
`alembic downgrade -1` against the live dev database, table confirmed gone, `alembic upgrade head`
restored it, full suite re-run green. One High fixed (see table above), two Mediums fixed
(`share_token` redacted out of the uvicorn access log and the global 500 handler; the a11y sweep
extended from the trivial list page to the actual new interactive surface, `/me/shared/{id}/edit`),
one Medium carried deliberately (`noindex` without `nofollow`/`Disallow: /s/` — matches F69's letter
exactly, no code change), two Lows fixed (a dead i18n key, a stale "three cabinet rooms" comment in
two files). No Critical or High security finding — `secure-review` probed 404 byte-identity, token
generation and comparison timing, XSS, CSRF, authz, IDOR and SSRF, all closed by construction.

**What actually landed is in `docs/iterations/I8-token-shared-articles.md`** — its impact map and
exit criteria, all ticked.

**Two things to expect if you carry this forward.**

1. **A page's own comment claiming it mirrors a sibling's behaviour is not proof the behaviour is
   actually wired.** `shared_editor.html` said, in its own comment, "the same idea as the blog
   editor" and used the identical `hx-trigger` pattern — but the script that actually implements
   F50's unsaved-text guard, `editor.js`, was hardcoded to the blog editor's own DOM ids and was
   never loaded on the shared page at all. Every test that ran green for this iteration was silent
   about it because none of them typed into the body textarea; the one file in the suite that tests
   exactly this path, `e2e/test_editor_guard.py`, was never extended to a second editor. **When a new
   page's markup or comments claim to model an existing one, check that the behaviour-carrying script
   is actually loaded on it** — a matching pattern in the template is not the same claim as a matching
   script tag.
2. **A URL that embeds a secret is a new kind of thing to this codebase's logging, and nothing forces
   a re-check of assumptions that held before it existed.** Every prior path in this application —
   blog slugs, `/me/*`, admin content keys — was safe to log verbatim, so uvicorn's default access log
   and the global 500 handler both did, unexamined. `/s/{share_token}` is the first path segment in
   the app that is itself a bearer credential, and nothing about ADR-042 or ADR-043 (both about the
   token's entropy and read-only scope) says anything about where the token ends up in a log stream.
   **A new URL shape is worth asking "does this path itself carry something secret" about, independent
   of whether the route's authorisation is correct** — the two questions have different answers here,
   and only one of them was asked before review.

**Merging is the owner's call** and, since T127, a push to `main` runs the suite and the lint gate
before it builds anything.

Everything below this line is I7's record and is still true.

---

**I7 is closed, 2026-08-26, in the same session that opened it. Merged into `main` 2026-08-28** at
the start of the I8 baseline (fast-forward, no conflicts; not pushed or deployed by that merge alone
— see `## Baseline I8` above for what that session also committed first). Branch
`iteration/I7-direct-video-embed`, cut from `main` at `ce8cc84` — which already carries every I6
commit merged, pushed and deployed. The one task in M19 is implemented, tested and reviewed; all
seven exit criteria in `docs/iterations/I7-direct-video-embed.md` are met.

**T145 in one line: a video in an article is now a real `<iframe>` from the moment the page
renders**, not a `<button>` facade a reader had to press first (F63, ADR-041, supersedes ADR-035).
`ALLOWED_TAGS`/`ALLOWED_ATTRIBUTES` swap `button` for `iframe`, closed the same way `data-video` was
— nh3 filters attribute names, never values, so `iframe.src` can only ever be a value already matched
against `_VIDEO_SERVICES`'s anchored per-host patterns. `video.js` is deleted along with its three
`<script>` inclusions and `prose.css`'s facade rules. The poster-picture affordance is retired — a
live iframe already shows the host's own thumbnail, so the picture that used to sit behind the button
no longer renders; its `title`, or `alt` failing that, still reaches the `<figcaption>`. ADR-038's
excerpt special-case is deleted as dead code, its outcome now falling out of ordinary tag-stripping.

| | | State |
|---|---|---|
| **T145** | a video plays from one press, not two, real embed from the start | **done**, `e4f01fc` |
| | review run 9's High: `autoplay=1` survived the move with nothing gating it | **fixed**, same session |

**Gates on I7's closing tree, none piped:** unit/API **371** exit 0 (370 at the baseline, review Run
9 added one excerpt test), e2e **112** exit 0 (113 at the baseline — the one fewer is
`test_the_video_facade_keeps_its_plates`, deleted per the impact map, not a silent loss), `ruff check`
clean, `ruff format --check` **124 files** exit 0. Admin sweeps: focus **207 stops / 0** without an
indicator (88/0 anonymous), targets **171 under 44 px / 0** under WCAG 2.5.8 (65/0 anonymous),
contrast **141 samples / 0 failures** admin both themes, **84/0** anonymous both themes (85 at I6 —
one fewer picture renders on the anonymous video article now that the poster is retired).

**Review: `docs/REVIEW.md` run 9, PASS with findings, all resolved same day, same branch** — run by
an independent reviewer agent, no write access to application code, with `secure-review` mandatory
on the `iframe`-allow-list change per ADR-041 (the first time `iframe` has been allowed since
ADR-035 first excluded it). `iframe.src` was probed with fifteen adversarial Markdown bodies and
found closed by construction, not merely untested; two independent locks (nh3's own scheme filter,
CSP's `frame-src`) were shown to survive even if that construction were ever wrong. One High fixed
(see table above), four Mediums fixed, three Lows fixed alongside them, four Lows carried with
reasons.

**What actually landed is in `docs/iterations/I7-direct-video-embed.md`**, including two items ("no
autoplay parameter", "focus-sweep exemption scoped to one class") added to "Expectations that
change" after the review, not before — the plan approved in chat did not anticipate either.

**Two things to expect if you carry this forward.**

1. **A parameter correct under the old design can become actively wrong under the new one, and
   nothing forces a re-read of *why* it was there.** `?autoplay=1` was right on ADR-035's facade — by
   the time the iframe existed the reader had already pressed play once — and T145's own approved DoD
   text carried it into the direct-embed rewrite unchanged, `allow="autoplay; …"` included. The
   precondition that made it safe (a prior press) is exactly what this iteration removed, and nobody
   re-derived the parameter from scratch until review did. **When a rewrite keeps a literal value from
   the design it replaces, ask what made that value correct before, and whether the replacement still
   provides it** — not whether the value itself still parses.
2. **An element whose contents a browser never displays is not an element whose contents don't
   matter.** `<iframe>…</iframe>`'s inner tokens are inert on screen, so `**bold**` or `` `code` ``
   left inside one (only its *text* was being suppressed, not its markup tags) was invisible to a
   reader and to every visual sweep — but `nh3.clean`'s tag-stripping still read those tags as
   content, and `excerpt_from` stored what was left. **A defect three steps removed from anything a
   screen renders can still land in a stored field a moment later in the same pipeline** — the fix
   here was to drop the tokens from the stream entirely rather than trust a render-time suppression to
   catch every token type that could appear between them.

**Merging is the owner's call** and, since T127, a push to `main` runs the suite and the lint gate
before it builds anything.

Everything below this line is I6's record and is still true.

---

**I6 is closed, 2026-08-25, in the same session that opened it.** Branch
`iteration/I6-editing-polish`, cut from `main` at `d90ec48`. All five tasks in M18 are implemented,
tested and reviewed; all six exit criteria in `docs/iterations/I6-editing-polish.md` are met.

**Merged, pushed and deployed, 2026-08-25, on the owner's instruction.** `main` fast-forwarded
`d90ec48..30010b9` and pushed to `origin`. The `publish` run on that push (`32886056210`) is green —
`tests` passed, then both images built and `latest` moved to `sha-30010b9`. **The NAS stack picked it
up via the Portainer API** (stack `id=1` `portfolio`, endpoint 3, `https://192.168.1.20:31015`):
fetched the live stack file and env unchanged, PUT back with `pullImage: true`, HTTP 200. All three
containers came up healthy on the new image (`web` container recreated `2026-08-25T18:57:05Z`);
`/healthz` answers 200 on both `http://192.168.1.20:8080` and
`https://profile.dmkdok.crazedns.ru:8443`.

M18 in one line each: **T140** stopped the owner's tools from blurring the photograph under them in
«Правка»; **T141** gave «Файлы на диске» its top margin when the room above it is otherwise empty;
**T142** taught the video toolbar and cheat sheet the captioned link form every service already
supports; **T143** fetches a YouTube or Rutube link's own title automatically, server-side, once, at
edit time (F66, ADR-040 — VK stays manual); **T144** closed ADR-038's deferred fix — a video's own
control label no longer leaks into an auto-generated excerpt or meta description.

| | | State |
|---|---|---|
| **T140** | the owner's tools stop blurring the photo they sit on | **done**, `28938e0` |
| **T141** | the disk section gets a top when the room above it is empty | **done**, `4f5bf91` |
| **T142** | the editor teaches the captioned form, not just the bare link | **done**, `109c38a` |
| **T144** | a video's own label stays out of the excerpt | **done**, `910c7fe` |
| **T143** | a YouTube or Rutube link fills its own caption | **done**, `8c4f0db` |
| | review run 8's High: the button's own next gesture produced a dead link | **fixed**, `ec9b573` |

**Gates on I6's closing tree, none piped:** unit/API **370** exit 0 (353 at the baseline, 367 before
the review fix), e2e **113** exit 0 (110 at the baseline, 111 before the review fix), `ruff check`
clean, `ruff format --check` **124 files** exit 0. Admin sweeps: focus **207 stops / 0** without an
indicator (88/0 anonymous), targets **171 under 44 px / 0** under WCAG 2.5.8 (65/0 anonymous),
contrast **141 samples / 0 failures** admin, **85/0** anonymous, both themes.

**Review: `docs/REVIEW.md` run 8, PASS with findings, all resolved same day, same branch** — run by
an independent reviewer agent, no write access to application code, with `secure-review` mandatory
on T143 per ADR-040 (first time this codebase has the server call out to a third party on the
owner's own action). One High fixed (see table above), four Mediums fixed, six Lows fixed or carried
with reasons. SSRF on T143 was probed with eight adversarial inputs and found closed by
construction, not merely untested.

**What actually landed, in one paragraph each, is in `docs/iterations/I6-editing-polish.md`.** Read
that before touching any of this.

**Two things to expect if you carry this forward.**

1. **Two tasks that each look correct in isolation can still fight each other at the interaction
   level.** T142 deliberately left the video button's caption selected (so a video starts captioned
   rather than anonymous); T143's paste-triggered auto-fill only recognised the address landing in
   the address slot. Pressing the button and immediately pasting the clipboard's video link — the
   most direct thing to do — landed the paste in the *selected caption* instead, and nothing in the
   suite caught it because no test simulated a paste *after* a toolbar insertion, only the
   insertion's own output. **Before trusting a multi-step UI flow, act it out**, not just each
   step's own assertion — an interaction's correctness is not the sum of its parts' correctness.
2. **A GET that can fail auth is not a safe default for a JSON endpoint on this site.** `main.py`'s
   401 handler redirects any failing `GET` to `/login` (written for page navigation), so a JSON
   route reachable by `GET` hands an anonymous caller a login page's HTML instead of a 401. T143's
   own anonymous test caught this before it shipped; every admin JSON endpoint in this codebase is
   now consistently a `POST` for exactly this reason — check that first, not the auth dependency,
   the next time an admin JSON route answers something unexpected to a stubbed anonymous test.

**Merging is the owner's call** and, since T127, a push to `main` runs the suite and the lint gate
before it builds anything.

Everything below this line is I5's record and is still true.

**One thing not ticked, and not this session's to tick.** I4's exit criterion 7 — the owner's own
pass through one full publishing flow using only the new menu and the new mode — looks, on the face
of it, satisfied by the pass that closed I5's criterion 8 (it used exactly that menu and mode). It is
left unticked here anyway: nobody has said so explicitly, and M16 cannot close in any case until
T128 and T129 (the appliance) are also done. Worth asking the owner directly rather than inferring
it.

**M17 closed 2026-08-25.** All five tasks were already implemented, tested, reviewed and committed
on `iteration/I5-authoring`, which this session found already fast-forwarded into `main` at
`d90ec48` (one test-only flakiness fix past I5's own last commit, `cover_of` waits for the album's
own commit rather than the photo's). **Exit criterion 8 — the owner's own pass, writing one
article with a picture at a chosen width and a video, using only the editor's own cheat sheet,
publishing it and reading it in both modes — is done, by the owner's confirmation**, and it is what
surfaced the three findings I6 opens with. The written-but-never-run tick this project paid for
once in T086 did not repeat here: the pass was actually run, and it is the reason I6 exists.

| | | State |
|---|---|---|
| **T135** | «Просмотр» is the page a visitor reads, on every page | **done**, `2c88ae6` |
| **T136** | «фотогр» finds «фотография» — a union, not a substitution | **done**, `584e561` |
| **T137** | the cabinet gets rooms, and «Снимки без описания» leaves it | **done**, `ea3e1bf` |
| **T138** | a video is a facade the reader opts into | **done**, `c59260a` |
| **T139** | the editor says how the markup works | **done**, `33381b5` |
| | review run 7's High: `/dev` was still draggable in «Просмотр» | **fixed**, prior session |

**Gates on I5's closing tree, none piped:** unit/API **353** exit 0 (289 at the
baseline), e2e **110** exit 0 (92 at the baseline, 107 before the review fix),
`ruff check` clean, `ruff format --check` **122 files** exit 0. Admin sweeps: focus
**207 stops / 0** without an indicator, targets **171 under 44 px / 0** under WCAG
2.5.8, contrast **141 samples / 0 failures** in both themes.

**Review: `docs/REVIEW.md` run 7, PASS**, independent of the implementing
sessions. One High, fixed; four Mediums, all closed — two by the fix and the
close, two by **ADR-038** and **ADR-039**; five Lows carried with reasons. It
records `secure-review` run as the manual checklist with **no Critical or High
security finding**, and says plainly that Semgrep is not installed on this host
and no scan was fabricated.

**What actually landed, in one paragraph each, is in
`docs/iterations/I5-authoring.md`** — six sections, one per task plus *Run 7
landed*, each listing what the plan did not say. Read those before touching any of
this; they are where the reasons live.

**Three things to expect if you carry this forward.**

1. **The marker only reaches what the marker is written on.** Run 7's High was
   `/dev` still being drag-reorderable in «Просмотр», because `dev-sortable.js`
   dragged from `.project__body` — the card's own content, which no `owner-only`
   can take away. Exit criterion 4 counts rendered boxes and a drag target is not
   a box. **Before trusting a box count, grep the JavaScript for selectors that
   name a shared element** — a behaviour attached by a selector in a script is
   invisible to it.
2. **A test that asserts «nothing happened» passes whenever nothing happened, for
   any reason.** The red run for that fix passed twice on the broken tree:
   `bounding_box()` is viewport-relative, so cards below the fold gave
   coordinates the mouse could not reach; and `reload()` straight after
   `mouse.up()` aborted the htmx POST before it landed. Assert on the request,
   which exists only if the thing happened, and only then on the state.
3. **A new i18n key still needs `docker compose restart web`**, and a full e2e run
   started before `/healthz` answers fails all of them in fixture setup. Both cost
   a debugging round in earlier iterations and nothing since they were written
   down.

**One line still open, one taken up.** `.project__handle` in `dev.css` restates `.photo-handle`
from `photo.css` because `/dev` does not load that stylesheet — one drag handle, two definitions,
still unfixed. ADR-038's excerpt fix — held back at I5's close because it changes every card and
every meta description on two sections — **was T144 in I6**, now done.

**Merging is the owner's call** and, since T127, a push to `main` runs the suite
and the lint gate before it builds anything.

Everything below this line is I4's record and is still true. **M16 remains open:
T128 and T129 are the owner's and need the appliance.** I4's exit criterion 7 — the
owner's own pass through one publishing flow — is likely satisfied by the same pass
that closed I5's criterion 8 (see "One thing not ticked" above), but that is an
inference, not a confirmation, and M16 cannot close on T128/T129 alone regardless.

---

**Iteration I4's code is finished. The iteration is not, and M16 is not ticked.** All four tasks are
implemented, tested, reviewed and committed on `iteration/I4-editing-mode` (cut from `main` at
`a0d1ecf`). Nothing is left in I4 that a session can do — **what remains is exit criterion 7, the
owner's own pass through one full publishing flow using only the new menu and the new mode.** No
test stands in for it, and the written-but-never-run tick is the T073 mistake this project already
paid for once in T086.

| | | State |
|---|---|---|
| **T131** | the admin bar retires into the navigation capsule | **done**, `cc403a5` |
| **T134** | `docs/` leaves ruff's discovery, so prose stops being formatted as code | **done**, `1eec8cb` |
| **T132** | «Просмотр» / «Правка» replace hover and the toggle on top of it | **done**, `82a3eef` |
| **T133** | the cabinet at `/me` — one page that says what needs the owner | **done**, `f75d1da` |
| | exit criterion 4: the visitor guard sweeps four pages, not one | **done**, `c5fba5b` |

**Gates on the closing tree, none piped:** unit/API **289** exit 0 (277 at the baseline), e2e **92**
exit 0 (81 at the baseline, 88 after T131), `ruff check` and `ruff format --check` clean over 118
files. Review: **`docs/REVIEW.md` run 6, PASS**, with two Low security findings recorded rather than
fixed and a plain statement that it is a self-review.

**What actually landed, in one paragraph each, is in `docs/iterations/I4-editing-mode.md`** — three
sections, *T131 landed*, *T132 landed* and *T133 landed*, each listing what the plan did not say.
Read those before touching any of this; they are where the reasons live.

**Two things to expect if you carry this forward.**

1. **The impact map undercounts the tests that carry a behaviour change, every time so far.** T131
   owed four more than the map named; T132 owed **seven** more, in three files the map never
   mentioned — every in-place editing flow, all passing until then only because `opacity: 0` is
   clickable. Before starting anything that changes a resting state, grep `e2e/` for locators that
   describe the old behaviour, not just the files the map lists.
2. **A new i18n key needs `docker compose restart web`.** `translate()`'s catalogue is `@lru_cache`d
   per process, and a missing key renders as its own dotted name — which looks exactly like markup
   that failed to render. It cost a debugging round in T131 and was cheap in T132 and T133 because
   it was written down.

**Two lines for the next intake, deliberately not fixed here.** The cabinet's «Снимки без описания»
list is unbounded and its rows are indistinguishable — on the owner's real data it renders 24 rows
all reading «Снимок в альбоме «X»», told apart only by where they lead; that is also the first
evidence for the trigger ADR-029 records, which is photographs at scale. And **ADR-029's own
consequences line is stale**: it says `/me` joins the parametrized admin-read case in
`test_authz_sweep.py`, which it does not and must not — that case asserts redirect-to-login
semantics and this route answers 404 by decision. The impact map said so first; both statements are
in the record and neither was edited away.

**Merging is the owner's call** and, since T127, a push to `main` runs the suite and the lint gate
before it builds anything.

Everything below this line is I3's record and is still true. **T128 and T129 remain open and remain
the owner's** — they are not blocked by I4 and I4 does not touch them.

---

**I3 is merged, pushed and deployed.** `main` = `38456e5`, fast-forwarded from
`iteration/I3-operations` (33 commits) and pushed to `origin`
(`https://github.com/Dmkdok/personal-site.git`). The `publish` run on that push
(`31895713071`) is **the first release in this project's history whose image was gated by a test
run** — `tests` green, then both images built and `latest` moved to `sha-38456e5`.

**The NAS stack is running that image, deployed 2026-08-15 via the Portainer API** (stack `id=1`
`portfolio`, endpoint 3, Portainer 2.44.0 on `https://192.168.1.20:31015`). All three containers
healthy; `https://profile.dmkdok.crazedns.ru:8443` answers 200 on `/`, `/photo`, `/blog`, `/dev`,
and `/healthz` answers 200 on both the LAN and the public address.

The dev stack (`db`, `web`) is up locally; `docker compose down` stops it. Docker Desktop is not
always running on this host — start it and wait for `docker info` before the first suite.

**Two traps this session hit, both cheap to avoid.** A full e2e run started immediately after
`docker compose restart web` fails all 81 at fixture setup, because the site is not answering yet —
wait for `/healthz` first. And Git Bash rewrites container-absolute paths on this host, so
`docker compose run -e LOG_DIR=/tmp/x` arrives inside the container as `C:/Users/...`; prefix the
command with `MSYS_NO_PATHCONV=1`. The same conversion makes `tar` treat a `C:/...` `BACKUP_DIR` as
a remote host and fail — give `scripts/backup.sh` a POSIX-relative path.

**Iteration I3's code is finished. The iteration is not, and M15 is not ticked.** Its page —
intake, the re-cut, the impact map, both pipeline defects and the exit criteria — is
**`docs/iterations/I3-operations.md`**. Milestone **M15** in `docs/TASKS.md`, six tasks:

| | | State |
|---|---|---|
| **T125** | the dedup race: an upload could answer 500 | **done**, `4255ec4` |
| **T130** | a photo failing *after* the render spins instead of failing | **done**, `6867154` |
| **T126** | the log as a file on disk + log ceilings | **done**, `0ec22c1` |
| **T127** | the suite gates the published image | code done `729fce3` — **needs a push to prove** |
| **T128** | a dump that runs on the server + snapshot task | script + docs done `66455ca` — **needs the snapshot task** |
| **T129** | an external check on `/healthz` | docs done `66455ca` — **needs the cron job** |

**Gates at the close (2026-08-15):** unit/API **277** exit 0, e2e **81 passed exit 0 twice
consecutively**, six launch flows 6 passed, lint and format clean over 53 files. The baseline's
intermittent 500 did not recur, and neither did the unexplained login failure recorded below.

**What is left is the owner's and only the owner's — do not tick any of it from a session.**

1. ~~**T127**~~ — **done 2026-08-15.** Proved on `scratch/t127-proof` by dispatch: red run
   `31895410780` → `tests` failure, `publish` skipped, no image; green run `31895508616` → `tests`
   success, both `publish` jobs success, `sha-0849b46` published and `latest` untouched. Branch
   deleted.
2. **T128** — create the Periodic Snapshot Task in the TrueNAS interface. The dataset, schedule and
   retention are specified in `docs/HANDOFF.md` §5; paste the resulting listing into the iteration
   page.
3. **T129** — create the cron job in `docs/HANDOFF.md` §7 and **verify it by stopping `web`**, not
   by watching it go green.
4. ~~**T126's last mile**~~ — **done 2026-08-15.** `app.log` is live on the appliance at
   `/mnt/tank/app_data/_dev_/portfolio/logs`, 1000:1000, carrying the same lines as stdout, and the
   grep against the production stack variables is clean (the only match is the admin *username* in
   `admin account ready: admin`, a line from M2 — not a credential).

   **`logs` is a plain directory, not a dataset, and that was the right call.** A dataset buys
   nothing: the recursive snapshot task on the parent already covers it, `atime=off` is inherited,
   and the application caps the file at 5 MB × 4 itself. The session initially insisted on a dataset
   out of convention, hit TrueNAS refusing to create one over an existing path, and was heading for
   a root cron job to `rmdir` it — the owner's question ("why can't the log write the way the photos
   do?") cut that off. The answer was ownership, never ZFS.

   **The deploy before the chown proved the non-negotiable in production**, which is worth keeping:
   the stack came up with the directory still root-owned and logged

   ```
   WARNING [portfolio] LOG_DIR /data/logs is not usable
   ([Errno 13] Permission denied: '/data/logs/app.log'); logging to stdout only
   ```

   — then migrated, seeded the admin and served 200s. A log path is not the reason the site is down.

**Merging is the owner's call and the consequence is now different from what it was.** A push to
`main` runs `publish`, which since T127 runs the suite and the lint gate first and builds nothing if
they fail. `latest` still follows `main` — but only a green `main`. The sane order is still to prove
T127 on a scratch branch before trusting it.

**Iteration I2 is complete.** `docs/TASKS.md` has no unticked line, M11 through M14. Its page is
**`docs/iterations/I2-pagination-media-phaseb.md`**; the review is run 4 in `docs/REVIEW.md`.

**One intermittent was seen and is not explained.** In one full e2e run of three, the
`admin_storage_state` fixture failed at setup: the login POSTed and answered `303`, and the page it
redirected to came back anonymous — no admin bar, so the session cookie was issued and then not
honoured. It did not recur on the next run, and the same fixture succeeds fifteen-odd times in every
run. Two runs of that batch also had the app restarting underneath them, because a `git stash` cycle
of `app/**` (used to watch a test go red) trips uvicorn's `WatchFiles` reloader — **so do that with
the stack down, or expect `ERR_EMPTY_RESPONSE` in the middle of a suite.** Whether the login failure
was the same disturbance or something in `end_session`'s token rotation is genuinely unknown. It is
the first thing to chase if it shows up again; there is nothing to fix until it does.

**The audit is now half finished, deliberately, and it says so itself.** Phase A (P1) closed in I1;
Phase B (P2) closed in I2, with F-016 closed as not-a-defect by ADR-020. Seven P3 findings
(F-019…F-022, F-024…F-026) remain open, deferred by ADR-017. `docs/UI-AUDIT.md` carries the register
at the top — that is the only edit ever made to it, and the findings below it are untouched.

## Baseline I4

Recorded 2026-08-16 on `iteration/I4-editing-mode`, cut from `main` at `a0d1ecf` (the I3 close,
merged and deployed). Every command below was run in this session, on this tree, none piped.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **277 passed**, exit 0 |
| e2e | `uv run pytest e2e` | **81 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | **1 file would be reformatted**, exit 1 |

**Two inherited findings, neither caused by this iteration.**

1. **`.env` was unparseable, so every `docker compose` command failed** — not only the suite:
   `failed to read .env: line 17: key cannot contain a space`, which is a failure of the file's
   parse, so `up`, `logs` and `test` were all dead. The owner had edited the file and fixed it on
   being shown the error; nothing in the repository changed. **If a later session sees Docker
   "broken", read this line before restarting anything** — `docker compose config --quiet` says so
   in one second.
2. **`ruff format --check` is red on `docs/iterations/I3-operations.md`.** I3's baseline recorded
   *"clean, 127 files"*; the count is 128 now and the extra file is the I3 iteration page itself,
   written during I3 after the last format check and never checked. Ruff formats fenced Python
   inside Markdown and wants to rewrite the T125 dedup excerpt, whose aligned trailing comments are
   the explanation. **ADR-030 / T134** takes `docs/` out of ruff's discovery. Nothing else is red.

The intermittent 500 that made I3's baseline amber did not recur.

```text
Iteration I4 progress:
- [x] 0 baseline recorded (branch, suite result, timestamp)
- [x] 1 delta intake agreed (in / out / deferred)
- [x] 2 impact map written
- [x] 3 docs amended (SPEC F36/F55 reworded, F61/F62 added; ADR-027…031; TASKS M16)
- [x] GATE approved by the owner — «утверждаю», 2026-08-16
- [x] 4 implementation — T131, T134, T132, T133, all four ticked
- [x] 5 verification green — unit/API **289** exit 0 (277 at baseline), e2e **92** exit 0 (81),
      lint and format clean over 118 files; exit criterion 4 closed by strengthening the guard
- [x] 6 review — `docs/REVIEW.md` run 6, PASS, two Low security findings recorded not fixed;
      it says plainly that it is a self-review rather than an independent one
- [ ] 7 closed — **M16 cannot be ticked**: exit criterion 7 is the owner's own publishing pass
```

**Both inherited findings are closed.** The `.env` parse was the owner's edit and never touched the
repository; `ruff format --check` is green over the whole tree since T134 took `docs/` out of ruff's
discovery (ADR-030).

## Open problems and bugs, all of them

Ordered by what bites first. Items 1–3 are consequences of this deployment; 4–8 predate it or sit
beside it.

1. **`SITE_URL` advertises `http://192.168.1.20:8080` to the internet.** Canonical, Open Graph,
   `sitemap.xml`. One variable in Portainer, then redeploy. Note the replacement must carry the
   port: `https://profile.dmkdok.crazedns.ru:8443`.
2. **The login throttle is shared by every external visitor** — no `X-Forwarded-For` from the
   router, so everyone is `192.168.1.1`. Five wrong passwords from a stranger lock the owner out
   for 15 minutes, with no LAN fallback because the LAN address is plain HTTP and the cookie is
   `Secure`. Detail above.
3. **No backups are scheduled.** No ZFS snapshot task on `media` or `pgdata`, no `pg_dump` cron.
   Harmless while the site is empty; not harmless the moment content exists. `make backup` does
   not apply here — see `docs/HANDOFF.md` §6.1.
4. **The Cyrillic font is downloaded twice on every cold load.** `base.html` preloads it through
   `static_url`, so the preload URL carries `?v=…`, while the `@font-face` rule asks for the same
   file without a query. The preload never matches, and it is the LCP-critical font. Pre-existing.
5. **CI runs no tests.** `publish.yml` builds and pushes; `latest` follows `main` in whatever state
   `main` is. The local gates are the only gates.
6. **The appliance runs TrueNAS 26.0.0-BETA.2.** A beta OS under a live site. Nothing has
   misbehaved, but it is worth knowing before diagnosing anything strange.
7. **`docs/TASKS.md` has no milestone for any of this work.** The deployment happened outside the
   M-numbering; it is the one place the tree and the checklists disagree.
8. **Credential hygiene, outstanding.** The TrueNAS account password and four tokens were pasted
   into a chat transcript. The classic GHCR PAT is *in use* — it is Portainer's registry credential
   — so it must be replaced in Portainer before being revoked, not after. `Test_Key` in TrueNAS is
   revoked and should be deleted. Full order of operations at the end of this session's notes.

Older functional gaps — article-image CLS, touch-target sizing, two labelling gaps, draft Russian
copy — are unchanged and live in `docs/HANDOFF.md` §8.

**Not a bug, but it will cost time again.** `media`, `pgdata` and `backups` are separate ZFS
datasets, so anything rooted at `portfolio` that does not cross a mount boundary shows them as empty
directories. Two consequences already met: an SMB share must be created on `media` itself, not on
the parent; and the **File Browser app cannot see them at all** — it bind-mounts `/mnt/tank` with
`propagation=rprivate` and has been running since 10 July, so mounts created afterwards never
entered its namespace. Restarting that app fixes it, and will be needed again for every future
dataset, ours or anyone's.

## Test report

Each gate below carries its own last-run timestamp and the command that produced it.

| Gate | Command | Last run | Result |
|---|---|---|---|
| Unit + API | `docker compose run --rm tests` | 2026-09-01, this session, on `470215b` | **399 passed**, exit 0 |
| End-to-end | `uv run pytest e2e -q` | 2026-09-01, this session, same tree | **4 failed, 3 errors**, exit 1 — see Resume here for detail and the unconfirmed drift hypothesis |
| Lint | `uv run ruff check .` | 2026-09-01, this session, same tree | clean, exit 0 |
| Format | `uv run ruff format --check .` | 2026-09-01, this session, same tree | clean, 130 files, exit 0 |

**e2e failing tests, named individually (2026-09-01):** three known pre-existing —
`test_upload_guard.py::test_files_that_cannot_succeed_never_reach_the_network`,
`test_view_parity.py::test_edit_mode_still_drags_the_project_board`,
`test_view_parity.py::test_named_owner_surfaces_have_no_box_in_view_mode[chromium-/dev-[data-drag-handle]]`
— plus four new, not seen at Baseline I9: `test_editor_guard.py::test_publishing_counts_as_saving`
(FAILED) and setup errors on `test_me.py::test_a_shared_articles_link_survives_only_until_it_is_reissued`,
`test_search.py::test_showing_the_rest_of_a_group_keeps_the_caret`,
`test_site_links.py::test_the_owner_changes_a_link_and_a_visitor_sees_it` (all three ERROR at the
same `admin_storage_state` fixture step, same cause — see Resume here).

No failing tests. **Iteration I2 grew the suite 233 → 271 and 60 → 81**, against the baseline in
`## Baseline I2` taken before the change request was read. Iteration I1 before it grew 224 → 226 and
40 → 57, and the search-field fix that followed took e2e to 60.

**Only the tests the impact map named were edited**, plus one it did not: `e2e/test_login.py`'s
unscoped `get_by_role("alert")`, which resolves to two elements once the toast host has a permanent
alert region on every page. Everything else new is an addition, and every addition fails without the
change it guards — with one named exception, T112, argued in the iteration doc.

`-q` is set twice, so a passing run prints dots and no summary line. **Read the exit code.** Never
pipe a test run through `tail` or `grep`: you get the pipe's status and a red suite reads as green.

**Two traps this machine cost time on, both of which will recur.** The i18n catalogue is behind
`@lru_cache` in `app/templating.py`, so a **newly added translation key does not appear until the web
container restarts** — it surfaces as the raw key (`blog.save_failed`) rendered on the page, and it
cost one confusing red test. `docker compose restart web`, then wait for `/healthz` before running
e2e; a run started against a restarting container fails at the `_site_is_up` fixture with
`RemoteDisconnected`, which looks nothing like the real cause. And `docker compose run --rm tests
<path>` **replaces the command rather than appending to it** — the service's command is
`["python", "-m", "pytest", "-q"]`, so a single file is run as
`docker compose run --rm tests python -m pytest <path>`.

**Nothing is known bad.** Every task in every milestone including M10 is done and ticked; the only
unticked item anywhere is T074, the production deploy, which the owner has chosen to run himself.

## Notes

Dated entries from the session that is current. Everything up to 2026-08-11 is in
`docs/status-archive.md` under "Notes, 2026-08-04 to 2026-08-11"; the traps out of it that are still
load-bearing are recorded where they are needed instead of here — `CLAUDE.md` for the test and
Serena rules, `docs/CONVENTIONS.md` for the rest.

**2026-09-01.** T148 landed and was independently re-verified (see Resume here). T149 was attempted
in a background implementer subagent, hit unexplained a11y test failures partway through its own
diagnosis, and was stopped and reverted rather than committed half-working — see Resume here for
the exact anomaly seen on the re-verification run afterward (3 new login-fixture errors, 1 new
autosave-message failure, on top of the 3 already-known pre-existing failures). Not fixed, not
explained past a hypothesis — written down for the next session per this project's own rule.
**This file is ~63 KB, well past the ~20 KB hygiene bar in the `pause` skill's step 4b** — I3/I4/I5's
old baselines and progress blocks below this point were never migrated to `docs/status-archive.md`
when their iterations closed. Not done this pause (time-boxed, owner asked to push urgently); worth
a dedicated pass before the file grows further.

## History

Closed baselines I1, I2 and I3, the 2026-08-13 deployment record and the session notes that came
with them are in `docs/status-archive.md`. The same history in narrative form, one file per
iteration, is in `docs/iterations/`. Neither is needed to resume work: this file is the handoff.

