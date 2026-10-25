from sqlalchemy import BigInteger, Boolean, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, foreign, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Guest(Base):
    __tablename__ = "guests"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    __table_args__ = (Index("uq_guest_email", "email", unique=True),)
    audience: Mapped[str] = mapped_column(String(10), default="guest", server_default="guest")

    def __str__(self):
        return self.name


class PhotoGuest(Base):
    __tablename__ = "photo_guests"
    photo_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    guest_id: Mapped[str] = mapped_column(String(64), primary_key=True)


class Invitation(Base):
    __tablename__ = "invitations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(2), default="en", server_default="en")
    max_guests: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_witness: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    encrypted_token: Mapped[str] = mapped_column(Text)
    uploads: Mapped[int] = mapped_column(Integer, default=0)
    parent_invitation_id: Mapped[str] = mapped_column(String(64), default="", server_default="")
    has_rsvp: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    email_status: Mapped[str] = mapped_column(String(20), default="draft")
    email_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer)

    guest_id: Mapped[str] = mapped_column(String(64), nullable=True)
    guest: Mapped[Guest] = relationship(
        primaryjoin=lambda: foreign(Invitation.guest_id) == Guest.id, lazy="joined"
    )
    attending: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    message: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=True)
    dietary: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=True)
    response_email: Mapped[str] = mapped_column(
        String(254), default="", server_default="", nullable=True
    )
    response_guests: Mapped[str] = mapped_column(
        Text, default="[]", server_default="[]", nullable=True
    )
    consent: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=True
    )
    witness_acceptance: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=True
    )
    updated_at: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=True)
    __table_args__ = (Index("uq_invitation_guest", "guest_id", unique=True),)


class InvitationLink(Base):
    __tablename__ = "invitation_links"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    invitation_id: Mapped[str] = mapped_column(String(64))


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    invitation_id: Mapped[str] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Photo(Base):
    multipart_id: Mapped[str] = mapped_column(Text, default="", server_default="")
    motion_multipart_id: Mapped[str] = mapped_column(Text, default="", server_default="")
    original_filename: Mapped[str] = mapped_column(String(200), default="", server_default="")
    storage_prefix: Mapped[str] = mapped_column(String(65), default="", server_default="")
    uploader_name: Mapped[str] = mapped_column(String(100), default="", server_default="")
    uploaded_at: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    completed_at: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    width: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    height: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duration_ms: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    codec: Mapped[str] = mapped_column(String(40), default="", server_default="")
    sha256: Mapped[str] = mapped_column(String(64), default="", server_default="")
    gallery_visible: Mapped[bool] = mapped_column(
        "published", Boolean, default=False, server_default="false"
    )
    carousel_visible: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=True
    )
    motion_size: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    motion_content_type: Mapped[str] = mapped_column(String(50), default="", server_default="")
    __tablename__ = "photos"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(BigInteger)
    content_type: Mapped[str] = mapped_column(String(50))
    caption: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    expires: Mapped[int] = mapped_column(Integer)

    guests: Mapped[list[Guest]] = relationship(
        secondary=lambda: PhotoGuest.__table__,
        primaryjoin=lambda: Photo.id == foreign(PhotoGuest.photo_id),
        secondaryjoin=lambda: Guest.id == foreign(PhotoGuest.guest_id),
        lazy="selectin",
    )


class AdminUser(Base):
    totp_secret: Mapped[str] = mapped_column(Text, default="", server_default="")
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    totp_last_step: Mapped[int] = mapped_column(Integer, default=-1, server_default="-1")
    __tablename__ = "admin_users"
    username: Mapped[str] = mapped_column(String(100), primary_key=True)
    password_hash: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[int] = mapped_column(Integer, default=0)


class InvitationAccess(Base):
    __tablename__ = "invitation_access"
    invitation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    encrypted_code: Mapped[str] = mapped_column(Text)
    recovery_at: Mapped[int] = mapped_column(Integer, default=0)
    pending_code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pending_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_link_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pending_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_expires: Mapped[int] = mapped_column(Integer, default=0)


class AuthThrottle(Base):
    __tablename__ = "auth_throttle"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer)


class RSVPNotification(Base):
    __tablename__ = "rsvp_notifications"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    invitation_id: Mapped[str] = mapped_column(String(64))
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer)


class ConfirmationEmail(Base):
    __tablename__ = "confirmation_emails"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    invitation_id: Mapped[str] = mapped_column(String(64))
    recipient: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(200))
    text_body: Mapped[str] = mapped_column(Text)
    html_body: Mapped[str] = mapped_column(Text)
    calendar: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer)


class InvitationMessage(Base):
    __tablename__ = "invitation_messages"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    language: Mapped[str] = mapped_column(String(2))
    audience: Mapped[str] = mapped_column(String(10), default="guest")
    text: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
