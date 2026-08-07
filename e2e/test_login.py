"""Launch flow 1 — login (SPEC F16, F20, F36; user flow 7)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import ru

ADMIN_BAR = "Режим редактирования"


@pytest.mark.launch_flow
def test_login_reveals_admin_and_logout_takes_it_away(
    page: Page, base_url: str, admin_credentials: tuple[str, str]
) -> None:
    username, password = admin_credentials

    # F36: nothing admin-shaped reaches an anonymous visitor.
    page.goto("/photo")
    expect(page.get_by_role("region", name=ADMIN_BAR)).to_have_count(0)
    expect(page.get_by_role("button", name=ru("photo.new_album"))).to_have_count(0)

    # Not linked from the navigation — the owner types the address.
    page.goto("/login?next=/photo")
    page.get_by_label("Логин", exact=True).fill(username)
    page.get_by_label("Пароль", exact=True).fill(password)
    page.get_by_role("button", name="Войти", exact=True).click()

    # F16: back on the page the owner came from, now in editing mode.
    expect(page).to_have_url(f"{base_url}/photo")
    expect(page.get_by_role("region", name=ADMIN_BAR)).to_be_visible()
    expect(page.get_by_role("button", name=ru("photo.new_album"))).to_be_visible()

    cookie = next(c for c in page.context.cookies() if c["name"] == "portfolio_session")
    assert cookie["httpOnly"] is True
    assert cookie["sameSite"] == "Lax"

    # F20: logging out revokes the affordances.
    page.get_by_role("button", name="Выйти", exact=True).click()
    expect(page).to_have_url(f"{base_url}/")
    page.goto("/photo")
    expect(page.get_by_role("region", name=ADMIN_BAR)).to_have_count(0)


def test_wrong_password_is_rejected_with_a_generic_message(
    page: Page, admin_credentials: tuple[str, str]
) -> None:
    """One deliberate failure per run; the success right after clears the slate.

    F17 counts failures per IP over 15 minutes and the whole suite shares one
    address, so a test that fails five times would lock the next run out.
    """
    username, password = admin_credentials

    page.goto("/login")
    page.get_by_label("Логин", exact=True).fill(username)
    page.get_by_label("Пароль", exact=True).fill("definitely-not-the-password")
    page.get_by_role("button", name="Войти", exact=True).click()

    error = page.get_by_role("alert")
    expect(error).to_be_visible()
    # F17: the message must not distinguish a wrong name from a wrong password.
    assert username not in error.inner_text()
    expect(page.get_by_role("region", name=ADMIN_BAR)).to_have_count(0)

    page.get_by_label("Логин", exact=True).fill(username)
    page.get_by_label("Пароль", exact=True).fill(password)
    page.get_by_role("button", name="Войти", exact=True).click()
    expect(page.get_by_role("region", name=ADMIN_BAR)).to_be_visible()
