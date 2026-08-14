"""Bounded indexes: one page size, one parser, one shape for the template.

Every index on this site used to render its whole table. That is fine at ten
articles and not at three hundred, and the fix is the same everywhere — so it
is written once here and the routers only say how many rows they have and which
page was asked for (SPEC F52).

The parser is deliberately forgiving. `?page=0`, `?page=-3`, `?page=abc` and
`?page=999` are all things a crawler, a stale link or a fat finger will produce,
and none of them is worth a 500 or a 404: they clamp to the nearest real page.
"""

from __future__ import annotations

from dataclasses import dataclass

#: One number, one place. Chosen to fill the three-column card grid on a wide
#: screen with four full rows and to stay one screenful on a phone.
PAGE_SIZE = 12


@dataclass(frozen=True)
class Page:
    """Where a bounded list is, and what it can offer next.

    `number` and `pages` are 1-based because they appear in URLs and in text
    the owner reads; `offset` is 0-based because SQL is.
    """

    number: int
    pages: int
    total: int
    size: int

    @property
    def offset(self) -> int:
        return (self.number - 1) * self.size

    @property
    def previous(self) -> int | None:
        return self.number - 1 if self.number > 1 else None

    @property
    def next(self) -> int | None:
        return self.number + 1 if self.number < self.pages else None

    @property
    def bounded(self) -> bool:
        """True when there is more than one page — i.e. when to render a control."""
        return self.pages > 1


def parse_page(raw: str | int | None) -> int:
    """The requested page number, or 1 for anything that is not one.

    Clamped at the bottom only: the top depends on how many rows there are, and
    that is `page_for`'s business.
    """
    try:
        number = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 1
    return max(1, number)


def page_for(total: int, requested: str | int | None, size: int = PAGE_SIZE) -> Page:
    """Resolve a request against a real row count.

    An empty list still has one page, so an empty index renders as an empty
    index rather than as page 0 of 0.
    """
    pages = max(1, -(-total // size))
    number = min(parse_page(requested), pages)
    return Page(number=number, pages=pages, total=total, size=size)


def page_url(path: str, number: int) -> str:
    """The canonical address of one page.

    Page 1 is the bare path and never `?page=1`: two URLs for one page is the
    duplicate-content problem the `canonical` in the head exists to avoid.
    """
    return path if number <= 1 else f"{path}?page={number}"
