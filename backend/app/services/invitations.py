import secrets
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import cipher, digest
from app.db.models import Invitation, InvitationLink
from app.schemas import InvitationCreate
from app.services.access import ensure_access
from app.services.messages import invitation_message


async def create_invitation(
    db: AsyncSession, data: InvitationCreate, *, is_admin: bool = False, token: str | None = None
) -> Invitation:
    token = token or secrets.token_urlsafe(32)
    invite = Invitation(
        id=uuid.uuid7().hex,
        name=data.name,
        email=str(data.email) if data.email else "",
        language=data.language,
        is_witness=data.is_witness,
        max_guests=data.max_guests,
        active=True,
        is_admin=is_admin,
        encrypted_token=cipher().encrypt(token.encode()).decode(),
        uploads=0,
        email_status="draft",
        created_at=int(time.time()),
    )
    db.add(invite)
    db.add(InvitationLink(token_hash=digest(token), invitation_id=invite.id))
    await db.flush()
    await ensure_access(db, invite.id)
    await invitation_message(db, invite)
    return invite


def invitation_link(invite: Invitation) -> str:
    token = cipher().decrypt(invite.encrypted_token.encode()).decode()
    return f"{settings().site_url.rstrip('/')}/#invite={token}"


def invitation_view(invite: Invitation) -> dict[str, object]:
    return {
        "id": invite.id,
        "name": invite.name,
        "email": invite.email,
        "language": invite.language,
        "is_witness": invite.is_witness,
        "max_guests": invite.max_guests,
        "active": invite.active,
        "link": invitation_link(invite),
        "email_status": invite.email_status,
        "email_error": invite.email_error,
        "has_rsvp": invite.has_rsvp,
    }
