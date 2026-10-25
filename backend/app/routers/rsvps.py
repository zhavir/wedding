import asyncio
from collections.abc import Awaitable

from fastapi import APIRouter, HTTPException
from sqlalchemy import update

from app.core.security import DB, Guest
from app.db.models import Invitation
from app.schemas import RSVP
from app.services.additional_guests import sync_additional_guests
from app.services.confirmations import queue_confirmation, send_confirmation
from app.services.email import send_invitation
from app.services.notifications import queue_notification, send_notification
from app.services.rsvps import read_response, store_response

router = APIRouter()


@router.get("/rsvp")
async def get_rsvp(invite: Guest, db: DB):
    return {
        "rsvp": await read_response(db, invite.id),
        "prefill": {"email": invite.guest.email or "", "name": invite.name},
    }


@router.put("/rsvp")
async def save_rsvp(body: RSVP, invite: Guest, db: DB):
    if len(body.guests) > invite.max_guests:
        raise HTTPException(422, "Your party exceeds the number of invited guests.")
    if invite.is_witness and body.attending and not body.witness_acceptance:
        raise HTTPException(422, "Please confirm that you accept the role of witness.")
    if body.witness_acceptance and (not invite.is_witness or not body.attending):
        raise HTTPException(422, "Witness acceptance is only available to attending witnesses.")
    # Serialize revisions of the same party before reconciling child invitations.
    await db.execute(
        update(Invitation).where(Invitation.id == invite.id).values(has_rsvp=Invitation.has_rsvp)
    )
    previous = await read_response(db, invite.id)
    # Duplicate network submissions do not trigger duplicate notifications.
    if previous and {"witness_acceptance": False, **previous} == body.model_dump(exclude_none=True):
        return {"saved": True}
    await store_response(db, invite.id, body)
    additional_ids = await sync_additional_guests(db, invite, body)
    invite.has_rsvp = True
    confirmation = None
    if body.attending and (
        not previous or not previous["attending"] or previous["email"] != str(body.email)
    ):
        confirmation = await queue_confirmation(db, invite, body)
    notification = queue_notification(db, invite, body)
    await db.commit()
    deliveries: list[Awaitable[object]] = [send_invitation(identity) for identity in additional_ids]
    if notification:
        deliveries.append(send_notification(notification))
    if confirmation:
        deliveries.append(send_confirmation(confirmation))
    if deliveries:
        await asyncio.gather(*deliveries)
    return {"saved": True}
