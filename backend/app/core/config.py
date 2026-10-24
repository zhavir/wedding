from functools import lru_cache

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
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

    @field_validator("rsvp_notification_email", mode="before")
    @classmethod
    def optional_notification_email(cls, value):
        return value or None


@lru_cache
def settings() -> Settings:
    return Settings()


class BootstrapSettings(BaseSettings):
    admin_username: str
    admin_password: SecretStr
    runtime_role_arn: str
    ses_identity: str
    site_url: str
    wedding_groom_email: str
    debug_deploy: bool = False


class MigrationSettings(BaseSettings):
    dsql_host: str | None = None
    wedding_groom_name: str = "Wedding groom"
    wedding_groom_email: str = "groom@example.com"
    wedding_bride_name: str = "Wedding bride"
    wedding_bride_email: str = "bride@example.com"

    @model_validator(mode="after")
    def require_production_hosts(self):
        if not self.dsql_host:
            return self
        for field in (
            "wedding_groom_name",
            "wedding_groom_email",
            "wedding_bride_name",
            "wedding_bride_email",
        ):
            if field not in self.model_fields_set or not getattr(self, field).strip():
                raise ValueError(
                    f"{field.upper()} is required for the initial production migration"
                )
        return self
