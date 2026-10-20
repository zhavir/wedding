"""Structured RSVP persistence; all writes share the caller's transaction."""

import time

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invitation, RSVPGuest, RSVPResponse, WitnessResponse
from app.schemas import RSVP


async def store_response(db: AsyncSession, invitation_id: str, body: RSVP) -> None:
    response = await db.get(RSVPResponse, invitation_id)
    if response is None:
        response = RSVPResponse(invitation_id=invitation_id)
        db.add(response)
    response.email = str(body.email)
    response.attending = body.attending
    response.message = body.message
    response.consent = body.consent
    response.updated_at = int(time.time())
    invite = await db.get(Invitation, invitation_id)
    if invite and invite.is_witness:
        witness = await db.get(WitnessResponse, invitation_id)
        if witness is None:
            witness = WitnessResponse(invitation_id=invitation_id)
            db.add(witness)
        witness.accepted = body.attending and body.witness_acceptance
    await db.execute(
        update(RSVPGuest)
        .where(RSVPGuest.invitation_id == invitation_id)
        .values(active=False, name="", dietary="", email="")
    )
    for position, person in enumerate(body.guests):
        key = f"{invitation_id}:{position}"
        guest = await db.get(RSVPGuest, key)
        if guest is None:
            guest = RSVPGuest(id=key, invitation_id=invitation_id, position=position)
            db.add(guest)
        guest.name, guest.dietary, guest.active = person.name, person.dietary, True
        guest.email = str(person.email) if person.email else ""


async def read_response(db: AsyncSession, invitation_id: str) -> dict | None:
    response = await db.get(RSVPResponse, invitation_id)
    if response is None:
        return None
    guests = await db.scalars(
        select(RSVPGuest)
        .where(RSVPGuest.invitation_id == invitation_id, RSVPGuest.active.is_(True))
        .order_by(RSVPGuest.position)
    )
    result = {
        "email": response.email,
        "attending": response.attending,
        "message": response.message,
        "consent": response.consent,
        "guests": [
            {
                "name": guest.name,
                "dietary": guest.dietary,
                **({"email": guest.email} if guest.email else {}),
            }
            for guest in guests
        ],
    }
    witness = await db.get(WitnessResponse, invitation_id)
    if witness:
        result["witness_acceptance"] = witness.accepted
    return result
