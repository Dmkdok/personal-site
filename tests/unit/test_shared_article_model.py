"""SharedArticle (T146): a table separate from post, reachable only by its token."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.shared_article import SharedArticle


def test_shared_article_round_trip(db):
    article = SharedArticle(title="Заголовок", body_md="Текст.", body_html="<p>Текст.</p>")
    db.add(article)
    db.commit()

    fetched = db.get(SharedArticle, article.id)
    assert fetched is not None
    assert fetched.title == "Заголовок"
    assert fetched.share_token
    assert len(fetched.share_token) >= 32


def test_shared_article_share_token_is_unique_and_auto_assigned(db):
    first = SharedArticle(title="Первая")
    second = SharedArticle(title="Вторая")
    db.add_all([first, second])
    db.flush()  # column default only runs on insert, not on construction

    assert first.share_token != second.share_token
    assert SharedArticle.__table__.c.share_token.unique is True
    assert SharedArticle.__table__.c.share_token.index is True


def test_shared_article_share_token_unique_constraint_is_enforced(db):
    first = SharedArticle(title="Первая")
    db.add(first)
    db.commit()

    duplicate = SharedArticle(title="Дубликат", share_token=first.share_token)
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
