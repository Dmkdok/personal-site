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
