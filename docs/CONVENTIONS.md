# Conventions

Read this before writing code in this repository. Established in M0–M2 and
relied on by every feature module.

## Running things

| Task | Command (from the repo root) |
|------|------------------------------|
| Start the site | `docker compose up -d` → http://localhost:8000 |
| Logs | `docker compose logs -f web` |
| Tests | `docker compose run --rm tests` |
| Migration | `uv run alembic revision --autogenerate -m "…"` (host) |
| Lint | `uv run ruff check . && uv run ruff format .` |

`./app` and `./migrations` are bind-mounted into the container and Uvicorn runs
with `--reload`, so Python, template and CSS edits apply without a rebuild.
Rebuild only after changing dependencies.

**Do not run pytest on the Windows host** — Starlette's test client hangs there.
The `tests` compose service exists for this reason and is also what the VPS runs.

## Language

- Everything the user sees is **Russian**.
- Code, comments, commits and `docs/` are **English**.
- No user-visible string is hardcoded in a template. Add it to
  `app/i18n/ru/<area>.json` and read it with `t("area.key")`.
  One file per feature area — never edit another area's file.

## Rendering a page

Always use `app.templating.render`, never `templates.TemplateResponse` directly.
It injects `is_admin`, the CSRF token and the shared globals, so a route cannot
accidentally ship a page without them.

```python
from app.deps import OptionalAdmin
from app.templating import render


@router.get("/blog", response_class=HTMLResponse)
def index(request: Request, db: DbSession, admin: OptionalAdmin) -> HTMLResponse:
    return render(
        request, "blog/index.html", {"active_section": "blog", "posts": posts}, admin=admin
    )
```

`active_section` is one of `home` / `dev` / `photo` / `blog` and drives the
navigation's current-page state.

## Authorisation

- Public read: `admin: OptionalAdmin` — `None` for visitors, used to reveal editing UI.
- Anything that changes state: `admin: CurrentAdmin` (from `app.deps`). No exceptions.
- `tests/api/test_authz_sweep.py` enumerates every route and fails if a mutating
  one is reachable anonymously. Do not add routes to its allow-list.

## CSRF

Enforced in middleware for every unsafe method. htmx requests carry the token
automatically (`hx-headers` on `<body>`), so **use htmx for admin actions**. A
plain HTML form must post to a path listed in `CSRF_EXEMPT_PATHS` and verify the
token itself — currently only `/login` and `/logout` do this.

## Feedback after an action

Return `headers=toast_headers("Сохранено")` from `app.templating`. Header values
must be latin-1, so it percent-encodes the message; `ui.js` decodes and shows it.
Errors (401/403/5xx) are already handled globally in `ui.js`.

## Markdown

`app.services.markdown.render_markdown` — raw HTML disabled, output sanitised
with an nh3 allow-list. Editor previews **must** call the same function so the
preview cannot diverge from the published page. `excerpt_from` builds card and
meta-description text.

## Images

`app.services.images` owns validation, storage and derivatives for every module.

- `store_and_process(data, filename, content_type, kind=...)` — single image
  (cover, in-article picture), synchronous.
- `validate_upload` → `store_original` → `verify_decodable` →
  `generate_derivatives` — the steps, for batch work that runs in the background.
- `delete_files(*relative_paths)` — removes originals and derivatives.
- `media_url(relative)` → `/media/…`.

Stored paths are **relative to MEDIA_ROOT**. Originals are never served over
HTTP; only `derived/` is mounted at `/media`. Filenames are always
server-generated UUIDs.

## Background work

`app.background.submit_with_session(fn, ...)` runs `fn(db, ...)` off the request
path with its own session. Register startup recovery with
`app.background.register_recovery(hook)` — used to re-process photos left
half-done by a restart.

## Slugs

`app.services.slugs.unique_slug(db, Model, title)` — transliterates Cyrillic and
resolves collisions with a numeric suffix.

## CSS

- Tokens live in `app/static/css/tokens.css`. **Never hardcode a colour.** Both
  themes come from `light-dark()`; `color-scheme` decides which side resolves.
- Layers: `@layer reset, tokens, base, layout, components, utilities`. Put new
  component rules in `@layer components`.
- One stylesheet per feature area, pulled in from that page's `head_extra` block.
- Reuse `.card`, `.card-grid`, `.button`, `.field`, `.empty`, `.label` before
  inventing anything.
- **Cards carry no tags, no reading time and no counters.** That absence is a
  requirement from the brief, not an oversight.
- Motion stays under 250 ms and must be disabled under `prefers-reduced-motion`.

## Editing in place

There is no separate admin area. Editing happens on the public page: htmx swaps
a read-only partial for an edit partial and back. `partials/editable.html` and
`partials/editable_form.html` are the reference implementation, wired up in
`app/routers/pages.py`.

## Jinja traps that have already cost time here

- **`loop` is not visible inside `{% include %}`.** Pass what you need
  explicitly: `{% with is_first = loop.first %}{% include … %}{% endwith %}`.
- **`something.values` resolves to the dict's `values()` method**, not the key.
  Any context dict with a `values` key must be read as `form["values"]`. The
  symptom is silently empty output, not an error. The same applies to `items`,
  `keys`, `get`, `copy` and `update`.
- **CSP forbids inline `<style>` and inline `style=` attributes.** htmx's
  indicator styles are disabled via the `htmx-config` meta tag in `base.html`
  and defined in `components.css` instead. If you need a per-item value such as
  an aspect ratio, put it in a class, not a `style` attribute.
- Check brace balance after editing a stylesheet: one stray `}` silently
  discards every rule after it, and `@layer` makes that easy to miss.

## Accessibility floor

Keyboard operation for everything, visible focus (inherited from `:focus-visible`),
`alt` on images, labels on inputs, AA contrast in both themes.
