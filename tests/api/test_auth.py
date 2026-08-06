"""Login, throttling, session invalidation."""

import os

from app.config import settings


def _login(client, password: str, csrf: str | None = None):
    if csrf is None:
        csrf = client.get("/login").text.split('name="csrf_token" value="')[1].split('"')[0]
    return client.post(
        "/login",
        data={
            "username": os.environ["ADMIN_USERNAME"],
            "password": password,
            "csrf_token": csrf,
            "next": "/",
        },
        follow_redirects=False,
    )


def test_correct_credentials_sign_in(client):
    assert _login(client, os.environ["ADMIN_PASSWORD"]).status_code == 303
    assert "admin-bar" in client.get("/").text


def test_wrong_password_and_unknown_user_are_indistinguishable(client):
    wrong_password = _login(client, "definitely-not-it")

    csrf = client.get("/login").text.split('name="csrf_token" value="')[1].split('"')[0]
    unknown_user = client.post(
        "/login",
        data={
            "username": "someone-else",
            "password": "definitely-not-it",
            "csrf_token": csrf,
            "next": "/",
        },
        follow_redirects=False,
    )

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert "Неверный логин или пароль" in wrong_password.text
    assert "Неверный логин или пароль" in unknown_user.text


def test_login_without_csrf_is_rejected(client):
    response = client.post(
        "/login",
        data={
            "username": os.environ["ADMIN_USERNAME"],
            "password": os.environ["ADMIN_PASSWORD"],
            "csrf_token": "bogus",
            "next": "/",
        },
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_repeated_failures_are_throttled(client, db):
    from app.models.admin_user import LoginAttempt

    db.query(LoginAttempt).delete()
    db.commit()

    statuses = [
        _login(client, "wrong-again").status_code for _ in range(settings.login_max_attempts + 1)
    ]
    assert statuses[-1] == 429, statuses

    db.query(LoginAttempt).delete()
    db.commit()


def test_logout_invalidates_the_session(admin_client):
    token = admin_client.headers["X-CSRF-Token"]
    response = admin_client.post(
        "/logout", data={"csrf_token": token}, follow_redirects=False
    )
    assert response.status_code == 303
    assert "admin-bar" not in admin_client.get("/").text


def test_password_is_never_stored_in_plaintext(db):
    from app.models.admin_user import AdminUser

    user = db.query(AdminUser).first()
    assert user is not None
    assert os.environ["ADMIN_PASSWORD"] not in user.password_hash
    assert user.password_hash.startswith("$argon2")
