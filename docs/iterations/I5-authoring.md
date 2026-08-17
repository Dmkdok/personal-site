# I5 — The visitor's view, video, and a cabinet with rooms

Cut from `iteration/I4-editing-mode` at `5bd408f`. Source: an owner request in session on
2026-08-16, seven parts. Four of them are the same complaint from four directions — **the mode I4
built stops at three selector families, and everywhere else the owner's page is still the owner's
page.** The other three are new capability: video in an article, a markup cheat sheet that says how
picture size works, and a search that matches a word from its beginning.

## Baseline

Recorded 2026-08-16 on `iteration/I4-editing-mode`. Every command was run in this session, on this
tree.

| Suite | Command | Result |
|-------|---------|--------|
| unit/API | `docker compose run --rm tests` | **289 passed**, exit 0 |
| e2e | `uv run pytest e2e` | **92 passed**, exit 0 |
| lint | `uv run ruff check .` | clean |
| format | `uv run ruff format --check .` | **118 files**, exit 0 |

**One inherited finding.** The tree was not clean: `CLAUDE.md`, `docs/DECISIONS.md`,
`docs/STATUS.md`, `docs/TASKS.md`, seven skill files, `.claude/settings.json` and two untracked
files — `docs/status-archive.md`, `docs/tasks-archive.md`. That is the previous session's split of
the documents into live work and history; it touches no application code. Committed on its own
before I5 opened, so this iteration's diff is only this iteration's.

## Intake

**Source.** Owner request, 2026-08-16, in session. Seven parts, all accepted; the owner chose one
iteration over two.

### In

| | Change | Acceptance — what the owner will look at |
|---|---|---|
| **A** | **«Просмотр» becomes the visitor's page, everywhere.** Not three families of control but every control, every owner-only mark, and every unpublished card. | On an album in «Просмотр» there is no uploader, no «Изменить», no drag handle, no dashed rim around an undescribed photograph, no draft chip — and the same on `/blog`, `/photo`, `/dev`. «Правка» brings all of it back. The mode switch is the only thing on the page that says the owner is signed in. |
| **B** | **Video in an article.** A paragraph holding nothing but a link to YouTube, RuTube or VK Video becomes a player. | The owner pastes a link on its own line, sees the player in the preview, publishes, and it plays. A visitor's page makes no request to the service until they click. |
| **C** | **The editor says how the markup works.** Picture size in particular — the vocabulary exists and nothing discoverable points at it. | Opening the cheat sheet in the editor answers "how do I make this picture wider" without leaving the page, and covers caption, video, table, quote, code and link too. |
| **D** | **The cabinet gets rooms.** A menu inside `/me`; **«События»** holds today's list, plus **«Сводка»** and **«Медиа»**. | The cabinet stops being one column of links. Adding the next administrative thing means adding a room, not another paragraph. |
| **E** | **«Снимки без описания» leaves the cabinet.** A missing description is not a problem to be worked through. | The cabinet no longer opens with 24 identical rows. The prompt survives in the album, in «Правка», where it is a hint in place rather than a task. |
| **F** | **Search matches a prefix.** «фотогр» finds «фотография». | Typing part of a word finds the thing, the way search elsewhere behaves. Nothing that is found today stops being found. |

### Out, with reasons

- **Owner-only hits on the search page are not hidden in «Просмотр».** The group heading counts
  what the query matched — «Показано 3 из 5». Hiding two rows with CSS leaves the heading claiming
  five above three, which is a worse lie than the leak it fixes, and correcting the count means the
  route running two queries per group and the mode reaching the server. Recorded as **ADR-033**.
- **Self-hosted video files.** The owner chose the service-link form. Accepting `mp4` through the
  uploader means a storage and bandwidth commitment with no transcoding behind it — a clip off a
  phone is comfortably 100 MB — and a second player to keep accessible. **ADR-035** records the
  choice and what it would take to add the other half later.
- **Trigram search (`pg_trgm`).** Prefix matching is what "partial match" ordinarily means, and it
  needs no extension, no migration and no second ranking mechanism to reconcile with `ts_rank`.
  **ADR-034**.
- **Deleting orphaned media from the cabinet.** The `/me/media` room reports; `--prune` stays a
  command run deliberately on the server. **ADR-037**.

### Budget

One milestone, five tasks. **A is a shared-primitive change and lands first, alone.**

### Non-negotiables

1. **A visitor's HTML is unchanged.** No owner markup, no `admin.css`, no `edits.js`, and no
   `owner-only` class anywhere in it. `F36` and `test_anonymous_html_contains_no_admin_markup`
   remain the guard.
2. **The CSP stays strict.** `frame-src` gains an explicit list of hosts and nothing else moves — no
   `unsafe-inline`, no wildcard, no `img-src` for a third party.
3. **Raw HTML stays off at the parser, and `iframe` never enters `ALLOWED_TAGS`.** The player is
   built by script at click time from a value the renderer closed, exactly as `WIDTH_WORDS` closes
   the class attribute today.
4. **Every mutating route keeps its `CurrentAdmin`**, and nothing joins `test_authz_sweep.py`'s
   allow-list. This iteration adds reads.
5. **No migration and no new model.** Every number the cabinet shows is a query over what is there.
6. **F-002 holds**: an action leaves the caret on a control, for every new control here.

## Impact map

| | Change | Touched | SPEC | Tests that cover today's behaviour | Blast radius | What proves no regression |
|---|---|---|---|---|---|---|
| **A** | «Просмотр» = the visitor's page | `static/css/admin.css`, `components.css:748-788`, `photo.css:340-346,451-529`, `blog.css`, `dev.css`, and the conditional blocks in `base.html`, `partials/nav.html`, `partials/site_links.html`, `partials/editable.html`, `partials/empty_state.html`, `blog/index.html`, `blog/post.html`, `blog/_new_button.html`, `blog/_post_card.html`, `photo/index.html`, `photo/album.html`, `photo/_board.html`, `photo/_album_card.html`, `photo/_album_head.html`, `photo/_grid.html`, `photo/_photo_tile.html`, `photo/_uploader.html`, `dev/index.html`, `dev/_board.html`, `dev/_project_card.html` | **F55** acceptance extended | `e2e/test_show_edits.py`, `test_home_editing.py`, `test_site_links.py`, `test_album_upload.py`, `test_article_publish.py`, `test_upload_guard.py`, `test_editor_guard.py`, `test_admin_keyboard.py`, `test_a11y.py`, `tests/api/test_authz_sweep.py:118-122` | **Shared primitive** — one rule, twenty-odd templates | In «Просмотр» the owner's `/`, `/blog`, `/photo`, `/photo/<album>` and `/dev` render the same set of rendered boxes a visitor's do; the visitor guard still passes on all four |
| **B** | Video in an article | `services/markdown.py` (renderer, `ALLOWED_TAGS`, `ALLOWED_ATTRIBUTES`), `app/main.py` CSP, `static/css/prose.css`, `static/js/` (new), `blog/post.html` / `dev/detail.html` script hook, `i18n/ru/prose.json` or `blog.json`, `tests/unit/test_markdown.py` | **F63** new | `tests/unit/test_markdown.py` (sanitiser allow-list assertions), `tests/api/test_pages.py` CSP header assertion | **Contained but security-adjacent** — the sanitiser and the CSP are both in it | A page with no video makes no third-party request and carries no `iframe`; a page with one carries none either until the play control is pressed; every existing markdown test passes unchanged |
| **C** | Markup cheat sheet | `blog/editor.html`, `static/css/blog.css`, `static/js/editor.js`, `i18n/ru/blog.json` | **F38** acceptance extended | `e2e/test_article_publish.py`, `e2e/test_a11y.py` (the editor is an admin surface) | **Additive** — one disclosure and two toolbar buttons | The sweeps pass over the editor with the sheet open and closed; the two new buttons insert what they claim |
| **D** | The cabinet gets rooms | `app/routers/me.py`, `app/templates/pages/me*.html`, `partials/cabinet_group.html`, `static/css/me.css`, `i18n/ru/me.json`, `app/routers/seo.py`, `e2e/conftest.py:224-239`, `tests/api/test_me.py`, `e2e/test_me.py` | **F62** acceptance extended, **F64** new | `tests/api/test_me.py` (all), `e2e/test_me.py` (all), `e2e/test_a11y.py` admin sweeps | **Additive** — two new read-only routes | Each room answers 404 anonymous and 200 signed-in; `Disallow` covers all three; both sweeps run over all three in both themes |
| **E** | Undescribed leaves the cabinet | `app/routers/me.py`, `i18n/ru/me.json`, `tests/api/test_me.py`, `e2e/test_me.py` | **F62** acceptance edited | `tests/api/test_me.py`, `e2e/test_me.py` — both assert the group is there | **Isolated**, but it is a deletion of promised behaviour | The album's own prompt (`photo-item--undescribed`, the count line) still renders in «Правка» |
| **F** | Prefix search | `services/search.py`, `tests/api/test_search_seo.py` | **F65** new | `tests/api/test_search_seo.py`, `e2e/test_search.py` | **Contained** — one function, no schema | Every existing search assertion passes **unchanged**: the prefix query is unioned into the existing one, never substituted for it |

### Ordering

**A lands first and alone.** It introduces the marker every other owner-only block will be written
against and it edits twenty templates; anything landing beside it would collide in the same files.
F is independent of everything and may land at any point. B lands before C, because C documents
what B builds. D and E are one task and are independent of A, B and C.

### Tests whose expectations change

Each of these asserts today's behaviour correctly. Changing one is a behaviour change, and every one
below is covered by an ADR taken in the same breath as the feature.

| Test | Asserts today | After | ADR |
|---|---|---|---|
| `tests/api/test_authz_sweep.py:118-122` | the marker list a visitor's HTML must not contain | the list **gains** `owner-only`; it only ever grows | ADR-032 |
| `e2e/` — every flow that clicks an owner control | reaches the control from whatever mode the fixture left | enters «Правка» first, through the existing `switch_mode` helper | ADR-032 |
| `tests/api/test_me.py`, `e2e/test_me.py` | the cabinet lists photographs with no description | it does not; the prompt lives in the album, in «Правка» | ADR-036 |

**Expect this map to undercount, as the last two did.** T131 owed four tests the map did not name and
T132 owed seven, in three files it never mentioned. Every one of them was a flow that clicked an
affordance which happened to be reachable. Task A widens the set of hidden things from three
selector families to every owner-only block on five pages, so before starting it, grep `e2e/` for
locators naming an owner control — `.upload-zone`, `photo-actions`, `status-chip`, `album-card__admin`,
`project__admin`, `article__admin`, `drafts`, `_new_button` — not only the files listed above.

**And remember the catalogue.** `translate()` is `@lru_cache`d per process: a new i18n key needs
`docker compose restart web`, or it renders as its own dotted name and every role-based selector
misses it. This iteration adds keys in five catalogues.

## Exit criteria

1. Baseline suites at their baseline counts or better: unit/API ≥ 289, e2e ≥ 92, both exit 0.
2. `ruff check` and `ruff format --check` both exit 0 over the whole tree.
3. Each of A–F has at least one check that fails without the change, watched failing first.
4. In «Просмотр», the signed-in owner's `/`, `/blog`, `/photo`, `/photo/<album>` and `/dev` present
   the same interactive controls a visitor's do — measured as **rendered boxes**
   (`getClientRects().length`), never as computed `opacity`, and never as a count of DOM nodes.
5. The visitor guard still sweeps `/`, `/dev`, `/photo`, `/blog` and finds no owner markup, no
   `admin.css`, no `edits.js` and no `owner-only`.
6. A published article containing a video makes **no request to the video host** until the play
   control is pressed, and the page's HTML contains no `iframe`.
7. Both accessibility sweeps run over all three cabinet rooms as well as the existing signed-in
   screens, in both themes, and pass.
8. **The owner writes one article containing a picture at a chosen width and a video, using only the
   editor's own cheat sheet, publishes it, and reads it in both modes.** No test stands in for this.

## T135 landed — and eight things the plan did not say

Done 2026-08-17. One rule in `admin.css` — `:root:not(.show-edits) .owner-only { display: none }` —
and the marker on every owner-only block across eighteen templates. The three families I4 gated lost
their `display: none` default and their `:root.show-edits` override, so one mechanism decides
visibility. Suites afterwards: **289 unit/API** exit 0, **97 e2e** exit 0 (92 before, `+5` for the
new parity file), `ruff check` clean, `ruff format --check` 119 files exit 0.

1. **`show-edits` survives in three CSS rules, not the two the task predicted.** The third is
   `.photo-item--undescribed`, and it has to be: the class is a *modifier on the tile*, so putting
   `owner-only` on it would take the photograph away with the rim. It stayed keyed off the mode,
   exactly like the `.editable` outline — both are hints drawn on a block that is present in either
   mode, so there is nothing for a `display: none` rule to remove. The honest statement is narrower
   than the DoD's: **one mechanism decides visibility, and two decorations read the mode.** Nothing
   is weakened by the difference, and inventing a child element to carry the marker would have added
   a DOM node to avoid a comment.

2. **The impact map named nine `e2e/` files. The suite broke in five — and one of them was not on
   the list.** `e2e/test_login.py` was missed by the grep the task prescribed, because it reaches the
   control by accessible name and not by class. That is the third iteration running where the
   undercount was a role-based selector; the grep list catches classes and misses `get_by_role`.

3. **That missed test asserted the leak.** `test_login_reveals_admin_and_logout_takes_it_away` ended
   with `expect(get_by_role("button", name="Новый альбом")).to_be_visible()` immediately after the
   login — which is precisely what F55 says must not happen. It was made **stricter**, not relaxed:
   the control is asserted *hidden* on the page the login lands on, then «Правка» is asked for, then
   it is asserted visible. Signing in reveals the menu; the mode reveals the affordances.

4. **One test could not use `switch_mode`, because the helper clicks.**
   `test_an_article_can_be_written_and_published_without_a_mouse` claims a full publishing flow
   without a mouse. Calling the sanctioned helper there would have quietly falsified the docstring,
   so the mode is entered from the keyboard — Tab to the menu button, Enter, Tab to «Правка», Enter,
   Escape — and the caret lands back on the button that opened the menu, which is what F-002 already
   guaranteed and what the rest of the flow tabs on from.

5. **Three unit tests broke on a string, in three files the map never mentioned.**
   `tests/api/test_blog.py`, `test_photo.py` and `test_projects.py` each assert the literal
   `class="status-chip"`, and the attribute grew by one class. Fixed by asserting the attribute whole
   — `class="status-chip owner-only"` — rather than loosening it to a substring: the assertion exists
   to prove the *shared* chip renders (UI-AUDIT F-010), and a substring match would pass on a
   mention of the word anywhere in the document.

6. **A dead block from T132 was still in `photo.css`.** `@media (hover: none)` set `opacity: 1` on a
   scrim that `display: none` had already removed, and repeated a `pointer-events` line. T132's DoD
   said the families lose their touch branch; this one outlived it and said nothing on any device.
   Deleted here because it sat on the very selector whose mode mechanism was being consolidated.

7. **Watched failing first, the parity check fails at its own guard rather than on a box diff.** On
   the pre-change tree `.owner-only` does not exist, so the guard that stops the test passing
   vacuously — "«/» carries no owner-only block at all" — fires before the comparison it protects.
   The box-level evidence came from the three named-surface checks, which failed with
   «`#upload-zone` still has a box in «Просмотр»», «`.photo-actions` …» and «`.board-actions` …».
   Four of the five new checks were red; the fifth, `.photo-item__admin`, was already green, because
   that is the one family I4 had gated.

8. **The empty state still says a different sentence in the two modes, and that is deliberate.**
   `blog.empty_note_admin`, `photo.empty_admin_note` and `photo.grid_empty_admin_note` are chosen
   **server-side** from `is_admin`, and the mode never reaches the server — the same reasoning that
   put ADR-033 out of scope. The empty state's *action button* carries `owner-only`; its sentence
   does not. Exit criterion 4 measures boxes and the counts are identical, so the check passes; an
   owner comparing the two modes by eye will still read a different sentence there. Left as it is,
   named here rather than fixed quietly.

**One caveat inside the parity check itself.** `/photo` is bounded for a visitor and whole for the
owner (ADR-022), so above `PAGE_SIZE` published albums the two sides hold different content and the
diff reports album cards. The assertion message says so in as many words, because the failure would
otherwise read as a leak.

**No i18n key was added**, so the `docker compose restart web` this iteration's intake warns about
was not needed for the catalogue — only for the templates, twice, either side of stashing the change
to watch the new checks fail.

## T136 landed — and four notes on how

Done 2026-08-17. `_prefix_tsquery` turns the normalised query into `token:* & token:*`, and `group()`
unions it onto the whole-word half — `websearch_to_tsquery(...) || to_tsquery(...)` — so `ts_rank`
reads the same combined query and `_statement` is still written once for the hits and the count.
Suites afterwards: **306 unit/API** exit 0 (289 before, `+17` from the two parametrised guards),
`e2e/test_search.py` **7** exit 0 with every assertion unchanged, `ruff check` clean,
`ruff format --check` 119 files exit 0. No migration, no extension, no new index, and
`MIN_QUERY_LENGTH` is where it was.

1. **The strip list is two characters longer than the DoD's.** The task named `&|!()<>:*'`; the code
   also strips `\` and `"`. Neither is a `to_tsquery` operator, and that is the point — they are the
   two characters that can still unbalance the parse *after* `:*` is appended to a token, and the
   failure mode is `syntax error in tsquery` answering a 500 to an HTML page. Stripping rather than
   escaping is the same decision throughout: a search box holds a phrase somebody typed, never an
   expression.

2. **The red run only became honest on the third attempt.** The first was worthless — a module-level
   `from app.services.search import _prefix_tsquery` made the whole file fail *collection* with
   `ImportError` on the stashed tree, so nothing was proved about search. The second hit a collection
   error of its own: a test parametrised on `query` that did not accept the argument
   («function uses no argument 'query'»). The import now sits **inside** the two helper tests, so a
   tree without the change still collects the file and the red run reads as failed assertions. Worth
   keeping as a habit: watch-it-fail-first proves nothing when what fails is the import.

3. **What the red run actually showed.** With `app/services/search.py` stashed,
   `test_a_prefix_finds_the_word_it_begins` failed on its own assertion — «Плёночная фотография
   зимой» not in the response for «фотогр» — and the eight `_prefix_tsquery` parametrisations failed
   on the missing name. The two robustness guards **passed on the stashed tree**, correctly: they
   guard the new parser path against a 500 and there is no new path there to break yet.

4. **`test_a_usable_token_does_produce_a_prefix_half` exists to guard the other guard.** Seven
   parametrisations assert `_prefix_tsquery(...) is None`, and a helper that returned `None`
   unconditionally would satisfy all seven while quietly deleting the feature.

## T137 landed — and nine things the plan did not say

Done 2026-08-17. Three rooms with their own addresses — `/me` «События», `/me/stats` «Сводка»,
`/me/media` «Медиа» — sharing one layout and one menu that marks the room being read;
«Снимки без описания» is gone from the cabinet; the disk walk moved into `app/services/storage.py`,
which `scripts/media_orphans.py` now calls and «Медиа» calls on a press. Suites afterwards:
**320 unit/API** exit 0 (306 before, `+14`), **99 e2e** exit 0 (97 before, `+2`), `ruff check` clean,
`ruff format --check` 120 files exit 0. Accessibility sweeps over the two new surfaces: focus stops
189 → 205 with **0** without an indicator, target sizes under 44 px 157 → 171 with **0** under
WCAG 2.5.8's 24, contrast failures **0** in both themes.

1. **Two templates the DoD's path list did not name.** `pages/me_base.html` is the layout ADR-036
   asked for, as a *parent template* rather than an include: the three rooms `{% extends %}` it, so
   `noindex, nofollow` and the room menu are structural and a fourth room gets both by existing.
   Repeating the robots meta in three files would have made forgetting it a one-line mistake.
   `partials/orphan_scan.html` is the second: the answer behind «Проверить» has to be renderable on
   its own to be swapped into a region.

2. **`scan()` deliberately does not carry the empty directories, and that is a near-miss.** The
   script walks for those **after** `--prune`, so a directory the prune has just emptied is reported
   and removed in the same run. The first version folded the walk into `scan()`, which moved it
   *before* the deletion — a byte-identical report run and a quietly different `--prune`. The DoD's
   own check would not have caught it, because the diff it prescribes is a report run.

3. **The diff needed a planted orphan to mean anything.** Real storage had no orphans and no empty
   directories, so a plain before/after diff would have exercised neither branch that changed. Two
   files under `photos/zzz-t137-check/` and one empty directory were planted in the media volume, the
   diff was taken with them there — identical from `media root:` down, including the `ORPHAN` line,
   the shared-upload section and the empty-directory list — and they were removed afterwards. The
   `--prune` branch is still not covered by that diff; it is the one branch a report run cannot
   reach, and it is named here rather than implied to be verified.

4. **The move left a name behind, and the command found it.** `if not args.prune and (orphans or
   empty)` still referred to the local list the scan replaced, so the script printed its entire
   report and *then* died on `NameError`. Only running it showed that — the diff the DoD asks for is
   not paperwork.

5. **Two size formats, on purpose.** `scripts/media_orphans.py` keeps its own B/KB/MB/GB ladder,
   because its output had to stay identical to the byte; the page has `_megabytes` and one Russian
   unit with a decimal comma. Formatting at each edge, not a second answer about what is on disk —
   the number itself comes from the one `scan`.

6. **«События» and «Медиа» share the failed photographs, through one function.** A failed photograph
   is something waiting *and* something wrong with the pipeline, so both rooms want it;
   `_failed_group` means they cannot end up listing it differently or offering two different retries.

7. **Only articles carry a publication date.** An album and a project have `is_published` and nothing
   else, and the DoD forbids a new column — so the figure is «Последняя статья», named for what it
   actually measures, rather than «Последняя публикация» promising more than the schema knows.

8. **The guard that the undescribed prompt survived was already written.**
   `tests/api/test_photo.py::test_the_owner_is_told_how_many_photos_have_no_description` asserts the
   count line and `photo-item--undescribed` on the album page and passes unchanged, so the deletion
   is provably a *move*. `tests/api/test_me.py` now asserts the cabinet is silent about it and names
   that test rather than duplicating it against a hand-made photograph whose `thumb_path` is `None`.

9. **The red run was taken at the API level only.** With `app/` and `scripts/` stashed, twelve of the
   twenty-two checks in `tests/api/test_me.py` failed on their own assertions and ten passed — the
   ten being the four "no such address" cases, which a *missing* route also satisfies, and the
   «События» checks that were already true. The new e2e checks make the same claims through a
   browser, so they were not stashed a second time. T136's lesson was applied: the three tests that
   need `app.services.storage` import it **inside** their bodies, so a tree without the module still
   collects the file.

## T138 landed — and ten things the plan did not say

Done 2026-08-17. A paragraph holding nothing but a link to YouTube, RuTube or VK Video becomes
`<figure class="prose-video">` around a `<button>` carrying the embed URL; `app/static/js/video.js`
builds the `<iframe>` on a press and nothing else in the product ever does. `ALLOWED_TAGS` gained
`button`; `iframe` did not. The CSP gained one line — `frame-src` naming the three hosts — and no
other directive moved. Suites afterwards: **353 unit/API** exit 0 (320 before, `+33`), **103 e2e**
exit 0 (99 before, `+4`), `ruff check` clean, `ruff format --check` 121 files exit 0.

1. **My own test found a real defect: two video links in one paragraph were one player.** The
   recogniser accepted a paragraph whose *first* token was a `link_open` and whose *last* was a
   `link_close` — which is also true of «link link», where the two belong to different links.
   Everything between them, including the first link's close and the second's open, was treated as
   the inside of one link. Fixed by requiring that no link boundary appears in between, which is the
   same "a figure is a paragraph, not a mention" rule pictures already follow.

2. **The CSP assertion the DoD names is not where the DoD says.** `tests/api/test_pages.py` is the
   footer-links file and holds no header assertion; the policy is asserted in
   `tests/api/test_authz_sweep.py`, which only checked that the header *exists*. That is what was
   extended, and it now reads the policy **directive by directive** — `img-src` still `'self' data:`,
   no `unsafe-inline`, no wildcard anywhere, `frame-src` exactly the three hosts — so widening one is
   a failing test rather than a detail nobody looks at.

3. **`autoplay=1` is part of the embed URL the renderer builds.** Without it a reader presses play
   twice: once on the facade, once in the player that replaces it. It is inside the URL rather than
   appended by the script, so the value in `data-video` stays something this module composed from an
   anchored pattern.

4. **The author's own link text becomes the caption.** `[Разбор съёмки](https://youtu.be/…)` alone in
   a paragraph is a facade *and* a `<figcaption>`; a linkified bare address is a facade with no
   caption, because its "link text" is the URL. The DoD did not ask for this, and the alternative was
   swallowing words the author typed.

5. **A poster from anywhere but our own media makes the paragraph an ordinary link.** ADR-035 leaves
   `img-src 'self' data:` alone, so a foreign poster could not load anyway; rather than render a
   facade with a hole in it, the link stays the link the author wrote.

6. **`video.js` is loaded in the editor too, which the DoD's path list did not include.** The preview
   goes through the same `render_markdown`, so it already showed the same facade — and a facade that
   did nothing on a press would have been the one thing in the preview that does not behave like the
   published page (F28). Two lines in `blog/editor.html`, with an e2e check that the preview's
   control builds a player.

7. **`span` gained `aria-hidden` in the sanitiser's attribute allow-list.** The play triangle is a
   decorative character, and the control's name is the label beside it. Authors cannot produce a
   `span` at all — raw HTML is off at the parser and `attrs_plugin` reaches images only — so the
   addition is reachable from the renderer and from nowhere else. The triangle is *text* rather than a
   CSS shape on purpose: a shape disappears under `forced-colors`.

8. **One test assertion had to be narrowed, and it was the test that was wrong.** The poster-caption
   check asserted `"title=" not in html`, which the picture tests can afford; the button legitimately
   carries `data-title`, the frame's accessible name. It now asserts that the *caption text* is not
   also a tooltip.

9. **The accessibility evidence needed a page that carries a facade, so the sweeps got one.** A new
   `published_video_post` fixture joins the anonymous contrast sweep (both themes), the anonymous
   focus sweep and the 360 px target-size sweep, and a new `forced-colors` test asserts the glyph's
   disc and the label's plate keep a border when their backgrounds are repainted. Results: contrast
   **85 samples, 0 failures, 0 unmeasurable** in both themes, with the facade measured and *not* among
   the twelve worst (the worst on the whole site is 4.65:1); the play control appears in
   `focus-sweep.json` as a stop with its own indicator; it is full-width, so it is not in the
   under-44 px list at all.

10. **A known wart, named rather than fixed.** `excerpt_from` strips tags and keeps text, so an
    article that *opens* with a video and leaves its excerpt empty gets «▶Смотреть видео» at the front
    of its meta description. Before T138 the same article got the raw URL there, so this is not a
    regression — but it is not right either, and it belongs in the next intake rather than in a task
    whose DoD says nothing about excerpts.
