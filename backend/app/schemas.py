from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

NormalizedEmail = Annotated[EmailStr, AfterValidator(str.casefold)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Model):
    code: str = Field(min_length=8, max_length=100)


class Person(Model):
    email: NormalizedEmail | None = None
    name: str = Field(min_length=1, max_length=100)
    dietary: str = Field(default="", max_length=500)

    @field_validator("email", mode="before")
    @classmethod
    def blank_email(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


class RSVP(Model):
    email: NormalizedEmail
    attending: bool
    guests: list[Person] = Field(max_length=12)
    message: str = Field(default="", max_length=1000)
    consent: Literal[True]
    witness_acceptance: bool = False

    @model_validator(mode="after")
    def attendance(self):
        if self.attending != bool(self.guests):
            raise ValueError("List attending guests, or leave guests empty when declining.")
        emails = [str(person.email).casefold() for person in self.guests[1:] if person.email]
        if len(set(emails)) != len(emails) or str(self.email).casefold() in emails:
            raise ValueError("Each additional guest must have a different email address.")
        return self


class Upload(Model):
    filename: str = Field(min_length=1, max_length=200)
    content_type: Literal[
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
        "video/mp4",
        "video/quicktime",
        "video/webm",
    ]
    motion_size: int = Field(default=0, ge=0, le=5 * 1024**3 * 10000)
    motion_content_type: Literal["", "video/mp4", "video/quicktime"] = ""
    size: int = Field(gt=0, le=5 * 1024**3 * 10000)
    caption: str = Field(default="", max_length=200)
    consent: bool | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def validate_media(self):
        if self.content_type.startswith("image/") and self.size > 25 * 1024 * 1024:
            raise ValueError("Images must be at most 25 MB.")
        if bool(self.motion_size) != bool(self.motion_content_type) or (
            self.motion_size and self.content_type.startswith("video/")
        ):
            raise ValueError("A Live Photo needs one still image and its paired video.")
        return self


class InvitationCreate(Model):
    name: str = Field(min_length=1, max_length=100)
    email: NormalizedEmail | None = None
    language: Literal["en", "it"] = "it"
    is_witness: bool = False
    max_guests: int = Field(default=2, ge=1, le=12)


class InvitationBatch(Model):
    invitations: list[InvitationCreate] = Field(min_length=1, max_length=100)


class SendBatch(Model):
    ids: list[str] = Field(min_length=1, max_length=25)


class RecoverInvitation(Model):
    email: NormalizedEmail


class UploadPart(Model):
    number: int = Field(ge=1, le=10000)
    etag: str = Field(min_length=1, max_length=200)


class FinishUpload(Model):
    parts: list[UploadPart] = Field(default_factory=list, max_length=10000)
    motion_parts: list[UploadPart] = Field(default_factory=list, max_length=10000)
