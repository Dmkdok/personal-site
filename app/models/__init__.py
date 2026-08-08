"""SQLAlchemy models. Importing this package registers every table on Base.metadata."""

from app.models.admin_user import AdminUser, LoginAttempt
from app.models.album import Album
from app.models.media_asset import MediaAsset
from app.models.photo import Photo, PhotoStatus
from app.models.post import Post, PostStatus
from app.models.project import Project
from app.models.site_content import SiteContent

__all__ = [
    "AdminUser",
    "Album",
    "LoginAttempt",
    "MediaAsset",
    "Photo",
    "PhotoStatus",
    "Post",
    "PostStatus",
    "Project",
    "SiteContent",
]
