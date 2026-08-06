"""Jinja2 environment: template globals, translations, asset URLs."""

import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
I18N_DIR = APP_DIR / "i18n"

DEFAULT_LANG = "ru"

# Bumped whenever the process restarts; enough to bust static caches in a
# single-instance deployment without a build pipeline.
ASSET_VERSION = str(int(Path(__file__).stat().st_mtime))


@lru_cache
def _strings(lang: str) -> dict[str, Any]:
    """Merge every JSON file under `i18n/<lang>/`.

    One file per feature area, so parallel work on different sections never
    collides in a single giant locale file.
    """
    directory = I18N_DIR / lang
    if not directory.is_dir():
        directory = I18N_DIR / DEFAULT_LANG

    merged: dict[str, Any] = {}
    for path in sorted(directory.glob("*.json")):
        for key, value in json.loads(path.read_text(encoding="utf-8")).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            else:
                merged[key] = value
    return merged


def translate(key: str, lang: str = DEFAULT_LANG, **kwargs: Any) -> str:
    """Look up a dotted key in the locale file. Missing keys surface as the key."""
    node: Any = _strings(lang)
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return key
        node = node[part]
    if not isinstance(node, str):
        return key
    return node.format(**kwargs) if kwargs else node


def static_url(path: str) -> str:
    return f"/static/{path.lstrip('/')}?v={ASSET_VERSION}"


templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals.update(
    t=translate,
    static_url=static_url,
    site_url=settings.site_url,
    lang=DEFAULT_LANG,
    current_year=datetime.now(UTC).year,
    # Safe defaults so every template can be rendered from any route; routes
    # override these per request.
    active_section=None,
    theme_attr=None,
    is_admin=False,
    csrf_token="",
    query="",
)
templates.env.trim_blocks = True
templates.env.lstrip_blocks = True


def toast_headers(message: str, kind: str = "success") -> dict[str, str]:
    """Headers that make the browser show a message after an htmx request.

    Header values must be latin-1, so the Russian text is percent-encoded here
    and decoded in ui.js.
    """
    return {"HX-Toast": quote(message), "HX-Toast-Kind": kind}


def render(
    request: Request,
    name: str,
    context: dict[str, Any] | None = None,
    *,
    admin: Any = None,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> HTMLResponse:
    """Render a template with the per-request values every page needs.

    Centralised so that no route can accidentally ship a page without its CSRF
    token, or leak admin affordances by forgetting to pass `admin`.
    """
    from app.security import csrf_token as _csrf_token

    merged: dict[str, Any] = {
        "is_admin": admin is not None,
        "admin": admin,
        "csrf_token": _csrf_token(request),
    }
    if context:
        merged.update(context)
    return templates.TemplateResponse(
        request, name, merged, status_code=status_code, headers=headers
    )
