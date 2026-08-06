# Brief

Date: 2026-08-04
Owner: Dmitriy Bogdanov (GitHub `Dmkdok`, Saint Petersburg) — Python backend developer, nature photographer, mountaineer.

## Pitch

A personal website that unifies three sides of one person — software development, photography, and a personal blog — into a single "corner of the internet" that the owner can edit directly on the live site, without touching code or a separate admin panel.

## Problem / JTBD

- The owner's audience and work are scattered across VK, Telegram, Instagram and YouTube. Cross-posting is manual and still leaves parts of the audience seeing only some of the content.
- There is no single link that can be sent to a prospective client ("here is who I am, here is my code, here are my photos").
- GitHub shows code but not photography; VK/Telegram show photos and posts but look like social feeds, not a professional portfolio.
- The owner does very different things; existing platforms force him to fragment that identity instead of presenting it as one coherent story.

## Primary user

**Prospective client** — someone considering hiring the owner as a photographer or as a developer. Arrives from a link in a message, a social profile or search. Needs to quickly judge quality of work and credibility, then find a way to make contact.

## Secondary users

- **Social media followers** (VK / Telegram / YouTube) — come for blog posts about travel and personal interests, want one place to follow instead of three.
- **The owner himself (admin)** — the single most demanding user: must be able to publish albums, articles and project cards from any browser, quickly and intuitively.

## Success (30 days)

- One link exists that the owner is comfortable sending to any client or follower, and he sends it.
- The owner publishes new content (album / article / project) without editing code or files, and without asking a developer for help.
- Photo, development and blog sections all contain real content, not placeholders.
- The site is the visible anchor of a personal brand that is expected to generate additional income later.

## In scope (v1)

Four sections (tabs), Russian language:

1. **Home** — intro (who he is, what he does), links to social profiles and contact details, navigation into the three sections. Nothing else: no aggregated feeds.
2. **Development** — a list of work / repositories. Cards are created and edited **fully manually** by the admin (title, description, links, tech stack, optional cover). No GitHub API integration.
3. **Photography** — a real photo portfolio: list of albums with captions → click an album → grid of photos → click a photo → lightbox with dimmed, softened background.
4. **Blog** — articles on non-professional topics (travel, personal interests), written in Markdown with a live preview.

Cross-cutting:

- **Inline admin editing.** When logged in as admin, editing happens on the public pages themselves — upload photos into an album, write an article, add a project card. No separate hard-to-use admin section.
- **Light and dark themes**, user-switchable, preference remembered.
- **Site-wide search** in the top navigation: one field that searches articles, projects and albums, with results grouped by section.
- Responsive: desktop and mobile.

## Out of scope (v1)

- 3D / WebGL / heavy scroll-driven animation (explicitly rejected).
- Tags, reading time, view counters, "featured" curation on the home page — deliberately omitted to keep cards and listings clean.
- Comments, RSS feed, newsletter.
- Contact form of any kind; contact is via published links only (no personal data collected → no 152-FZ consent flow needed).
- Analytics of any kind.
- English version of the site (structure must not block adding it later).
- GitHub auto-sync, payments, multi-user accounts, public registration.
- Production deployment to the VPS (planned as a separate step after the local version is approved).

## Constraints

- **Backend: Python** (owner's stated preference and his professional stack — Django / FastAPI).
- **Docker.** Everything runs via `docker compose`.
- **Media on the host disk.** Photo and file directories must be bind-mounted to an external volume on the hard drive so that container rebuilds cannot destroy them.
- **Local first.** Deliverable runs on `localhost` for review and approval. The owner already has a VPS and a domain; production rollout comes afterwards.
- **Language:** Russian UI and content now; data model and UI strings structured so English can be added later without a rewrite.
- **A11y:** WCAG 2.2 AA as the working baseline (keyboard-navigable lightbox and menu, visible focus, sufficient contrast in both themes, alt text on photos).
- **Complexity budget:** "polished, but balanced" — the owner explicitly does not want time sunk into elaborate micro-detail work.
- **Scale:** up to ~30 albums × up to 50 photos ≈ 1500 photos, camera JPEGs (~5–15 MB each), i.e. plan for ~20 GB of originals.

## Integrations

None. No analytics, no email/SMTP, no GitHub API, no CMS, no payment provider, no third-party fonts or CDNs (fonts self-hosted).

External links only: [github.com/Dmkdok](https://github.com/Dmkdok), [vk.ru/dmkdok](https://vk.ru/dmkdok), [t.me/dmkdok_blog](https://t.me/dmkdok_blog), [youtube.com/@dmkdok](https://www.youtube.com/@dmkdok).

## Brand & content

- **Tone:** simple but very stylish. Calm, confident, personal — not corporate, not "startup landing".
- **Visual references — liked:** [theodorusclarence.com](https://theodorusclarence.com/) for typography, clarity and overall feel; [TRIONN](https://www.awwwards.com/sites/trionn-2) for the rounded "pill" navigation block in a slightly different tone, its typography and its contrast.
- **Explicitly rejected:** the reference's cluttered cards (tags, reading time, metadata badges); pure black backgrounds — dark grey preferred; TRIONN's 3D particles, WebGL and sound-on-hover.
- **Design direction:** dark-grey and light themes, rounded pill navigation at the top with the search field moved into it, expressive typography, clean uncluttered cards, restrained motion only (fade-in, hover).
- **Copy source:** drafts written by the implementer; the owner edits them on the live site afterwards.
- **Imagery:** the owner's real photographs (nature / mountains), uploaded by him. Placeholder imagery only until then.
- **Photo handling:** no watermark, no EXIF display. Web-optimised derivatives are served to visitors; originals are kept on disk as the source of truth but are not offered for download.

## Quality bar

Balanced:

- `pytest` for API, upload pipeline and authorisation logic.
- Playwright for the key flows: admin login, uploading photos into an album, publishing an article, opening the lightbox, switching to the dark theme.
- No CI pipeline required for v1.

## Acceptance bar (owner's words)

> «Я приму результат, когда всё будет работать без ошибок и все требования из моей задачи будут выполнены.»

Operationalised in `SPEC.md` as a launch checklist: every requirement F1–Fn demonstrably passing, test suite green, no console errors, and the owner able to perform all three publishing flows unaided.

## Open questions

None blocking. Assumptions accepted by the owner:

1. Draft copy is written by the implementer and edited later by the owner on the live site.
2. Design: dark-grey + light themes, pill navigation with integrated search, expressive typography, clean cards without tags or reading time, light motion only, no 3D/WebGL.
3. Originals are stored on disk but not exposed as downloads (implied by "nothing extra needed").
