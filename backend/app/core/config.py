from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://wedding:wedding@db:5432/wedding"
    dsql_host: str | None = None
    db_user: str = "wedding_app"
    bucket_name: str = "wedding-photos"
    aws_region: str = "eu-central-1"
    aws_endpoint_url: str | None = None
    s3_public_endpoint: str | None = None
    invite_encryption_key: str
    site_url: str = "http://localhost:5173"
    allowed_origins: str = ""
    cookie_secure: bool = True
    session_days: int = Field(default=400, ge=1, le=400)
    max_upload_bytes: int = 25 * 1024 * 1024
    max_uploads_per_invite: int = 100
    rsvp_notification_email: EmailStr | None = None
    ses_endpoint_url: str | None = None
    ses_region: str | None = None
    ses_profile: str | None = None
    email_from: str = "wedding@example.com"
    content_file: Path = Path("content/locales/en/wedding.json")

    @field_validator("rsvp_notification_email", mode="before")
    @classmethod
    def optional_notification_email(cls, value):
        return value or None


@lru_cache
def settings() -> Settings:
    return Settings()
