# Iteration I8 — Private articles reachable by a secret token link

- **Source:** owner request, made in chat (not an audit or bug) — friends need to read hidden
  articles (trip plans, personal links) without registering on the site
- **Opened:** 2026-08-29
- **Milestone:** `M20` in `docs/TASKS.md`
- **Baseline:** unit/API 371 passed, e2e 112 passed, lint clean, format 126 files, exit 0 — all at
  2026-08-28, branch `iteration/I8-token-shared-articles`, cut from `main` at `b2318f0`. See
  `docs/STATUS.md` → `## Baseline I8` for the full record.

## In scope

| Item | Why now |
|------|---------|
| `shared_article` entity, separate from `post` | The owner rejected folding this into the blog — a hidden article is not a draft and must never appear in `/blog`'s own listing, editing or publish lifecycle |
| Public read route `GET /s/{token}`, rendered through the existing Markdown/sanitiser pipeline | The only way a friend reaches the content; must not exist as a guessable or enumerable address |
| Invalid/missing token → 404, response identical either way | No leak of "a token like this exists but is wrong" vs "nothing here" |
| Excluded from `/sitemap.xml`, site search, public navigation; response carries `noindex` | A capability URL that ends up in a search index or a crawler's sitemap stops being secret |
| Cabinet section at `/me/shared`: list, create, edit, delete, copy-link, regenerate-token | The owner's only way to manage these articles; admin session required, same as every other cabinet room |
| Token route never accepts a mutating request | F18's structural authorisation sweep must keep proving this, not just this feature's own tests |

## Out of scope this round

| Item | Reason | Recorded as |
|------|--------|-------------|
| Multi-user accounts / per-person login for friends | Rejected as overbuilt for "a couple of friends look occasionally" — no current need for per-person revocation or view attribution | ADR-042 |
| Revoking one person's access without breaking the link for everyone else | A consequence of the bearer-token design, accepted deliberately, not a gap to close later in this round | ADR-042 |
| View auditing / access logs on shared links | Same reasoning as above — no current need, and it is additive later if it ever appears | ADR-042 |
| Editing a shared article via the token link itself | The token is read-only by construction; edit rights stay behind the single admin session (SPEC F15–F18) | ADR-042 |
| Rate limiting on `GET /s/{token}` | Token is `secrets.token_urlsafe(32)` — 256 bits; brute force is computationally infeasible regardless of a limiter. F17's limiter exists because login passwords are short; that reasoning does not transfer | ADR-043 |
| Image upload / inline media inside a shared article | Not requested — the draft brief describes text and links (a trip plan), not photos; `body_md`/`body_html` only, no `cover_path`, no upload endpoint | none — simply not built; add on a future request |

## Impact map

| Item | Touches | SPEC: changes / preserves | Existing coverage | Class | Regression proof |
|------|---------|---------------------------|-------------------|-------|-------------------|
| `SharedArticle` model + migration | New `app/models/shared_article.py` (`Base`, `TimestampMixin` — same pattern as `Post`); new Alembic revision creating `shared_article` (`id`, `title`, `body_md`, `body_html`, `share_token` unique+indexed, `created_at`, `updated_at`) | Adds F67; preserves the `post` table and every model referencing it — no existing table altered | None (new table) | Data | Migration runs clean on the current schema and reverses clean (`alembic upgrade head` / `alembic downgrade -1`), proven on the dev database, not a fixture; new unit test constructs one row and reads it back |
| Public read route `GET /s/{token}` | New `app/routers/shared.py` (GET handler only at this row); `app/templates/pages/shared_article.html` (new, modelled on `app/templates/blog/post.html` minus the draft banner and blog nav, `noindex` unconditional); reuses `render_markdown`/`ALLOWED_TAGS` from `app/services/markdown.py` unchanged | Adds F67 (renders), F69 (not indexed); preserves F9 (sanitised Markdown rendering — same pipeline, no new tags/attributes), F13 (SEO basics — sitemap listing untouched) | `tests/unit/test_markdown.py` covers `render_markdown`/`ALLOWED_TAGS` already and needs no change since neither is touched; no existing route-level coverage (new) | Contract (route + response shape) | New API test: valid token → 200 with rendered body and `<meta name="robots" content="noindex">`; missing token and a well-formed-but-wrong token → both 404, byte-identical response body, proven by diffing the two |
| `/sitemap.xml`, search, public nav stay silent on shared articles | Nothing touched — `app/routers/seo.py::sitemap` enumerates `Post`/`Project`/`Album` by explicit query, `app/routers/search.py`'s `GROUP_LABELS` names exactly those three groups; `shared_article` is absent from both by construction | Preserves F13, F10 | `e2e/test_seo.py` / equivalent sitemap test (if any) unaffected — no assertion needs to change | Local | New unit test: create a `shared_article` row, request `/sitemap.xml` and `/search?q=<its title>`, assert it appears in neither |
| Admin CRUD: create / save / delete / regenerate-token | `app/routers/shared.py` (POST handlers, same file as the GET route above — one task, not two, since both own the same path); `CurrentAdmin` dependency from `app/deps.py` (identical guard to every other mutating endpoint); `toast_headers`/`HX-Redirect` pattern from `app/routers/blog.py` | Adds F70, F71; preserves F18 (authorisation on every mutating endpoint), F19 (CSRF) | `tests/api/test_authz_sweep.py` is structural — it walks `app.routes` and fills `{id}` from `PARAM_SAMPLES["id"]`, already present — new routes named with an `id` path param are swept with **zero test-file changes**; confirmed by reading `_iter_api_routes`/`PARAM_SAMPLES` | Cross-cutting policy (auth boundary) | `test_authz_sweep.py` passes unmodified and its route count grows by the new endpoints (asserted via `test_there_are_mutating_routes`'s count, if it pins one); `secure-review` in Phase 6 covers this row regardless of size, per the impact-map's own rule for this class |
| Cabinet section: `/me/shared` list + editor, nav entry, copy-link | `app/templates/pages/me_shared.html` (new, modelled on `me_media.html`), `app/templates/pages/shared_editor.html` (new, modelled on `blog/editor.html` — full editor with live preview, reusing the same preview endpoint pattern as `blog.py::preview`), `app/templates/partials/cabinet_nav.html` (append one tuple `("shared", "/me/shared")` — additive, the three existing tuples are unchanged), `app/i18n/ru/me.json` (`me.room_shared`), new `app/i18n/ru/shared.json` | Adds F70; preserves F62/F64 (cabinet rooms — the existing three keep their own addresses and content) | `e2e/test_me.py::test_no_room_exists_for_a_visitor`, `::test_every_room_is_an_address_of_its_own` assert against explicit tuples that need one more entry each — additive, no existing assertion is removed or weakened; `e2e/conftest.py`'s admin-sweep page-list fixture (~line 260) needs `/me/shared` appended so the focus/contrast/target-size QA sweeps reach the new room | Shared primitive (`cabinet_nav.html` is included by every cabinet page) — bundled into this same task rather than split out, since nothing else in this milestone touches the partial and there is no real parallel-write conflict to guard against | `e2e/test_me.py`'s two tests above pass with the new tuple entries; a new e2e test drives the whole owner flow: create → copy-link → open the link anonymously → 200; regenerate → old token 404s, new token 200 |

## Ordering

1. **T146 (Data) lands first, alone, serially.** Nothing else in this milestone is buildable or
   testable without the table existing.
2. **T147 depends on T146** and is otherwise one task — the public route and the admin CRUD share
   `app/routers/shared.py`; splitting them would recreate the same-file conflict the ordering rule
   exists to avoid, the same reasoning M19 already used for a single-file feature.

## Expectations that change

None. Every touched existing test gains a new tuple entry, a new fixture-list line, or is left
untouched; no existing assertion is edited or weakened. (`tests/api/test_authz_sweep.py` needs no
edit at all — see the row above.)

## Exit criteria

- [x] A `shared_article` row survives a migration up and down, proven on the dev database
- [x] `GET /s/{a valid token}` renders the article through the same sanitised Markdown pipeline as a
      blog post, with `noindex` present unconditionally —
      `test_valid_token_renders_the_article_through_the_markdown_pipeline`,
      `test_shared_article_carries_noindex_unconditionally`
- [x] `GET /s/{missing or invalid token}` returns 404, identically for both cases —
      `test_missing_and_wrong_token_are_byte_identical_404s` (normalised for the per-request CSP
      nonce and the requested address itself, the only two things that legitimately vary)
- [x] The article is absent from `/sitemap.xml`, from `/search`, and from every public nav element —
      `test_shared_article_is_absent_from_the_sitemap_and_search`; `seo.py` and `search.py` untouched
- [x] `/me/shared` lists the owner's shared articles, gated by admin session; create, edit, delete,
      copy-link and regenerate-token all work from there — `tests/api/test_shared.py`'s F70 block,
      plus `e2e/test_me.py::test_a_shared_articles_link_survives_only_until_it_is_reissued` driving
      copy-link and delete through the real UI
- [x] Regenerating a token invalidates the old link immediately (old token 404s, new token 200) —
      `test_regenerating_invalidates_the_old_link_and_issues_a_working_new_one` (API) and the same
      e2e test above (browser clipboard round-trip)
- [x] No route under `/s/{token}` accepts a mutating request — proven by
      `tests/api/test_authz_sweep.py` with zero edits to that file
- [x] Baseline suites green at their Phase 0 counts or better — unit/API **394** exit 0 (374 at the
      T146 baseline), e2e **113** exit 0 (112 at Phase 0, +1 for the new create→copy→regenerate flow
      test), lint clean, format clean **130 files**
