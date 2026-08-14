"""The page parser and the page shape (SPEC F52).

A page number arrives from the address bar, from a crawler and from a stale
link, so the parser's job is to answer rather than to fail: every malformed or
out-of-range value resolves to a real page.
"""

import pytest

from app.services.pagination import PAGE_SIZE, Page, page_for, page_url, parse_page


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2", 2),
        (3, 3),
        ("0", 1),
        ("-3", 1),
        ("abc", 1),
        ("", 1),
        (None, 1),
        ("1.5", 1),
        ("2junk", 1),
    ],
)
def test_the_parser_answers_instead_of_failing(raw, expected):
    assert parse_page(raw) == expected


def test_a_page_beyond_the_end_is_the_last_page():
    """`?page=999` on three pages is page 3, not a 404 and not an empty list."""
    assert page_for(total=30, requested="999", size=12).number == 3


def test_an_empty_list_still_has_one_page():
    page = page_for(total=0, requested="1")
    assert page.pages == 1
    assert page.number == 1
    assert page.bounded is False


def test_the_shape_the_template_reads():
    page = page_for(total=30, requested="2", size=12)
    assert (page.offset, page.previous, page.next, page.pages) == (12, 1, 3, 3)
    assert page.bounded is True


def test_a_full_last_page_does_not_invent_another():
    """24 rows at 12 a page is two pages, not three with an empty one."""
    page = page_for(total=24, requested="2", size=12)
    assert page.pages == 2
    assert page.next is None


def test_page_one_is_the_bare_path():
    """Two URLs for one page is the duplicate the canonical exists to avoid."""
    assert page_url("/blog", 1) == "/blog"
    assert page_url("/blog", 0) == "/blog"
    assert page_url("/blog", 2) == "/blog?page=2"


def test_the_page_size_lives_in_one_place():
    assert page_for(total=100, requested="1") == Page(
        number=1, pages=page_for(100, 1).pages, total=100, size=PAGE_SIZE
    )
