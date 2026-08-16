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
| F3 | Album index lists published albums with cover, title and caption | Given `/photo`, when albums exist, then each published album renders one card with cover image, title and caption, ordered by the admin's ordering; unpublished albums are absent; a visitor is shown a bounded page of them with a crawlable link to the rest, while the signed-in owner is shown all of them because the board is a drag-reorder surface over a global order. *Bounded for the visitor 2026-08-14 (I2/R-05) — see ADR-022.* |
| F4 | Album page shows a photo grid | Given `/photo/{slug}`, when the album is published, then its ready photos render in a responsive grid in the admin's order, lazy-loaded, with intrinsic width/height set so layout does not shift |
| F5 | Lightbox | Given the album grid, when a photo is clicked, then an overlay opens showing the larger derivative with the background dimmed and edges softened; ←/→ and on-screen arrows navigate, `Esc` and clicking the backdrop close it, focus is trapped while open and returns to the triggering thumbnail on close, and body scroll is locked |
| F6 | Project list rendered from manually created cards | Given `/dev`, when published projects exist, then each renders as a card with title, short description, tech stack and its links; external links carry `target="_blank" rel="noopener noreferrer"` |
| F7 | Project detail page for projects with a long description | Given a project with a long description, when `/dev/{slug}` is opened, then the rendered Markdown description is shown; projects without one link straight to their repository instead |
| F8 | Blog index lists published articles | Given `/blog`, when published articles exist, then each renders a card with cover (if set), title, excerpt and publication date, newest first, with no tags, reading time or view count anywhere; the page renders a bounded number of them and links to the rest. *Bounded 2026-08-14 (I2/R-05).* |
| F9 | Article page renders sanitised Markdown | Given `/blog/{slug}` for a published article, when it renders, then headings, lists, quotes, links, code and images appear with readable measure (≈65–75 characters) and images are responsive; drafts return 404 to anonymous visitors |
| F10 | Site-wide search across articles, projects and albums | Given a query of 2+ characters submitted from the pill, when `/search?q=…` renders, then matches from all three content types appear grouped under labelled headings, ranked by relevance; a query with no matches renders an explicit empty state; an empty query renders guidance rather than an error; each group states how many matches it has, and a group holding more than fits offers a way to reach the rest rather than truncating in silence. *Counts and continuation added 2026-08-14 (I2/F-014).* |
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
| F24 | Upload validation | Given a file that is not a JPEG/PNG/WebP/HEIC, exceeds 50 MB, or fails to decode, when it is uploaded, then it is rejected with a clear per-file message, nothing is written outside the media volume, and the stored filename is server-generated (never derived from client input); a file whose type or size the browser can already see will be refused is rejected **before any of its bytes are sent**, with its own reason on its own row, and the server-side check remains the authority. *Client-side gate added 2026-08-10 (I1/F-004); it is a second, earlier gate, never a replacement.* *HEIC/HEIF accepted 2026-08-14 (I2/R-10) — see F51.* |
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
| F36 | Admin affordances hidden from visitors | Given an anonymous visitor, when any public page renders, then no edit control, no owner menu and no admin-only markup is present in the HTML *(reworded by I4 — the admin bar it named was retired into the navigation capsule, ADR-027; the guarantee is unchanged)* |
| F37 | Save feedback and failure handling | Given any admin save, when it succeeds then a confirmation is shown; when it fails then the error is shown and the entered content is not lost |
| F38 | Image size control inside an article | Given an image inserted into an article, when the author appends a size from a fixed vocabulary to its Markdown, then the published page renders it at that width — column, wide or full — with a caption when one is given, responsive sources, and no arbitrary attribute or inline style reaching the HTML; the syntax is discoverable from the editor without reading documentation |
| F39 | Editable contact links and copyright | Given a logged-in admin, when a social link or the copyright name is changed from the site, then both the footer and the home-page contacts block reflect it without a code change; an emptied link disappears from both; only `http` and `https` URLs are accepted |
| F40 | Media grouped by the thing it belongs to | Given an album or an article, when its files are stored, then originals and derivatives live under a directory of their own inside a per-kind parent, on a volume that survives the application being rebuilt or removed, so that one album's files can be located, copied or restored without picking them out of everyone else's |

### M9 — media lifecycle, quality and identity

Added 2026-08-08 from the owner's second round of use. They span several areas,
so they are grouped by where they came from rather than split across the tables
above.

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F41 | Deleting something deletes its files | Given an album, an article, a project, a cover or a picture removed from an article's text, when the deletion is saved, then every file that belonged to it and is referenced by nothing else is gone from both `originals/` and `derived/` — every rendition, not a guessed subset — and any directory left empty by the removal is gone too; a file another page still uses is kept |
| F42 | The same picture is stored once | Given a picture uploaded a second time — the same frame used as an article's cover and again in its opening paragraph — when it is stored, then the bytes already on disk are reused, no second copy is written, and both places serve the same URL |
| F43 | Photographs published as photographs | Given a photograph in an album, when it is published, then the site can serve it at the full resolution it was uploaded at, at a quality where re-compression is not visible; given a picture inside an article, it is capped at 1920 px, where maximum quality buys nothing; an upload of up to 50 MB is accepted |
| F44 | The site is recognisable in a tab | Given any page, when it is open in a browser tab or saved to a home screen, then it shows the site's own «Dm» mark, legible against both light and dark browser chrome, served from this origin under the existing CSP |
| F45 | The whole copyright line is editable | Given a logged-in admin, when the copyright line in the footer is edited, then the entire line — symbol, year and name — is what is stored and shown; nothing about it is assembled in a template |
| F46 | The home page's own line is editable | Given a logged-in admin on the home page, when the line under the hero is clicked, then it edits in place like every other block and the change is visible to visitors |
| F47 | A cover is a cover, not the first picture | Given an article with a cover, when a visitor opens it, then the cover appears in the blog index card and as the Open Graph image but does not open the article's text |
| F48 | The repository explains itself | Given someone arriving at the repository on GitHub, when they read `README.md`, then they learn what the site is, what it is built from, how to run it, how to run the tests, how it deploys, and where the rest of the documentation lives, with screenshots |

### I1 — UI audit, Phase A

Added 2026-08-10 from `docs/UI-AUDIT.md`. Both state something the product was
already trying to do and did not finish; see ADR-016.

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F49 | An admin action always leaves the caret somewhere, and always answers | Given a logged-in admin operating a board or a grid from the keyboard, when a control is pressed — including a move that cannot happen, such as ↑ on the first item or ★ on the photo that is already the cover — then the action reports its outcome in a message, and focus is on a control adjacent to the action taken, never on `<body>` |
| F50 | Unsaved article text cannot be lost silently | Given the article editor with text typed since the last successful save, when the tab is closed or navigated away from, then the browser's own confirmation is raised; and when an autosave fails, then the save-state region shows a distinct failed state that persists until the next successful save rather than a message that removes itself |

### I2 — pagination, HEIC intake, UI audit Phase B

Added 2026-08-14 from `docs/ROADMAP.md` (R-05, R-10, R-12) and the P2 backlog of
`docs/UI-AUDIT.md`. Intake, impact map and exit criteria:
`docs/iterations/I2-pagination-media-phaseb.md`.

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F51 | A photograph off an iPhone can be published without being converted first | Given a HEIC or HEIF file within the size limit, when it is uploaded to an album, an article or a cover, then it is accepted, decoded with orientation corrected from EXIF, and the same WebP rendition ladder is produced as for a JPEG — nothing downstream of intake learns a new format; a file whose bytes are not a real image of an accepted type is still refused, and the browser-side gate offers HEIC in its file dialog |
| F52 | A long index does not render itself entirely | Given more published articles than one page holds, when `/blog` is opened, then a bounded number render with a link to the next page whose URL can be shared and crawled; every published article appears on exactly one page; the same holds for `/photo` as a visitor sees it; an out-of-range page is an honest empty page or a redirect, never a 500 |
| F53 | An error message can be read, and read again | Given an admin action that fails, when its message is shown, then it is announced assertively, stays until it is dismissed or replaced rather than removing itself on a timer, carries its own close control, and renders above the lightbox; a success message keeps its brief self-removing behaviour |
| F54 | A rejected form says which field is wrong | Given a form rejected on a field other than the first, when it re-renders, then that field carries `aria-invalid="true"` and is described by its own message, and the caret lands on it rather than on the top of the form |
| F55 | The owner can see everything he can edit | Given a signed-in owner, when he switches to «Правка», then every editable region on the page shows its control at once and keeps showing it, with no pointer anywhere; when he switches to «Просмотр», then no edit control is present at all, so the page he reads is the page a visitor reads; the choice survives a reload without a flash of the wrong state *(reformulated by I4 — the hover-reveal this originally sat on top of is gone, ADR-028)* |
| F56 | Interface state survives a high-contrast theme | Given Windows High Contrast (forced colours), when a thumbnail, a navigation link or an entry is hovered or focused, then its state is expressed by a property the mode preserves, so no control is left without a visible focus indicator |

### Added by iteration I3 — operations

Added 2026-08-15 from `docs/ROADMAP.md` (R-01, R-02, R-03). These are the first requirements in
this document that describe the site being *operated* rather than used. Intake, impact map and exit
criteria: `docs/iterations/I3-operations.md`.

**R-01 is deliberately taken in its smallest honest form** (ADR-023, ADR-024): while the site is in
test mode on the NAS, carrying throwaway photographs, the appliance's own snapshots are the backup
and this repository ships only the one command the appliance cannot supply. The engineered form —
a schedule owned by the repo, a retention policy, a self-describing set — waits for the move to a
dedicated server.

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F57 | A copy of everything can be taken, and put back | Given the deployed site, when the owner wants a restorable copy, then the appliance holds dated snapshots covering both the media dataset and the database dataset, taken on a schedule he did not have to remember; and a logical dump of the database plus an archive of the media is **one documented command on the server**, where the stack has no compose project to run it from |
| F58 | The owner can read the log without a terminal | Given a fault he wants to understand, when he opens the storage the site already writes to, then the application's log is a plain file under it, carrying the same lines the container prints — no `docker logs`, no shell on the appliance — and no secret, session token or password appears in it |
| F59 | The published image is one the suite passed | Given a push that would publish, when the unit/API suite or the lint gate fails, then no image is built and no tag moves; `latest` can only ever point at a commit whose gates were green |
| F60 | Logs cannot fill the disk | Given any service in either deployment, when it has been running and logging for a long time, then both the container's log driver and the application's own log file are bounded by an explicit maximum size and file count, so no volume of output can exhaust the volume that holds the photographs |

### Added by iteration I4 — the editing mode

Added 2026-08-16 from an owner request, not from an audit. Intake, impact map and exit criteria:
`docs/iterations/I4-editing-mode.md`. Both requirements below are visible only to the signed-in
owner; a visitor's page is unchanged, which F36 continues to guarantee.

**The cabinet is a summary, not an editing surface** (ADR-029). The non-goal at the end of this
document — "a separate admin panel as the primary editing surface" — stands: F62 answers *what
needs attention*, and every answer it gives is a link back to the page where the editing happens
in place.

| ID | Requirement | Acceptance |
|----|-------------|------------|
| F61 | The owner's controls live in one place, and that place covers nothing | Given a signed-in owner on any page, when it renders, then the mode indicator, the mode switch, the cabinet and «Выйти» are reachable from a single menu on the navigation capsule, no element is fixed over the content, and the document reserves no clearance it would not reserve for a visitor; «Выйти» takes a deliberate second action rather than sitting under the pointer |
| F62 | The owner can see what needs him without touring the site | Given a signed-in owner, when he opens the cabinet, then one page lists his drafts, his unpublished albums and projects, every photograph that failed to process — with the retry that already exists — and every photograph with no description, each linking to the page that edits it; the page is never indexed, and to anyone without a session the address does not exist |


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
- Focus is never dropped to `<body>` by an htmx swap: a control that acts leaves the caret on a control. *Added 2026-08-10 (I1/F-002).*
- The automated accessibility sweeps measure the signed-in surfaces, not only the anonymous ones. *Added 2026-08-10 (I1/F-001).*
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
- A documented backup command covering both the database and the media directory, runnable **where
  the site actually runs** and not only from a development checkout (F57). *Amended by I3: the
  command existed but could not execute on the deployment, because it reaches the database through
  a compose project the server does not have.*
- Dated snapshots of the media and database datasets, taken by the storage appliance on its own
  schedule (F57). *The repository does not own this schedule while the site is on the NAS —
  ADR-023.*
- The application's log readable as a file on the storage the site already writes to (F58), and
  bounded log output on every service in every deployment (F60).

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
6. **A single admin** — a bad manual edit has no review step. Mitigation: drafts for articles, publish toggles for albums and projects, and the appliance's dated snapshots to roll back to. *Amended by I3: this read "No CI and a single admin". CI now runs the suite and gates the published image (F59), so the unreviewed-change risk is narrower than it was — it is a content risk, not a code risk.*
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
