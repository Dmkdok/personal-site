"""The structural guarantee behind in-place editing (ADR-006).

Every mutating route on the application must reject an anonymous request. This
enumerates the routes rather than listing them by hand, so an endpoint added
later without an auth dependency fails the suite instead of shipping open.
"""

import pytest
from fastapi.routing import APIRoute

# Public POST endpoints. Anything added here is a deliberate decision, and both
# of these verify a CSRF token in the handler itself.
PUBLIC_MUTATING_PATHS = {"/login", "/logout"}

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Stand-in values for path parameters.
PARAM_SAMPLES = {
    "key": "home.intro",
    "slug": "example",
    "album_id": "1",
    "photo_id": "1",
    "post_id": "1",
    "project_id": "1",
    "id": "1",
}


def _fill(path: str) -> str:
    for name, value in PARAM_SAMPLES.items():
        path = path.replace("{" + name + "}", value)
    return path


def _iter_api_routes(app):
    """Walk the whole route tree.

    Since the FastAPI 0.141 router refactor, `include_router` leaves an
    `_IncludedRouter` wrapper in `app.routes` instead of flattening the routes
    into it, so a flat scan would silently find nothing and this sweep would
    pass while proving nothing.
    """
    stack = [app]
    seen: set[int] = set()
    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))

        # `_IncludedRouter` keeps the real router behind `original_router`.
        nested = getattr(node, "original_router", None)
        if nested is not None:
            stack.append(nested)

        for route in getattr(node, "routes", ()):
            if isinstance(route, APIRoute):
                yield route
            else:
                stack.append(route)


def _mutating_routes(app):
    for route in _iter_api_routes(app):
        if route.path in PUBLIC_MUTATING_PATHS:
            continue
        for method in route.methods - SAFE_METHODS:
            yield method, route.path


def test_there_are_mutating_routes(app_module):
    """Guards the guard: if this list is empty the sweep proves nothing."""
    assert list(_mutating_routes(app_module)), "no mutating routes found to check"


def test_every_mutating_route_rejects_anonymous(client, app_module):
    """Anonymous requests must never reach a handler that changes state."""
    unprotected: list[str] = []

    for method, path in _mutating_routes(app_module):
        # A real visitor already holds a CSRF token, so send a valid one: this
        # isolates authorisation from CSRF and stops a 403 masking a hole.
        client.get("/")
        token = client.get("/").text.split('X-CSRF-Token": "')[1].split('"')[0]

        response = client.request(
            method,
            _fill(path),
            headers={"X-CSRF-Token": token},
            follow_redirects=False,
        )
        if response.status_code not in (401, 403, 404, 405):
            unprotected.append(f"{method} {path} -> {response.status_code}")

    assert not unprotected, "mutating routes reachable without a session: " + ", ".join(unprotected)


@pytest.mark.parametrize(
    "method,path",
    [("GET", "/admin/content/home.intro"), ("GET", "/admin/content/home.intro/edit")],
)
def test_admin_read_endpoints_require_session(client, method, path):
    """Admin-only reads redirect to the login form rather than rendering."""
    response = client.request(method, path, follow_redirects=False)
    assert response.status_code in (303, 401, 403)


def test_mutation_without_csrf_is_rejected(admin_client):
    """Even a signed-in admin cannot mutate without the CSRF token."""
    response = admin_client.post(
        "/admin/content/home.intro",
        data={"value_md": "no token"},
        headers={"X-CSRF-Token": ""},
    )
    assert response.status_code == 403


def test_anonymous_html_contains_no_admin_markup(client):
    """A visitor must not receive edit controls, even hidden ones."""
    html = client.get("/").text
    # The list only ever grows. `admin-bar` was retired into the navigation
    # capsule by ADR-027 and cannot appear in any HTML now, owner's included —
    # which costs this sweep nothing and makes a shortened list, one day, a
    # weakened guarantee rather than a tidied one.
    for marker in ("admin-bar", "owner-menu", "editable__edit", "/admin/content/"):
        assert marker not in html, f"admin markup leaked to anonymous visitor: {marker}"


def test_every_response_carries_the_security_headers_including_a_500(_schema):
    """The 500 is the one that used to leave without them.

    Starlette builds it in `ServerErrorMiddleware`, which sits *outside* the
    user middleware stack, so the middleware that stamps the policy never runs
    on the way out — on precisely the response most likely to be carrying
    detail nobody meant to publish.
    """
    from starlette.testclient import TestClient

    from app.main import create_app

    app = create_app()

    @app.get("/boom-for-tests")
    def boom() -> None:
        raise RuntimeError("deliberate")

    with_errors = TestClient(app, raise_server_exceptions=False)

    for path, expected in (("/", 200), ("/boom-for-tests", 500)):
        response = with_errors.get(path)
        assert response.status_code == expected, path
        assert "Content-Security-Policy" in response.headers, path
        assert response.headers["X-Frame-Options"] == "DENY", path
        assert response.headers["X-Content-Type-Options"] == "nosniff", path
