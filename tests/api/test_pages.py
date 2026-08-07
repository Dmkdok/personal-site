"""The owner's outbound links, edited in place from the footer (F35, T084).

The four social links and the name in the copyright line used to be typed into
two templates. They are `site_content` rows now, rendered twice — once as the
footer list, once as the home page's chips — so every assertion here counts
*two* occurrences on purpose: one rendering going stale while the other updates
is exactly the bug this replaced.
"""

from datetime import UTC, datetime

import pytest

from app.models.site_content import SiteContent
from app.templating import translate

DEFAULTS = {
    "github": "https://github.com/Dmkdok",
    "telegram": "https://t.me/dmkdok_blog",
    "vk": "https://vk.ru/dmkdok",
    "youtube": "https://www.youtube.com/@dmkdok",
}

#: A complete, valid submission. Tests override the one field they are about.
FORM = {**DEFAULTS, "rights": "Дмитрий Богданов"}


@pytest.fixture(autouse=True)
def virgin_site_content(db):
    """No stored rows, so every test starts from the bundled defaults."""
    db.query(SiteContent).delete()
    db.commit()
    yield
    db.query(SiteContent).delete()
    db.commit()


def _stored(db, slug: str) -> str | None:
    """The value the application wrote, read through a fresh transaction."""
    db.rollback()
    row = db.get(SiteContent, (f"footer.{slug}", "ru"))
    return None if row is None else row.value_md


def _save(admin_client, **overrides):
    return admin_client.post("/admin/site-links", data={**FORM, **overrides})


# ------------------------------------------------------------------- defaults
def test_defaults_render_in_both_places_without_a_single_stored_row(client, db):
    """A virgin database still shows the links: the catalogue is the seed."""
    assert db.query(SiteContent).count() == 0

    html = client.get("/").text
    for url in DEFAULTS.values():
        assert html.count(url) == 2, f"{url} should render in the footer and in the contacts block"

    # Reading the page must not have written anything — the footer renders on
    # every page in the site, and a template render that writes is a trap.
    db.rollback()
    assert db.query(SiteContent).filter(SiteContent.key.like("footer.%")).count() == 0


def test_the_copyright_year_is_automatic_and_only_the_name_is_stored(admin_client, db):
    _save(admin_client, rights="Кто-то Другой")

    html = admin_client.get("/").text
    assert f"© {datetime.now(UTC).year} Кто-то Другой" in html
    db.rollback()
    assert db.get(SiteContent, ("footer.rights", "ru")).value_md == "Кто-то Другой"


# ---------------------------------------------------------------------- saving
def test_a_saved_link_reaches_the_footer_and_the_contacts_block(admin_client, client, db):
    changed = "https://t.me/somewhere_else"
    assert _save(admin_client, telegram=changed).status_code == 200
    assert _stored(db, "telegram") == changed

    html = client.get("/").text
    assert html.count(changed) == 2
    assert DEFAULTS["telegram"] not in html
    # The links nobody touched are untouched.
    assert html.count(DEFAULTS["github"]) == 2


def test_an_empty_value_removes_the_link_from_both_renderings(admin_client, client, db):
    assert _save(admin_client, vk="").status_code == 200
    assert _stored(db, "vk") == ""

    html = client.get("/").text
    assert DEFAULTS["vk"] not in html
    assert ">VK<" not in html, "the label outlived the link it belonged to"
    assert html.count(DEFAULTS["youtube"]) == 2


# ------------------------------------------------------------------ validation
@pytest.mark.parametrize(
    "bad",
    ["javascript:alert(1)", "data:text/html,<script>alert(1)</script>", "//evil.example", "ftp:x"],
)
def test_a_non_http_scheme_is_refused_and_the_stored_value_survives(admin_client, client, db, bad):
    _save(admin_client, github="https://github.com/kept")
    assert _stored(db, "github") == "https://github.com/kept"

    response = _save(admin_client, github=bad)

    # The form comes back — with the error, and with what was typed still in it.
    assert response.status_code == 200
    assert translate("footer.invalid_url") in response.text
    assert 'href="' + bad not in response.text

    # And nothing was written.
    assert _stored(db, "github") == "https://github.com/kept"
    assert "https://github.com/kept" in client.get("/").text


def test_one_bad_field_does_not_save_the_good_ones_beside_it(admin_client, db):
    _save(admin_client, youtube="https://youtube.com/@kept")
    _save(admin_client, youtube="https://youtube.com/@new", vk="javascript:alert(1)")

    assert _stored(db, "youtube") == "https://youtube.com/@kept"
    assert _stored(db, "vk") == DEFAULTS["vk"]


# --------------------------------------------------------------- authorisation
def test_an_anonymous_save_is_refused(client, csrf_from_page):
    """A real visitor holds a CSRF token, so send one: this isolates authz."""
    token = csrf_from_page(client.get("/").text)
    response = client.post("/admin/site-links", data=FORM, headers={"X-CSRF-Token": token})
    assert response.status_code in (401, 403)


@pytest.mark.parametrize("path", ["/admin/site-links", "/admin/site-links/edit"])
def test_the_admin_partials_are_not_served_to_a_visitor(client, path):
    assert client.get(path, follow_redirects=False).status_code in (303, 401, 403)


def test_no_editing_markup_leaks_to_a_visitor(client):
    html = client.get("/").text
    for marker in ("/admin/site-links", "site-links__edit"):
        assert marker not in html, f"admin markup leaked to anonymous visitor: {marker}"
