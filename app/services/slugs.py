"""URL slugs from Russian titles, guaranteed unique."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from slugify import slugify


def make_slug(title: str, fallback: str = "zapis") -> str:
    """Transliterate a Cyrillic title into a URL-safe slug."""
    slug = slugify(title, max_length=120, word_boundary=True)
    return slug or fallback


def unique_slug(db: Session, model: type, title: str, *, exclude_id: int | None = None) -> str:
    """A slug that is not yet taken, suffixing -2, -3, … on collision."""
    base = make_slug(title)
    candidate = base
    suffix = 2

    while True:
        query = select(model.id).where(model.slug == candidate)
        if exclude_id is not None:
            query = query.where(model.id != exclude_id)
        if db.scalar(query) is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1
