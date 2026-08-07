# Product Spec

Source: `docs/BRIEF.md` (2026-08-04). Language of the product UI: Russian. Language of this document: English.

## Summary

A personal website for one person with three distinct professional/creative identities — developer, photographer, blogger — presented as one coherent site rather than three scattered social profiles. Four sections: **Главная / Разработка / Фото / Блог**.

The defining product constraint is **editing in place**: the owner logs in on the public site and edits the very page he is looking at. There is no separate admin area to navigate. Uploading an album, writing an article and adding a project card are all done from the section they belong to.

Visual direction: rounded "pill" navigation bar at the top containing the site-wide search, expressive typography, deliberately clean cards (no tags, no reading time, no counters), dark-grey and light themes, restrained motion. No 3D, no WebGL.

## Users & scenarios

### Primary — prospective client

Arrives from a link. Wants, within ~30 seconds, to answer: *what does this person do, is the work good, how do I reach him.*
Needs: fast-loading photo galleries, credible project descriptions, obvious contact links.

### Secondary — social media follower

Arrives from VK / Telegram / YouTube. Wants the owner's writing in one place instead of three feeds.
Needs: readable article pages, easy return to the blog index.

### Secondary — the owner (admin)

Publishes from a browser, possibly on a laptop after a shoot. Wants to drag 40 photos into an album and have it just work, and to write an article in Markdown while seeing the result.
Needs: no code, no file management, no fragile admin UI, clear feedback on long uploads.

## User flows

### Public

1. **Landing** — visitor opens `/` → intro block (who the owner is, what he does), social/contact links, three large entries into Разработка / Фото / Блог. Navigation pill is present on every page.
2. **Photography** — `/photo` → list of album cards (cover image + title + caption) → click → `/photo/{slug}` → responsive grid of photos → click a photo → lightbox opens: photo enlarged, background dimmed and edges softened, arrows / ←→ keys move between photos, `Esc` or click outside closes, focus returns to the originating thumbnail.
3. **Development** — `/dev` → list of project cards (title, short description, tech stack, links) → links open the repository or demo in a new tab. Optional detail page `/dev/{slug}` when the project has a long description.
4. **Blog** — `/blog` → list of article cards (cover, title, excerpt, date — no tags, no reading time) → `/blog/{slug}` → article rendered from Markdown with typographic care.
5. **Search** — visitor types in the field inside the navigation pill → results page `/search?q=…` groups matches under Статьи / Проекты / Альбомы, each result linking to its page. Empty query and no-results states are explicit.
6. **Theme** — visitor toggles light/dark in the navigation pill. Choice persists across visits; first visit follows the OS preference. No flash of the wrong theme on load.

### Admin

7. **Login** — owner opens `/login` (not linked from public navigation) → username + password → on success an admin bar appears fixed to the viewport and edit affordances become visible on public pages. Session persists for 30 days unless logged out.
8. **Create an album and upload photos** — on `/photo` while logged in → «Новый альбом» → title + caption → album page opens → drag a batch of files onto the drop zone (or pick via file dialog) → each photo shows an upload/processing state → thumbnails appear as they become ready → owner reorders by drag, sets the cover, edits alt text, deletes unwanted shots → «Опубликовать» makes the album visible to visitors.
9. **Write an article** — on `/blog` while logged in → «Новая статья» → editor screen with Markdown on the left and live preview on the right → image dropped into the editor uploads and inserts Markdown at the cursor → saved as a draft automatically → «Опубликовать» sets the publication date and makes it public.
10. **Add a project** — on `/dev` while logged in → «Добавить проект» → inline card form: title, short description, optional long description in Markdown, repository URL, demo URL, tech stack, optional cover → save → card appears in the list; drag to reorder.
11. **Edit intro copy** — on `/` while logged in → editable text blocks show an edit affordance on hover → click → inline editor → save → page updates in place.

## Functional requirements

### Public site

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F1 | Four-section navigation in a rounded pill bar, fixed on scroll, containing section links, the search field and the theme toggle | Given any page, when it renders, then the pill shows Главная / Разработка / Фото / Блог with the current section marked (`aria-current="page"`), plus search and theme controls; it stays reachable while scrolling and collapses to a compact mobile form below 768 px |
| F2 | Home page shows intro copy, contact/social links and three section entries — nothing aggregated | Given `/`, when it renders, then the intro text, links to GitHub/VK/Telegram/YouTube and three navigational blocks are present, and no post/album/project feed is shown |
| F3 | Album index lists published albums with cover, title and caption | Given `/photo`, when albums exist, then each published album renders one card with cover image, title and caption, ordered by the admin's ordering; unpublished albums are absent |
| F4 | Album page shows a photo grid | Given `/photo/{slug}`, when the album is published, then its ready photos render in a responsive grid in the admin's order, lazy-loaded, with intrinsic width/height set so layout does not shift |
| F5 | Lightbox | Given the album grid, when a photo is clicked, then an overlay opens showing the larger derivative with the background dimmed and edges softened; ←/→ and on-screen arrows navigate, `Esc` and clicking the backdrop close it, focus is trapped while open and returns to the triggering thumbnail on close, and body scroll is locked |
| F6 | Project list rendered from manually created cards | Given `/dev`, when published projects exist, then each renders as a card with title, short description, tech stack and its links; external links carry `target="_blank" rel="noopener noreferrer"` |
| F7 | Project detail page for projects with a long description | Given a project with a long description, when `/dev/{slug}` is opened, then the rendered Markdown description is shown; projects without one link straight to their repository instead |
| F8 | Blog index lists published articles | Given `/blog`, when published articles exist, then each renders a card with cover (if set), title, excerpt and publication date, newest first, with no tags, reading time or view count anywhere |
| F9 | Article page renders sanitised Markdown | Given `/blog/{slug}` for a published article, when it renders, then headings, lists, quotes, links, code and images appear with readable measure (≈65–75 characters) and images are responsive; drafts return 404 to anonymous visitors |
| F10 | Site-wide search across articles, projects and albums | Given a query of 2+ characters submitted from the pill, when `/search?q=…` renders, then matches from all three content types appear grouped under labelled headings, ranked by relevance; a query with no matches renders an explicit empty state; an empty query renders guidance rather than an error |
| F11 | Light and dark themes | Given a first visit, when the page loads, then the theme follows `prefers-color-scheme`; when the visitor toggles it, then the choice is stored and applied on subsequent visits before first paint (no flash); both themes meet WCAG 2.2 AA contrast and the dark theme uses dark grey, never pure black |
| F12 | Responsive layout | Given viewports of 360, 768, 1024 and 1440 px, when any page renders, then content is legible without horizontal scrolling and interactive targets satisfy WCAG 2.2 AA 2.5.8 (24×24 px, with the inline and spacing exceptions). *Amended 2026-08-07 from a flat 44×44 px — see ADR-010.* |
| F13 | SEO basics | Given any public page, when it renders, then it has a unique `<title>`, meta description, canonical URL and Open Graph tags with an image; `/sitemap.xml` lists all published pages and `/robots.txt` exists |
| F14 | Error pages | Given an unknown URL or a server error, when it is served, then a styled 404 / 500 page renders inside the site layout with a route back to the home page |

### Admin — authentication

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F15 | Single admin account seeded from environment | Given a fresh database and `ADMIN_USERNAME` / `ADMIN_PASSWORD` set, when the app starts, then exactly one admin user exists with an Argon2id password hash; the plaintext password is never written to the database or logs |
| F16 | Session login | Given valid credentials at `/login`, when submitted, then a signed `HttpOnly`, `SameSite=Lax` session cookie is issued (30-day lifetime, `Secure` when served over HTTPS) and the visitor is redirected to the page they came from |
| F17 | Brute-force resistance | Given 5 failed login attempts from one IP within 15 minutes, when a 6th is made, then it is rejected with a generic message and a `429`, and the response for wrong username vs wrong password is indistinguishable |
| F18 | Authorisation on every mutating endpoint | Given no valid session, when any create/update/delete/upload endpoint is called, then it returns 401/403 and changes nothing — verified for every such endpoint by test |
| F19 | CSRF protection | Given a state-changing request without a valid CSRF token, when it is processed, then it is rejected with 403 |
| F20 | Logout | Given a logged-in admin, when logout is used, then the session is invalidated server-side and admin affordances disappear |

### Admin — photography

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F21 | Album CRUD in place on the photo pages | Given a logged-in admin on `/photo`, when «Новый альбом» is used, then an album is created with a unique slug derived from the title, and its title, caption, cover, order and published state can be edited from the album page itself without navigating to a separate admin area |
| F22 | Batch upload by drag-and-drop | Given an album page, when up to 50 image files are dropped at once, then each is uploaded and processed, per-file progress and state (загружается / обрабатывается / готово / ошибка) are visible, and successes are unaffected by individual failures |
| F23 | Derivative generation | Given an accepted upload, when processing completes, then the original is stored unmodified on the media volume and WebP derivatives at 640 / 1600 / 2560 px width are generated with aspect ratio preserved, orientation corrected from EXIF, and stored width/height recorded; images smaller than a target size are not upscaled |
| F24 | Upload validation | Given a file that is not a JPEG/PNG/WebP, exceeds 25 MB, or fails to decode, when it is uploaded, then it is rejected with a clear per-file message, nothing is written outside the media volume, and the stored filename is server-generated (never derived from client input) |
| F25 | Photo management | Given photos in an album, when the admin reorders by drag, sets a cover, edits alt text or deletes a photo, then the change persists and is reflected for visitors; deleting a photo removes its derivatives and its original from disk |
| F26 | Publish control | Given an unpublished album, when a visitor requests its URL, then it returns 404; when the admin publishes it, then it appears in `/photo` and in search |
| F27 | Processing resilience | Given the container restarts while photos are still processing, when it starts again, then photos left in a pending state are re-processed or clearly marked as failed with a retry action |

### Admin — blog

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F28 | Markdown editor with live preview | Given a logged-in admin creating or editing an article, when text is typed, then a preview pane renders the same Markdown pipeline used for the published page, updating within ~500 ms of a pause in typing |
| F29 | Image insertion into articles | Given the editor, when an image is dropped into it or chosen via a button, then it uploads, derivatives are generated, and Markdown referencing it is inserted at the cursor position |
| F30 | Draft and publish lifecycle | Given a new article, when it is saved, then it is stored as a draft invisible to anonymous visitors; when published, then `published_at` is set and it appears on `/blog` and in search; it can be returned to draft |
| F31 | Content safety | Given article Markdown containing raw HTML such as `<script>` or `onerror` attributes, when rendered, then the dangerous markup is sanitised away while ordinary formatting survives |
| F32 | Slug handling | Given a title, when an article is created, then a URL-safe slug is generated (Cyrillic transliterated); when it collides with an existing slug, then it is made unique automatically; changing the title of a published article does not silently break its existing URL |

### Admin — development

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F33 | Manual project cards | Given a logged-in admin on `/dev`, when «Добавить проект» is used, then a card can be created with title, short description, optional Markdown long description, repository URL, demo URL, tech stack and optional cover image, then edited or deleted in place |
| F34 | Project ordering and publishing | Given several projects, when the admin drags them into an order or toggles published state, then the public list reflects it |

### Admin — shared

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F35 | Editable site copy | Given a logged-in admin on the home page, when an editable text block is clicked, then it can be edited inline in Markdown and saved without a page reload, and the change is visible to visitors |
| F36 | Admin affordances hidden from visitors | Given an anonymous visitor, when any public page renders, then no edit control, admin bar or admin-only markup is present in the HTML |
| F37 | Save feedback and failure handling | Given any admin save, when it succeeds then a confirmation is shown; when it fails then the error is shown and the entered content is not lost |
| F38 | Image size control inside an article | Given an image inserted into an article, when the author appends a size from a fixed vocabulary to its Markdown, then the published page renders it at that width — column, wide or full — with a caption when one is given, responsive sources, and no arbitrary attribute or inline style reaching the HTML; the syntax is discoverable from the editor without reading documentation |
| F39 | Editable contact links and copyright | Given a logged-in admin, when a social link or the copyright name is changed from the site, then both the footer and the home-page contacts block reflect it without a code change; an emptied link disappears from both; only `http` and `https` URLs are accepted |
| F40 | Media grouped by the thing it belongs to | Given an album or an article, when its files are stored, then originals and derivatives live under a directory of their own inside a per-kind parent, on a volume that survives the application being rebuilt or removed, so that one album's files can be located, copied or restored without picking them out of everyone else's |

## Non-functional

**Performance**
- Album grid page with 50 photos: images lazy-loaded with `srcset`, intrinsic dimensions set, CLS ≈ 0.
- Target LCP under 2.5 s on a broadband connection; grid thumbnails ≤ ~120 KB each.
- Batch of 50 photos processes in the background without blocking the request or the UI.

**Security**
- Argon2id password hashing; session cookie signed, `HttpOnly`, `SameSite=Lax`, `Secure` under HTTPS.
- CSRF tokens on all state-changing forms and requests.
- Upload hardening: MIME and magic-byte validation, size cap, decode verification, server-generated filenames, no execution of anything under the media volume, path traversal impossible by construction.
- Login rate limiting; generic authentication error messages.
- Markdown output sanitised (allow-list).
- Security headers: `X-Content-Type-Options`, `Referrer-Policy`, frame denial, and a Content-Security-Policy that works without external hosts (all fonts, CSS and JS are self-hosted).
- Secrets only via environment variables; `.env` is git-ignored, `.env.example` is committed.

**Accessibility (WCAG 2.2 AA baseline)**
- Full keyboard operation of navigation, search, lightbox and every admin control.
- Focus visible everywhere; focus trapped in the lightbox and returned on close.
- Contrast ≥ 4.5:1 for body text in both themes.
- `alt` text on photos, with the admin able to set it; decorative imagery marked as such.
- `prefers-reduced-motion` respected — animations reduced to opacity or removed.
- Semantic landmarks and a skip-to-content link.

**SEO**
- Server-rendered HTML for all public pages.
- Unique titles/descriptions, canonical URLs, Open Graph and Twitter card tags.
- `sitemap.xml`, `robots.txt`, semantic heading hierarchy, descriptive link text.

**Operations**
- Everything runs with one `docker compose up`.
- Media and database data live on host bind mounts so that `docker compose down -v` cannot destroy photographs.
- A documented backup command covering both the database and the media directory.

## Content / data model

| Entity | Key fields |
|--------|-----------|
| `admin_user` | `id`, `username`, `password_hash`, `created_at` — exactly one row |
| `album` | `id`, `slug` (unique), `title`, `caption`, `cover_photo_id`, `is_published`, `sort_order`, `lang` (default `ru`), `created_at`, `updated_at`, `search_vector` |
| `photo` | `id`, `album_id`, `original_path`, `thumb_path`, `medium_path`, `large_path`, `width`, `height`, `alt`, `sort_order`, `status` (`pending`/`processing`/`ready`/`failed`), `error`, `byte_size`, `created_at` |
| `post` | `id`, `slug` (unique), `title`, `excerpt`, `body_md`, `body_html`, `cover_path`, `status` (`draft`/`published`), `published_at`, `lang`, `created_at`, `updated_at`, `search_vector` |
| `project` | `id`, `slug` (unique), `title`, `summary`, `body_md`, `body_html`, `repo_url`, `demo_url`, `tech_stack`, `cover_path`, `is_published`, `sort_order`, `lang`, `created_at`, `updated_at`, `search_vector` |
| `site_content` | `key` (e.g. `home.intro`), `lang`, `value_md`, `value_html`, `updated_at` — inline-editable copy blocks |
| `login_attempt` | `ip`, `attempted_at`, `success` — for rate limiting |

Notes:
- `lang` exists from day one but is fixed to `ru` in v1; it is what makes the later English version additive rather than a rewrite.
- `search_vector` is a generated full-text column with a Russian text-search configuration, GIN-indexed, giving site-wide search without any external search engine.
- Media paths are stored relative to the media root so the volume can be moved.

## Integrations

None. The only external references are outbound links to GitHub, VK, Telegram and YouTube. Fonts, CSS and JavaScript are self-hosted; the site functions with no third-party network requests.

## Edge cases and error states

1. **Empty sections** — a section with no content shows a designed empty state (for the admin, one that invites creating the first item).
2. **Upload of a non-image / oversized / corrupt file** — rejected per file with a specific message; the rest of the batch continues.
3. **Disk full during upload** — upload fails cleanly, the photo is marked failed, no half-written derivative is served.
4. **Restart mid-processing** — pending photos are picked up again on startup (F27).
5. **Session expiry mid-edit** — the save attempt returns 401 and the UI prompts a re-login without discarding typed content.
6. **Slug collision** — resolved automatically with a numeric suffix (F32).
7. **Draft or unpublished item requested directly** — 404 for anonymous visitors, visible with a clear "черновик" marker for the admin.
8. **Very long article or very wide image** — content is constrained to the readable measure; wide media scrolls inside its own container, never the page.
9. **Search with 1 character, only spaces, or special characters** — guidance shown, no error, no SQL issues.
10. **JavaScript unavailable** — public browsing (navigation, albums, articles, search) still works; only the lightbox, drag-and-drop upload and live preview degrade.
11. **Album cover missing** — a neutral placeholder is used instead of a broken image.
12. **Deleting an album containing photos** — the admin is asked to confirm, and both database rows and files on disk are removed.

## Non-goals

Restated from the brief so they are testable as "must not be present": 3D/WebGL/scroll-driven animation; tags; reading time; view counters; comments; RSS; newsletter; contact form; analytics; GitHub API sync; English UI; multi-user accounts or public registration; a separate admin panel as the primary editing surface; pure black as the dark background.

## Risks & assumptions

1. **Inline editing raises the security stakes** — admin endpoints sit on the same surface as public pages, so authorisation must be verified endpoint by endpoint, not assumed. Mitigation: F18 is a mandatory test, not a code review item.
2. **Photo processing is the main performance risk** — 50 × 15 MB in one batch is real work. Mitigation: background processing with per-file feedback; if in-process background work proves insufficient, a worker process is the fallback (recorded in DECISIONS.md).
3. **Storage growth** — ~1500 photos plus three derivatives each is roughly 20–25 GB. Mitigation: bind mount to the host disk, documented in the handoff so the owner sizes the VPS accordingly.
4. **"Simple but very stylish" is subjective** — mitigation: the design system is built and shown first (M1), before feature work, so direction is corrected early rather than at the end.
5. **Russian full-text search quality** — Postgres stemming is good but not perfect for Russian. Accepted for v1; the alternative (an external search engine) contradicts the simplicity constraint.
6. **No CI and a single admin** — a bad manual edit has no review step. Mitigation: drafts for articles, publish toggles for albums and projects, and a documented backup command.
7. **Assumption:** the owner runs Docker Desktop on Windows for local review; the media bind mount must therefore work on a Windows host path as well as on Linux.
8. **Assumption:** originals are retained on disk but never exposed for download.

## Launch checklist

Status 2026-08-07. Two items remain open, both named explicitly below.

- [x] All requirements F1–F37 demonstrated as passing. *(137 unit/API tests plus 27 e2e; F12 as amended by ADR-010.)*
- [x] `docker compose up` on a clean checkout brings up the whole site; no manual steps beyond copying `.env.example`.
- [x] `pytest` suite green, including the F18 authorisation sweep and the upload pipeline tests. *(137 passed, exit 0.)*
- [x] Playwright flows green: login, album upload, article publish, lightbox, theme switch, search. *(`pytest e2e -m launch_flow` → 6 passed, exit 0.)*
- [x] No browser console errors or failed network requests on any page in either theme. *(Swept over `/`, `/dev`, `/photo`, `/blog`, `/search`, an album page.)*
- [x] Keyboard-only pass through navigation, search, lightbox and one full admin publishing flow.
- [x] Contrast checked in both themes; `prefers-reduced-motion` honoured. *(Light theme fixed — see ADR-010's neighbours in `docs/qa/contrast-*.json`; dark theme was clean throughout.)*
- [ ] **OPEN — The owner completes all three publishing flows unaided, without touching code.** Automated flows pass, but the owner has not sat down and done it. This is an acceptance step no test can stand in for.
- [x] Photos survive `docker compose down` followed by `up`. *(Host bind mount at `./data/media`; `make clean` drops only the database volume.)*
- [x] `docs/HANDOFF.md` written, including VPS deployment steps and the backup command.
- [x] A restore from `make backup` artefacts has been rehearsed. *(2026-08-07, `make restore-check`: a dump replayed into a scratch database, the media archive unpacked to a temporary directory, and every restored path checked against it — 13 rows, 44 files, nothing missing. T086.)*
