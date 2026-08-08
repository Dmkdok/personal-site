"""Application settings, read from the environment (see .env.example)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDERS = {"change-me", "change-me-to-a-long-random-string"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: Literal["local", "production"] = "local"

    secret_key: str
    database_url: str
    admin_username: str
    admin_password: str

    site_url: str = "http://localhost:8000"
    media_root: Path = Path("/data/media")

    # The size the owner actually exports at. Peak memory per file rises with
    # it; `images.MAX_PIXELS` is the backstop, not this.
    max_upload_mb: int = 50
    max_batch_files: int = 50
    session_max_age_days: int = 30

    # Login throttling: this many failures from one IP inside the window blocks further attempts.
    login_max_attempts: int = 5
    login_window_minutes: int = 15

    @field_validator("secret_key")
    @classmethod
    def _reject_placeholder_secret(cls, value: str) -> str:
        if value in _PLACEHOLDERS or len(value) < 32:
            raise ValueError(
                "SECRET_KEY must be a unique random string of at least 32 characters. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return value

    @field_validator("admin_password")
    @classmethod
    def _reject_placeholder_password(cls, value: str, info: ValidationInfo) -> str:
        """The same guard `secret_key` gets, for the same reason.

        `.env.example` shipped `ADMIN_PASSWORD=change-me` with nothing checking
        it, while the identical placeholder in `SECRET_KEY` was refused. The
        launch checklist says the only manual step is copying that file, so
        read literally it produced a live site whose admin password is written
        down in the repository.
        """
        if value in _PLACEHOLDERS:
            raise ValueError(
                "ADMIN_PASSWORD is still the placeholder from .env.example. Set a real password."
            )
        if info.data.get("env") == "production" and len(value) < 12:
            raise ValueError("ADMIN_PASSWORD must be at least 12 characters when ENV=production.")
        return value

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def originals_dir(self) -> Path:
        return self.media_root / "originals"

    @property
    def derived_dir(self) -> Path:
        return self.media_root / "derived"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment


settings = get_settings()
