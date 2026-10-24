"""The invitation owns its latest response; repeated submissions are idempotent."""

import json
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invitation
from app.schemas import RSVP


async def store_response(db: AsyncSession, invitation_id: str, body: RSVP) -> None:
    invite = await db.get(Invitation, invitation_id)
    assert invite is not None
    invite.response_email = str(body.email).casefold()
    invite.attending = body.attending
    invite.message = body.message
    invite.dietary = body.guests[0].dietary if body.guests else ""
    invite.consent = body.consent
    invite.updated_at = int(time.time())
    invite.witness_acceptance = body.attending and body.witness_acceptance
    invite.response_guests = json.dumps(
        [person.model_dump(exclude_none=True) for person in body.guests], ensure_ascii=False
    )
    invite.has_rsvp = True


async def read_response(db: AsyncSession, invitation_id: str) -> dict | None:
    invite = await db.get(Invitation, invitation_id)
    if invite is None or not invite.has_rsvp:
        return None
    return {
        "email": invite.response_email,
        "attending": invite.attending,
        "message": invite.message,
        "consent": invite.consent,
        "guests": json.loads(invite.response_guests),
        **({"witness_acceptance": invite.witness_acceptance} if invite.is_witness else {}),
    }
