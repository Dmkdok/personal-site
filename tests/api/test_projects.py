"""Development section: hand-entered project cards, edited in place on /dev."""

import pytest

from app.models.project import Project

FORM = {
    "title": "Foodgram",
    "summary": "Сервис публикации рецептов с фильтрами и подписками",
    "body_md": "## О проекте\n\nDjango и DRF, контейнеризация, CI.",
    "repo_url": "https://github.com/Dmkdok/foodgram",
    "demo_url": "",
    "tech_stack": "Python, Django, DRF, PostgreSQL, Docker",
}


@pytest.fixture(autouse=True)
def clean_projects(db):
    db.query(Project).delete()
    db.commit()
    yield
    db.query(Project).delete()
    db.commit()


def _create(admin_client, **overrides):
    payload = {**FORM, **overrides}
    # An empty file part forces a real multipart body — the same encoding the
    # form uses in the browser, which is where UTF-8 could go wrong.
    return admin_client.post(
        "/dev/admin/projects",
        data=payload,
        files={"cover": ("", b"", "application/octet-stream")},
    )


def _only(db) -> Project:
    project = db.query(Project).first()
    assert project is not None, "project was not created"
    return project


def test_create_stores_every_field(admin_client, db):
    assert _create(admin_client).status_code == 200

    project = _only(db)
    assert project.title == "Foodgram"
    assert project.summary.startswith("Сервис публикации")
    assert project.repo_url == "https://github.com/Dmkdok/foodgram"
    assert project.tech_stack == ["Python", "Django", "DRF", "PostgreSQL", "Docker"]
    assert project.slug == "foodgram"
    # New projects start hidden so nothing half-written goes live.
    assert project.is_published is False


def test_cyrillic_survives_a_multipart_submission(admin_client, db):
    """The form is multipart because of the cover, so text must still be UTF-8."""
    _create(admin_client)
    assert "рецептов" in _only(db).summary


def test_unpublished_project_is_invisible_to_visitors(admin_client, db):
    _create(admin_client)
    slug = _only(db).slug

    # Dropping the session cookie turns this into an ordinary visitor.
    admin_client.cookies.clear()
    assert "Foodgram" not in admin_client.get("/dev").text
    assert admin_client.get(f"/dev/{slug}").status_code == 404


def test_publish_makes_it_visible(admin_client, db):
    _create(admin_client)
    project = _only(db)

    response = admin_client.post(f"/dev/admin/projects/{project.id}/publish")
    assert response.status_code == 200

    db.expire_all()
    assert _only(db).is_published is True

    admin_client.cookies.clear()
    assert "Foodgram" in admin_client.get("/dev").text


@pytest.mark.parametrize(
    "bad_url",
    ["javascript:alert(1)", "data:text/html,<script>", "ftp://example.com", "example.com"],
)
def test_dangerous_or_malformed_urls_are_refused(admin_client, db, bad_url):
    response = _create(admin_client, repo_url=bad_url)

    assert response.status_code == 200
    assert "http://" in response.text  # the inline error explains what is expected
    assert db.query(Project).count() == 0, f"{bad_url} was stored"


def test_rejected_save_keeps_what_was_typed(admin_client):
    response = _create(admin_client, repo_url="javascript:alert(1)")
    assert "Foodgram" in response.text
    assert "рецептов" in response.text


def test_title_is_required(admin_client, db):
    response = _create(admin_client, title="   ")
    assert response.status_code == 200
    assert db.query(Project).count() == 0


def test_edit_updates_the_card(admin_client, db):
    _create(admin_client)
    project = _only(db)

    response = admin_client.post(
        f"/dev/admin/projects/{project.id}",
        data={**FORM, "title": "Foodgram v2", "tech_stack": "Python, FastAPI"},
        files={},
    )
    assert response.status_code == 200

    db.expire_all()
    updated = _only(db)
    assert updated.title == "Foodgram v2"
    assert updated.tech_stack == ["Python", "FastAPI"]


def test_delete_removes_the_project(admin_client, db):
    _create(admin_client)
    project = _only(db)

    response = admin_client.delete(f"/dev/admin/projects/{project.id}")
    assert response.status_code == 200
    assert db.query(Project).count() == 0


def test_ordering_persists(admin_client, db):
    _create(admin_client, title="Первый")
    _create(admin_client, title="Второй")

    ordered = db.query(Project).order_by(Project.sort_order).all()
    first, second = ordered[0], ordered[1]

    response = admin_client.post(f"/dev/admin/projects/{second.id}/move", data={"direction": "up"})
    assert response.status_code == 200

    db.expire_all()
    reordered = db.query(Project).order_by(Project.sort_order).all()
    assert reordered[0].id == second.id
    assert reordered[1].id == first.id


def test_project_without_a_long_description_has_no_detail_page(admin_client, db):
    _create(admin_client, body_md="")
    project = _only(db)
    admin_client.post(f"/dev/admin/projects/{project.id}/publish")

    assert admin_client.get(f"/dev/{project.slug}").status_code == 404


def test_detail_page_renders_markdown(admin_client, db):
    _create(admin_client)
    project = _only(db)
    admin_client.post(f"/dev/admin/projects/{project.id}/publish")

    html = admin_client.get(f"/dev/{project.slug}").text
    assert "<h2>О проекте</h2>" in html
    assert "контейнеризация" in html


def test_no_tags_reading_time_or_counters_on_the_list(admin_client, db):
    _create(admin_client)
    project = _only(db)
    admin_client.post(f"/dev/admin/projects/{project.id}/publish")

    html = admin_client.get("/dev").text
    for forbidden in ("мин чтения", "просмотр", "reading-time", "view-count"):
        assert forbidden not in html
